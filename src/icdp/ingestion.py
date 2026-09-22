from __future__ import annotations
import csv
import io
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

# Security guardrail: 250MB maximum raw upload size to prevent memory exhaustion DoS
MAX_UPLOAD_BYTES = 250 * 1024 * 1024
MAX_SHEETS_COUNT = 100

@dataclass
class IngestionResult:
    frame: pd.DataFrame
    sheets: dict[str, pd.DataFrame]
    selected_sheets: list[str]
    encoding: str | None
    delimiter: str | None
    header_rows: dict[str, int]

def _score(values: list) -> float:
    vals = [str(v).strip() for v in values if pd.notna(v) and str(v).strip()]
    if not vals:
        return 0.0
    return len(vals) + len(set(vals)) / len(vals) + sum(any(c.isalpha() for c in v) for v in vals) / len(vals)

def _header(raw: pd.DataFrame, scan: int = 20) -> int:
    if raw.empty:
        return 0
    return max(range(min(scan, len(raw))), key=lambda i: _score(raw.iloc[i].tolist()))

def _deduplicate_columns(columns: list) -> list[str]:
    """Ensures all column headers are unique, non-empty, and clean."""
    seen: dict[str, int] = {}
    result: list[str] = []
    for i, c in enumerate(columns):
        base = str(c).strip() if pd.notna(c) else ""
        if not base or base.lower().startswith("unnamed:"):
            base = f"unnamed_{i}"
        if base in seen:
            seen[base] += 1
            result.append(f"{base}_{seen[base]}")
        else:
            seen[base] = 0
            result.append(base)
    return result

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").dropna(axis=1, how="all").copy()
    df.columns = _deduplicate_columns(df.columns)
    return df.reset_index(drop=True)

def _read_csv_optimized(stream: io.StringIO, sep: str, header, nrows=None) -> pd.DataFrame:
    """Uses C-engine for single-character delimiters (10x-20x faster than python engine)."""
    try:
        if len(sep) == 1:
            return pd.read_csv(stream, sep=sep, header=header, nrows=nrows, dtype=object, engine="c", on_bad_lines="warn")
    except Exception:
        stream.seek(0)
    return pd.read_csv(stream, sep=sep, header=header, nrows=nrows, dtype=object, engine="python", on_bad_lines="warn")

def inspect_upload(name: str, content: bytes) -> tuple[dict[str, pd.DataFrame], dict[str, int], str | None, str | None]:
    # CWE-22: Path traversal defense
    safe_name = Path(name).name.lower()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File size exceeds safety limit of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")

    if safe_name.endswith(".csv"):
        last_exc = None
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
            try:
                text = content.decode(enc)
                try:
                    sep = csv.Sniffer().sniff(text[:65536], delimiters=",;\t|").delimiter
                except csv.Error:
                    sep = ","
                
                # Sample header
                sample_io = io.StringIO(text)
                sample = _read_csv_optimized(sample_io, sep=sep, header=None, nrows=25)
                h = _header(sample)
                
                # Full read
                full_io = io.StringIO(text)
                df = _clean(_read_csv_optimized(full_io, sep=sep, header=h))
                return {"CSV": df}, {"CSV": h}, enc, sep
            except Exception as exc:
                last_exc = exc
        raise ValueError(f"Unable to read CSV file: {last_exc}")

    if safe_name.endswith((".xlsx", ".xls", ".xlsm")):
        book = pd.ExcelFile(io.BytesIO(content))
        sheets: dict[str, pd.DataFrame] = {}
        headers: dict[str, int] = {}
        if len(book.sheet_names) > MAX_SHEETS_COUNT:
            raise ValueError(f"Workbook exceeds safety sheet count limit ({MAX_SHEETS_COUNT} sheets max).")
            
        for sheet in book.sheet_names:
            sample = pd.read_excel(book, sheet_name=sheet, header=None, nrows=25, dtype=object)
            h = _header(sample)
            headers[sheet] = h
            sheets[sheet] = _clean(pd.read_excel(book, sheet_name=sheet, header=h, dtype=object))
        if not sheets:
            raise ValueError("Workbook contains no readable sheets.")
        return sheets, headers, None, None

    raise ValueError("Supported formats: CSV, XLSX, XLS, XLSM")

def combine_sheets(sheets: dict[str, pd.DataFrame], selected: list[str], mode: str = "Append rows", add_source: bool = True) -> pd.DataFrame:
    chosen = [sheets[x].copy() for x in selected if x in sheets]
    if not chosen:
        raise ValueError("Select at least one sheet")
    if mode == "Use first selected sheet":
        return chosen[0]
    if add_source:
        for name, df in zip(selected, chosen):
            if "Source Sheet" not in df.columns:
                df.insert(0, "Source Sheet", name)
    return pd.concat(chosen, ignore_index=True, sort=False)

def read_upload(name: str, content: bytes, selected_sheets: list[str] | None = None, mode: str = "Append rows", add_source: bool = True, cached_sheets=None, cached_headers=None) -> IngestionResult:
    if cached_sheets is not None:
        sheets = cached_sheets
        headers = cached_headers or {}
        enc, sep = None, None
    else:
        sheets, headers, enc, sep = inspect_upload(name, content)
        
    selected = selected_sheets or [max(sheets, key=lambda x: len(sheets[x]))]
    frame = combine_sheets(sheets, selected, mode, add_source)
    return IngestionResult(frame, sheets, selected, enc, sep, headers)
