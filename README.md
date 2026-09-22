# Intelligent Client Data Preparation for Coverage Analysis (ICDP)
**NIQ Hackfest 2026 Submission**

An enterprise-ready, AI-augmented data preparation application designed to standardize heterogeneous client shipment and sales files into the canonical **NielsenIQ (NIQ)** schema for Coverage Analysis.

---

## 🚀 Key Features

1. **Multi-Format Ingestion**: Auto-sniffing for CSV (delimiters & multi-encoding fallback) and multi-tab Excel (`.xlsx`, `.xls`, `.xlsm`) with high-speed header sampling (`nrows=25`) and memory caching for 50+ MB files.
2. **Comprehensive Data Profiling**: Automated detection of missing/blank values, numeric candidates, date patterns, duplicate rows, and negative adjustments.
3. **Flexible, Non-Destructive Data Cleanup**:
   - Negative value handling: Convert to positive, replace with zero, blank, or do nothing.
   - Composite duplicate definitions with custom deduplication policies (`Keep first`, `Keep last`, `Delete all`).
   - Mixed date format standardization (Excel serial dates, `YYYYMMDD`, long dates, etc.).
   - Column renaming, dropping, and reordering with a single-click reset to raw baseline.
4. **Token-Aware & AI-Augmented Classification**:
   - Multi-token semantic matching for canonical fields: `Country`, `Region`, `Channel`, `City/State`, `Category`, `Brand`, `SKU`, `Fact`.
   - Comprehensive regex support for weekly and monthly time periods (`WEEK_01_2026`, `2026_WK12`, `W01-2026`, `JAN_2026`).
   - Azure AI Inference integration (`hack-fest-gpt-5.6-luna`) to classify ambiguous or unconfirmed columns with token cost tracking.
5. **Canonical NIQ Transformation**:
   - Standardizes country, region, and channel across global dictionaries (`config/standards.yaml`).
   - Cleans SKUs (`[^A-Za-z0-9_-]`) and title-cases product attributes.
   - Preserves time periods as numeric metric columns.
6. **Zero-Distortion Numerical Reconciliation**:
   - Mathematical pre/post checksum verification ($\Delta \le 0.01$).
   - Multi-dimensional slice-and-dice group reconciliation across categories (e.g. `Channel` $\times$ `Brand`).
7. **Human-in-the-Loop Governance & Audit Trail**:
   - Interactive data editor with approval status tracking (`Approved`, `Needs Review`, `Incomplete`).
   - Immutable cell-level audit log recording every user change with timestamps.
8. **Controlled Multi-Format Delivery**:
   - Validates Excel thresholds (1,048,576 rows, 16,384 columns).
   - Exports CSV, multi-tab Excel workbook, and full audit ZIP package with JSON manifests.

---

## 🔒 Cybersecurity & Responsible AI Compliance

- **In-Memory Credential Isolation**: Azure AI API keys reside exclusively in volatile session RAM and are never persisted to disk or included in export bundles.
- **Data Minimization**: Only column headers and anonymized 3-sample distinct values are shared with the LLM. No PII or customer transactions leave the environment.
- **Fail-Safe Offline Mode**: Fully operational using local rule and dictionary engines if the corporate VPN / network is unreachable.
- **Fast Network Timeouts**: 10-second connect and 15-second read timeouts prevent UI locking during network disruptions.

---

## 🛠️ Quick Start

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12

### 2. Local Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Run the Streamlit application
python -m streamlit run app.py
```

### 3. Docker Deployment
```bash
docker compose up --build
# Access the application at http://localhost:8501
```

---

## 🧪 Automated Testing

Execute the comprehensive test suite:
```powershell
.venv\Scripts\python -c "
import sys; sys.path.insert(0, '.')
import tests.test_features as t
t.test_profile_cleanup_and_duplicates()
t.test_date_transform_reconcile_export()
t.test_classification_and_token_matching()
t.test_week_time_period_patterns()
t.test_confidence_sorting_and_dimensional_reconciliation()
print('>>> ALL 5 TESTS PASSED SUCCESSFULLY! <<<')
"
```

---

## 📂 Project Structure

```
├── app.py                      # Main Streamlit 9-step wizard application
├── config/
│   └── standards.yaml          # Domain dictionaries for Country, Region, Channel
├── sample_data/
│   └── client_shipment.csv     # Sample multi-dimensional client shipment dataset
├── src/
│   └── icdp/
│       ├── __init__.py         # Package metadata (v2.0.0)
│       ├── ai_client.py        # Azure AI Inference client & prompt orchestration
│       ├── classification.py   # Token matching & AI column classification
│       ├── cleanup.py          # Negative, duplicate, date, and column rules
│       ├── exports.py          # CSV, multi-tab Excel, and ZIP package builders
│       ├── ingestion.py        # CSV & multi-sheet Excel sniffing & loading
│       ├── profiling.py        # High-speed vectorized data profiling
│       ├── quality.py          # Quality exception reporting & recommendations
│       ├── reconciliation.py   # Pre/post mathematical reconciliation engine
│       └── transform.py        # Canonical NIQ hierarchy transformation
├── tests/
│   └── test_features.py        # End-to-end unit and integration test suite
├── .streamlit/
│   └── config.toml             # Theme styling and server configuration
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Multi-container orchestration
└── requirements.txt            # Production dependencies
```
