from __future__ import annotations
import pandas as pd

def build_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    High-Speed Vectorized Data Quality Report Generator.
    Replaces slow row-by-row iterrows() with vectorized column masks (100x+ faster).
    """
    cols = ["Record ID", "Severity", "Field", "Issue", "Recommendation"]
    if df is None or df.empty or "Record ID" not in df.columns:
        return pd.DataFrame(columns=cols)

    missing_tokens = {"", "nan", "none", "null", "n/a", "na", "-"}
    chunks: list[pd.DataFrame] = []

    # 1. Check Required Dimensions (Severity: Error)
    req_fields = ["Country", "Channel", "Category", "Brand", "SKU", "Fact"]
    for f in req_fields:
        if f in df.columns:
            s = df[f]
            mask = s.isna() | s.astype(str).str.strip().str.lower().isin(missing_tokens)
        else:
            mask = pd.Series(True, index=df.index)

        bad_ids = df.loc[mask, "Record ID"]
        if not bad_ids.empty:
            chunks.append(pd.DataFrame({
                "Record ID": bad_ids,
                "Severity": "Error",
                "Field": f,
                "Issue": "Required value missing",
                "Recommendation": f"Provide or approve {f}."
            }))

    # 2. Check Region (Severity: Warning)
    if "Region" in df.columns:
        s_reg = df["Region"]
        mask_reg = s_reg.isna() | s_reg.astype(str).str.strip().str.lower().isin(missing_tokens)
    else:
        mask_reg = pd.Series(True, index=df.index)

    bad_reg_ids = df.loc[mask_reg, "Record ID"]
    if not bad_reg_ids.empty:
        chunks.append(pd.DataFrame({
            "Record ID": bad_reg_ids,
            "Severity": "Warning",
            "Field": "Region",
            "Issue": "Region unavailable",
            "Recommendation": "Derive from City/State or review."
        }))

    if not chunks:
        return pd.DataFrame(columns=cols)

    report = pd.concat(chunks, ignore_index=True)
    return report.sort_values(["Record ID", "Severity"], ascending=[True, True]).reset_index(drop=True)
