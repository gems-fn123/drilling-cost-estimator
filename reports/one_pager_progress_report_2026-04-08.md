# One‑Pager Progress Report (as of 2026-04-08)

## Scope
This snapshot summarizes three tracks from the current delivered artifacts:
1. cost-driver validity,
2. estimation method by WBS family and WBS level,
3. web app estimator tool readiness.

---

## 1) Cost-Driver Validity Status

### A. Driver-classification validity (what is currently **approved**)
- WBS Lv.5 alignment is operational on a frozen source snapshot: **822/822 rows mapped**, unresolved keys **0**.
- Approved class mix (all fields combined):
  - **well_tied**: 651 keys (79.20%), USD 79.14M (74.27%)
  - **campaign_tied**: 46 keys (5.60%), USD 12.26M (11.51%)
  - **hybrid**: 125 keys (15.21%), USD 15.16M (14.23%)
- Field-separated outputs are available and maintained (DARAJAT vs SALAK not pooled).

### B. Predictive validity (what is currently **measured**)
Current backtest mode is explicitly a **historical median peer baseline** (no regression claim yet):
- **DARAJAT** (11 wells): MAE USD 1.03M, MAPE 109.11%, Bias USD +0.156M
- **SALAK** (9 wells): MAE USD 1.61M, MAPE 641.25%, Bias USD +0.498M

Interpretation: classification and decomposition are in place, but predictive accuracy remains weak/volatile (especially SALAK), so this is still a controlled baseline phase rather than production-grade driver model validation.

### C. Gaps to close for “driver validity” sign-off
- Confidence-coverage evidence (e.g., decision-facing 90%/95% coverage pack) is not yet published as a dedicated release artifact.
- Scenario coefficient/rule evidence is not yet audited and packaged for release.

---

## 2) Estimation Method by WBS Family (and by WBS Level)

## Method currently in force
Campaign estimate is decomposed into:
1. **well-tied component**,
2. **hybrid component**,
3. **campaign-tied component**,
then estimated **per field** and allocated to WBS Lv.5 detail rows with in-field support weights.

### A. By WBS family / estimation class
- **well_tied / well_scope**
  - Method: direct well-linked benchmarking at field-separated grouped level; contributes both direct well estimates and rollup contribution.
- **campaign_tied** (campaign_logistics, campaign_compliance, shared_support, waste_support)
  - Method: campaign-level benchmark component; excluded from direct well estimation.
- **hybrid** (interpad_move_count, pad_expansion_flag, tie_in_flag, rig_skid_count)
  - Method: campaign-scope, design-driver-scaled component; excluded from direct per-well estimation.

### B. By WBS level (current implementation reality)
- **Lv.5**: active modeling grain for classification + estimation allocation.
- **Lv.1–Lv.4**: currently treated as roll-up/reporting levels derived from Lv.5 totals in this release package (no separate level-specific model claimed).

### C. Field-specific composition signal (latest packaged)
- **DARAJAT** cost share by class: well_tied 73.49%, hybrid 14.09%, campaign_tied 12.42%.
- **SALAK** cost share by class: well_tied 75.63%, hybrid 14.48%, campaign_tied 9.89%.

Implication: both fields are dominated by well_scope, but hybrid/campaign shares are still material and must stay in decomposition.

---

## 3) Web App Estimator Tool Progress

### Current readiness (prototype)
- Status: **ready for UX/design review**, **not production-ready**.
- Data contract is present for app ingestion (`phase5_app_dataset.csv`) with field partitioning and confidence/readiness columns.
- Prototype shell exists for Streamlit demo.
- Current dataset snapshot: fields = DARAJAT + SALAK, rows = 118.

### What works now
- Field-first flow with non-pooled behavior.
- Group-level table view with P10/P50/P90 and readiness/confidence metadata.
- Monitoring feed contract available.

### Remaining blockers before production
1. Publish validation reports as active release artifacts.
2. Publish CI/coverage evidence in a decision-facing package.
3. Deliver audited scenario rule/coefficient contract.
4. Bundle release governance docs (deployment + checklist + training) in one signed package.

---

## Overall RAG Snapshot (2026-04-08)
- **Driver classification validity:** 🟢 Green (rules implemented, fully mapped, field-separated).
- **Predictive driver validity:** 🟠 Amber/Red boundary (baseline-only method; high MAPE volatility, especially SALAK).
- **Estimation method governance (per family + per level):** 🟠 Amber (clear decomposition, but higher-level dedicated models and scenario evidence not yet released).
- **Web app estimator tool:** 🟠 Amber (demo-ready, not release-ready).
