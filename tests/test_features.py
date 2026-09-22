from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from icdp.profiling import profile_dataframe
from icdp.cleanup import apply_negative_action, duplicate_report, standardize_dates
from icdp.classification import classify_columns
from icdp.transform import load_standards, transform_to_niq
from icdp.quality import build_quality_report
from icdp.reconciliation import reconcile
from icdp.exports import excel_allowed, sanitize_for_export, csv_bytes
from icdp.ai_client import AIClient

ROOT = Path(__file__).resolve().parents[1]

def data():
    return pd.read_csv(ROOT / "sample_data/client_shipment.csv", dtype=object)

def assert_raises(exc_type, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
        raise AssertionError(f"Expected {exc_type.__name__} but no exception was raised.")
    except exc_type:
        pass

def test_profile_cleanup_and_duplicates():
    df = data()
    p = profile_dataframe(df)
    assert p["exact_duplicates"] == 1
    assert p["negative_values"] >= 1
    updated = apply_negative_action(df, "JAN_2026", "Convert to positive")
    assert pd.to_numeric(updated["JAN_2026"], errors="coerce").min() >= 0
    assert len(duplicate_report(df, [])) == 2

def test_date_transform_reconcile_export():
    df = data()
    dated = standardize_dates(df, ["SHIP_DATE"], "YYYY-MM-DD", True)
    assert dated["SHIP_DATE"].notna().all()
    mapping = classify_columns(df)
    standards = load_standards(ROOT / "config/standards.yaml")
    out = transform_to_niq(df, mapping, standards)
    assert "JAN_2026" in out
    summary, _ = reconcile(df, out, "JAN_2026", "JAN_2026")
    assert summary["Match"]
    assert excel_allowed(out)

def test_classification_and_token_matching():
    df = data()
    mapping = classify_columns(df)
    m = dict(zip(mapping["Source Column"], mapping["NIQ Field"]))
    assert m["SALES_ZONE"] == "Region"
    assert m["MEASURE"] == "Fact"
    assert m["COUNTRY_NAME"] == "Country"
    assert m["TRADE_TYPE"] == "Channel"
    assert m["SHIP_TO_CITY"] == "City/State"
    assert m["PROD_GROUP"] == "Category"
    assert m["BRAND_DESC"] == "Brand"
    assert m["ITEM_CODE"] == "SKU"

def test_week_time_period_patterns():
    sample_cols = ["WEEK_01", "week_12", "WEEK_01_2026", "2026_WK12", "W01-2026", "Q1_2026", "JAN_2026", "202601"]
    test_df = pd.DataFrame(columns=sample_cols)
    mapping = classify_columns(test_df)
    for _, r in mapping.iterrows():
        assert r["NIQ Field"] == "Time Period", f"Failed for column {r['Source Column']}"
        assert r["Confidence"] == 1.0

def test_confidence_sorting_and_dimensional_reconciliation():
    df = data()
    mapping = classify_columns(df)
    standards = load_standards(ROOT / "config/standards.yaml")
    out = transform_to_niq(df, mapping, standards)
    assert set(out["Region"].unique()).issuperset({"North", "West", "South"})
    assert set(out["Fact"].unique()).issuperset({"Value", "Units"})
    summary, detail = reconcile(df, out, "JAN_2026", "JAN_2026", group_columns=["Channel", "Brand"])
    assert summary["Match"]
    assert len(detail) >= 3
    assert detail["Match"].all()

def test_formula_injection_defense():
    """Verify CWE-1236 mitigation against CSV/Excel formula injection."""
    dangerous_df = pd.DataFrame({
        "Text": ["=cmd|' /C calc'!A0", "@SUM(A1:A10)", "-payload", "+test", "\tattack", "Normal Text"],
        "Numbers": [-12.50, +42, 100, -0.05, 0, 999.9]
    })
    sanitized = sanitize_for_export(dangerous_df)
    
    # Dangerous formula string triggers must be escaped with single-quote
    assert sanitized["Text"].iloc[0].startswith("'=")
    assert sanitized["Text"].iloc[1].startswith("'@")
    assert sanitized["Text"].iloc[2].startswith("'-")
    assert sanitized["Text"].iloc[3].startswith("'+")
    assert sanitized["Text"].iloc[4].startswith("'\t")
    assert sanitized["Text"].iloc[5] == "Normal Text"
    
    # Real numbers must remain intact
    assert float(sanitized["Numbers"].iloc[0]) == -12.50
    assert float(sanitized["Numbers"].iloc[1]) == 42
    
    # CSV bytes export must not contain raw executable formulas
    raw_csv = csv_bytes(dangerous_df).decode("utf-8-sig")
    assert "'=cmd" in raw_csv
    assert "'@SUM" in raw_csv

def test_ssrf_and_credential_protection():
    """Verify CWE-918 (SSRF) and CWE-200 (Credential leakage) defenses."""
    # SSRF: reject non-http schemes
    assert_raises(ValueError, AIClient, "file:///etc/passwd", "test_key")
    assert_raises(ValueError, AIClient, "gopher://127.0.0.1:80", "test_key")
    assert_raises(ValueError, AIClient, "", "test_key")
        
    # Valid endpoints accepted
    client = AIClient("https://ai.example.com", "super_secret_token_12345")
    assert client.endpoint == "https://ai.example.com/"
    
    # Credential redaction in error messages
    error_msg = "Error 401: Unauthorized request with key super_secret_token_12345 and Bearer eyJhbGciOi..."
    redacted = client._redact_secrets(error_msg)
    assert "super_secret_token_12345" not in redacted
    assert "[REDACTED_KEY]" in redacted
    assert "[REDACTED_TOKEN]" in redacted

def test_vectorized_quality_report():
    """Verify vectorized quality report produces accurate error and warning counts."""
    df = data()
    mapping = classify_columns(df)
    standards = load_standards(ROOT / "config/standards.yaml")
    out = transform_to_niq(df, mapping, standards)
    q = build_quality_report(out)
    assert "Record ID" in q.columns
    assert "Severity" in q.columns
    assert "Field" in q.columns
    assert set(q["Severity"].unique()).issubset({"Error", "Warning"})

if __name__ == "__main__":
    tests = [
        test_profile_cleanup_and_duplicates,
        test_date_transform_reconcile_export,
        test_classification_and_token_matching,
        test_week_time_period_patterns,
        test_confidence_sorting_and_dimensional_reconciliation,
        test_formula_injection_defense,
        test_ssrf_and_credential_protection,
        test_vectorized_quality_report
    ]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\nALL {len(tests)} TESTS PASSED SUCCESSFULLY!")
