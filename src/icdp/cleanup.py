from __future__ import annotations
import pandas as pd

def apply_negative_action(df: pd.DataFrame, column: str, action: str) -> pd.DataFrame:
    if column not in df.columns:
        return df.copy()
    out = df.copy()
    col = out[column]
    if pd.api.types.is_numeric_dtype(col):
        values = pd.to_numeric(col, errors="coerce")
    else:
        values = pd.to_numeric(col.astype(str).str.replace(",", "", regex=False), errors="coerce")
        
    if action == "Convert to positive":
        values = values.abs()
    elif action == "Replace with zero":
        values = values.mask(values < 0, 0)
    elif action == "Replace with blank":
        values = values.mask(values < 0, pd.NA)
        
    out[column] = values
    return out

def duplicate_report(df: pd.DataFrame, keys: list[str] | None) -> pd.DataFrame:
    if not keys:
        return df[df.duplicated(keep=False)].copy()
    valid_keys = [k for k in keys if k in df.columns]
    if not valid_keys:
        return df[df.duplicated(keep=False)].copy()
    return df[df.duplicated(subset=valid_keys, keep=False)].copy()

def remove_duplicates(df: pd.DataFrame, keys: list[str] | None, keep: str) -> pd.DataFrame:
    subset = [k for k in (keys or []) if k in df.columns] or None
    keep_map = {"Keep first": "first", "Keep last": "last", "Delete all duplicates": False}
    keep_val = keep_map.get(keep, "first")
    return df.drop_duplicates(subset=subset, keep=keep_val).reset_index(drop=True)

def standardize_dates(df: pd.DataFrame, columns: list[str], fmt: str, dayfirst: bool = False) -> pd.DataFrame:
    out = df.copy()
    format_map = {
        "YYYY-MM-DD": "%Y-%m-%d",
        "DD/MM/YYYY": "%d/%m/%Y",
        "MM/DD/YYYY": "%m/%d/%Y",
        "Long date": "%d %B %Y",
        "Month text": "%b %Y"
    }
    pattern = format_map.get(fmt, "%Y-%m-%d")
    
    for c in columns:
        if c not in out.columns:
            continue
        raw = out[c].astype(str).str.strip()
        parsed = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")
        
        # 1. Match YYYYMMDD compact format
        ymd = raw.str.fullmatch(r"\d{8}", na=False)
        parsed.loc[ymd] = pd.to_datetime(raw.loc[ymd], format="%Y%m%d", errors="coerce")
        
        # 2. Match Excel serial date numbers (e.g. 45290)
        excel_mask = raw.str.fullmatch(r"\d{4,5}(?:\.0)?", na=False) & ~ymd
        excel_values = pd.to_numeric(raw.loc[excel_mask], errors="coerce")
        parsed.loc[excel_mask] = pd.to_datetime(excel_values, unit="D", origin="1899-12-30", errors="coerce")
        
        # 3. Fallback mixed parsing
        remaining = ~ymd & ~excel_mask
        parsed.loc[remaining] = pd.to_datetime(raw.loc[remaining], errors="coerce", dayfirst=dayfirst, format="mixed")
        
        # Preserve NaT/empty correctly
        formatted = parsed.dt.strftime(pattern)
        out[c] = formatted.where(parsed.notna(), raw)
        
    return out

def manage_columns(df: pd.DataFrame, delete: list[str], rename_map: dict[str, str], order: list[str]) -> pd.DataFrame:
    out = df.drop(columns=delete, errors="ignore").rename(columns=rename_map)
    valid = [c for c in order if c in out.columns]
    return out[valid + [c for c in out.columns if c not in valid]]
