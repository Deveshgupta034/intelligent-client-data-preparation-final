# Methodology Note: AI Usage, Assumptions & Confidence Framework
**Challenge:** Intelligent Client Data Preparation for Coverage Analysis  
**Model:** Hackfest Azure AI Luna (`hack-fest-gpt-5.6-luna`)  
**Target User:** NIQ Customer Support (CS) & Commercial Operations Teams  

---

## 1. Role of AI & Usage Architecture

In alignment with NIQ Hackfest guidelines, artificial intelligence is deployed selectively, ethically, and deterministically:

1. **Selective Invocation (High Token Efficiency)**:
   - 90%+ of standard client dimensions (`Country`, `Region/Zone`, `Channel`, `Brand`, `Category`, `SKU`, `Fact`) and periodic columns (`JAN_2026`, `WEEK_01_2026`, `2026_WK12`) are resolved instantly in **< 0.05 seconds** using token-aware heuristic classifiers.
   - The Azure AI Luna model (`hack-fest-gpt-5.6-luna`) is invoked **only for ambiguous, low-confidence, or localized abbreviations** (e.g., `MKT_SUBDIV`, `EX_FAC_VOL`).
   - This hybrid strategy ensures negligible API latency, near-zero token consumption (fair usage compliance), and zero downtime when working offline or outside the corporate VPN.

2. **Zero Numerical Hallucination**:
   - LLMs are strictly quarantined from numerical calculations. AI is **never** used to estimate, invent, extrapolate, or modify shipment quantities, sales values, or return amounts.
   - All numerical transformations are governed by strict vectorized Pandas operations.

3. **Responsible AI & Volatile Credential Security**:
   - The Azure Luna Bearer token is accepted via masked inputs and retained strictly in **volatile session memory**. It is never written to disk, committed to Git, or exported in downloadable manifests.
   - External public LLM APIs (OpenAI, Anthropic, Google Gemini) are strictly prohibited and completely absent from the codebase.
   - API consumption telemetry (Prompt Tokens, Completion Tokens, Total Tokens) is logged per operation into `api_token_usage.csv` to ensure auditability and token quota compliance.

---

## 2. Core Assumptions

1. **Canonical Output Schema**:
   - The target schema strictly adheres to the official NIQ Coverage Analysis dimensions:
     $$\text{Country} \parallel \text{Region} \parallel \text{Channel} \parallel \text{City/State} \parallel \text{Category} \parallel \text{Brand} \parallel \text{SKU} \parallel \text{Fact}$$
   - In accordance with the challenge brief, `Region` subsumes regional aliases such as `Zone` (`SALES_ZONE`).
   - All time periods (`Month`, `Week`, `Quarter`, `Date`) are preserved strictly in **columnar format** to support immediate Coverage ratio calculations ($RMS / \text{Shipment}$).

2. **Handling Negative Values (Returns & Corrections)**:
   - In ex-factory shipment datasets, negative values typically represent commercial returns, credit notes, or retrospective volume adjustments.
   - The solution preserves signed return values by default during mathematical reconciliation, ensuring that net ex-factory totals match exactly.
   - Flexible analyst overrides allow converting negatives to positive, zero, or blank depending on client-specific reporting conventions.

3. **Distinguishing Explicit Zero from Missing Data**:
   - Explicit `0` or `0.0` values represent confirmed zero shipments (e.g., out of stock or inactive distribution points) and are preserved as valid numeric facts.
   - Blank, null, or whitespace-only cells are classified as missing data, surfaced in `data_quality_report.csv`, and excluded from numerical sums without distortion.

4. **Row-to-Source Traceability & Lineage**:
   - Every standardized row receives an immutable `Record ID` (e.g., `REC-000001`).
   - For multi-tab workbooks, an optional `Source Sheet` lineage column records the exact worksheet of origin.
   - Any manual edit made in the Human Review stage captures `Record ID`, `Field`, `Original Value`, `Final Value`, and `UTC Timestamp` in `user_change_audit.csv`.

---

## 3. Confidence Scoring & Human-in-the-Loop Governance

| Confidence Level | Classification Mechanism | System Action | Analyst Requirement |
| :--- | :--- | :--- | :--- |
| **$\ge 90\%$** | Exact token match or high-certainty regex pattern | Auto-confirmed in mapping table | Displayed with green badge; editable if desired |
| **$70\% - 89\%$** | Partial token overlap or AI Luna high-probability recommendation | Flagged for review; suggested mapping pre-populated | Analyst verifies with one-click checkbox |
| **$< 70\%$** | Ambiguous acronyms or unmapped headers | Flagged as *Unmapped / Review Required* | Analyst assigns canonical target from dropdown or triggers Luna AI |

### Quality Guardrail Summary
- **No Silent Overwriting**: Every AI recommendation is visible in the interactive Streamlit mapping matrix before transformation executes.
- **Reversibility**: A one-click *Reset to Raw Data* control restores pristine source frames from in-memory cache at any step.
- **Mathematical Integrity**: Mathematical reconciliation executes across user-selected categorical slices (e.g., $\text{Channel} \times \text{Brand}$) with configurable tolerance ($\pm 0.01$). Export packages are blocked from false certification if tolerance is exceeded.

