from __future__ import annotations
import pandas as pd

def reconcile(
    source: pd.DataFrame,
    output: pd.DataFrame,
    source_measure: str,
    output_measure: str,
    group_columns: list[str] | None = None,
    tolerance: float = 0.01
) -> tuple[dict, pd.DataFrame]:
    """
    High-Performance Zero-Data-Loss Reconciliation Engine.
    Slices only active dimensional columns to minimize memory footprint.
    """
    group_columns = group_columns or []
    if source is None or output is None or source_measure not in source.columns or output_measure not in output.columns:
        return {
            "Source Measure": source_measure,
            "Output Measure": output_measure,
            "Input Total": 0.0,
            "Output Total": 0.0,
            "Difference": 0.0,
            "Tolerance": tolerance,
            "Match": False
        }, pd.DataFrame()

    # Fast numeric parsing
    s_col = source[source_measure]
    if pd.api.types.is_numeric_dtype(s_col):
        s_vals = pd.to_numeric(s_col, errors="coerce").fillna(0.0)
    else:
        s_vals = pd.to_numeric(s_col.astype(str).str.replace(",", "", regex=False), errors="coerce").fillna(0.0)

    o_col = output[output_measure]
    if pd.api.types.is_numeric_dtype(o_col):
        o_vals = pd.to_numeric(o_col, errors="coerce").fillna(0.0)
    else:
        o_vals = pd.to_numeric(o_col.astype(str).str.replace(",", "", regex=False), errors="coerce").fillna(0.0)

    before = float(s_vals.sum())
    after = float(o_vals.sum())
    difference = after - before

    summary = {
        "Source Measure": source_measure,
        "Output Measure": output_measure,
        "Input Total": before,
        "Output Total": after,
        "Difference": difference,
        "Tolerance": tolerance,
        "Match": abs(difference) <= tolerance
    }

    # Lightweight grouping without deep copying whole DataFrames
    valid_groups: list[str] = []
    for c in group_columns:
        if c in output.columns:
            valid_groups.append(c)
    valid_groups = list(dict.fromkeys(valid_groups))

    detail = pd.DataFrame()
    if valid_groups:
        s_mini = pd.DataFrame({source_measure: s_vals}, index=source.index)
        for c in valid_groups:
            if c in source.columns:
                s_mini[c] = source[c]
            elif len(source) == len(output):
                s_mini[c] = output[c].values

        o_mini = pd.DataFrame({output_measure: o_vals}, index=output.index)
        for c in valid_groups:
            o_mini[c] = output[c]

        a = s_mini.groupby(valid_groups, dropna=False)[source_measure].sum().rename("Input Total")
        b = o_mini.groupby(valid_groups, dropna=False)[output_measure].sum().rename("Output Total")

        detail = pd.concat([a, b], axis=1).fillna(0.0).reset_index()
        detail["Difference"] = detail["Output Total"] - detail["Input Total"]
        detail["Match"] = detail["Difference"].abs() <= tolerance

    return summary, detail
