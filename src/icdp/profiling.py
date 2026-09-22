from __future__ import annotations
import pandas as pd

def _get_numeric_series(col: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(col):
        return col
    return pd.to_numeric(col.astype(str).str.replace(",", "", regex=False), errors="coerce")

def numeric_candidates(df: pd.DataFrame) -> list[str]:
    result = []
    for c in df.columns:
        converted = _get_numeric_series(df[c])
        if converted.notna().mean() >= 0.7:
            result.append(c)
    return result

def date_candidates(df: pd.DataFrame) -> list[str]:
    result = []
    for c in df.columns:
        col = df[c]
        if pd.api.types.is_datetime64_any_dtype(col):
            result.append(c)
            continue
        name = str(c).lower()
        if any(x in name for x in ("date", "period", "month", "week", "year")):
            result.append(c)
            continue
        sample = col.dropna().head(100)
        if len(sample) and pd.to_datetime(sample, errors="coerce", format="mixed").notna().mean() >= 0.7:
            result.append(c)
    return list(dict.fromkeys(result))

def profile_dataframe(df: pd.DataFrame) -> dict:
    """
    High-Performance Single-Pass DataFrame Profiler.
    Reuses numeric conversions and vectorizes missing cell calculations.
    """
    nums: list[str] = []
    negatives: dict[str, int] = {}
    null_count = int(df.isna().sum().sum())
    missing_tokens = {"", "nan", "none", "null", "n/a", "na", "-"}

    for c in df.columns:
        col = df[c]
        # 1. Numeric candidate & negative value detection in single pass
        converted = _get_numeric_series(col)
        if converted.notna().mean() >= 0.7:
            nums.append(c)
            neg_count = int((converted < 0).sum())
            if neg_count > 0:
                negatives[c] = neg_count

        # 2. Text null representation detection
        if col.dtype == object or str(col.dtype) == "string":
            s = col.dropna()
            if not s.empty:
                null_count += int(s.astype(str).str.strip().str.lower().isin(missing_tokens).sum())

    n_rows = len(df)
    n_cols = len(df.columns)
    exact_dups = int(df.duplicated().sum()) if n_rows > 0 else 0

    return {
        "rows": n_rows,
        "columns": n_cols,
        "exact_duplicates": exact_dups,
        "missing_cells": null_count,
        "numeric_columns": nums,
        "date_columns": date_candidates(df),
        "negative_by_column": negatives,
        "negative_values": sum(negatives.values())
    }
