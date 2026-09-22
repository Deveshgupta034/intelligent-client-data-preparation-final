from __future__ import annotations
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

EXCEL_ROWS = 1_048_576
EXCEL_COLS = 16_384

def sanitize_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mitigates CWE-1236 (CSV / Formula Injection) by prefixing a single-quote (')
    to any text cell starting with dangerous formula characters (=, +, -, @, \\t, \\r),
    while preserving genuine numeric values.
    """
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object or str(out[col].dtype) == "string":
            def _clean_cell(val):
                if pd.isna(val):
                    return val
                s = str(val)
                if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
                    # Preserve actual numbers like -10.5 or +5
                    try:
                        float(s.replace(",", ""))
                        return val
                    except ValueError:
                        return f"'{s}"
                return val
            out[col] = out[col].map(_clean_cell)
    return out

def csv_bytes(df: pd.DataFrame) -> bytes:
    clean_df = sanitize_for_export(df)
    return clean_df.to_csv(index=False).encode("utf-8-sig")

def excel_allowed(df: pd.DataFrame) -> bool:
    if df is None:
        return True
    return len(df) <= EXCEL_ROWS and len(df.columns) <= EXCEL_COLS

def excel_bytes(output, quality, mapping, audit, profile, duplicates, recon_summary, recon_detail, usage) -> bytes:
    if not excel_allowed(output):
        raise ValueError("Excel limits exceeded (max 1,048,576 rows). Use CSV or ZIP export.")
    
    b = io.BytesIO()
    with pd.ExcelWriter(b, engine="openpyxl") as w:
        sanitize_for_export(output).to_excel(w, sheet_name="Standardized NIQ Output", index=False)
        sanitize_for_export(quality).to_excel(w, sheet_name="Data Quality", index=False)
        sanitize_for_export(mapping).to_excel(w, sheet_name="Column Classification", index=False)
        sanitize_for_export(pd.DataFrame(audit)).to_excel(w, sheet_name="User Change Audit", index=False)
        pd.DataFrame([profile or {}]).to_excel(w, sheet_name="Profiling", index=False)
        sanitize_for_export(duplicates).to_excel(w, sheet_name="Duplicates", index=False)
        pd.DataFrame([recon_summary or {}]).to_excel(w, sheet_name="Reconciliation", index=False)
        sanitize_for_export(recon_detail).to_excel(w, sheet_name="Reconciliation Detail", index=False)
        pd.DataFrame(usage or []).to_excel(w, sheet_name="API Token Usage", index=False)
    return b.getvalue()

def package_bytes(output, quality, mapping, audit, profile, duplicates, recon_summary, recon_detail, usage, source_name: str) -> bytes:
    b = io.BytesIO()
    # CWE-22: Sanitize source name against path traversal or malicious characters
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(str(source_name)).name) if source_name else "source_data"
    manifest = {
        "application": "Intelligent Client Data Preparation for Coverage Analysis",
        "security_hardened": True,
        "formula_injection_defense": "RFC-4180 / CWE-1236 Compliant",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": safe_name,
        "rows": len(output) if output is not None else 0,
        "columns": len(output.columns) if output is not None else 0,
        "excel_allowed": excel_allowed(output),
        "time_periods_preserved_as_columns": True
    }
    
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("standardized_niq_output.csv", csv_bytes(output))
        z.writestr("data_quality_report.csv", csv_bytes(quality))
        z.writestr("column_classification.csv", csv_bytes(mapping))
        z.writestr("duplicate_report.csv", csv_bytes(duplicates))
        z.writestr("profiling_report.json", json.dumps(profile or {}, indent=2, default=str))
        z.writestr("reconciliation_summary.json", json.dumps(recon_summary or {}, indent=2, default=str))
        z.writestr("reconciliation_detail.csv", csv_bytes(recon_detail))
        z.writestr("user_change_audit.csv", csv_bytes(pd.DataFrame(audit or [])))
        z.writestr("api_token_usage.csv", csv_bytes(pd.DataFrame(usage or [])))
        z.writestr("run_manifest.json", json.dumps(manifest, indent=2))
        if excel_allowed(output):
            z.writestr("standardized_niq_output.xlsx", excel_bytes(output, quality, mapping, audit, profile, duplicates, recon_summary, recon_detail, usage))
            
    return b.getvalue()
