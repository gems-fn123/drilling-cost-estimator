# Integrated Project Workflow — Phase Breakdown

## Purpose
Detailed operational workflow: five-phase pipeline with inputs, activities, outputs, and success criteria per phase.

## Audience
Phase leads, engineers, and AI agents.

## Prerequisites
- Read [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) section 3 (Development Corridor)
- Review [docs/PROJECT_INSTRUCTION.md](docs/PROJECT_INSTRUCTION.md) for strategic context

---

## Phase 1: Discovery & Contracting

### Goal
Inventory data sources, align naming, confirm hierarchy integrity.

### Input
- Source workbooks: `20260327_WBS_Data.xlsx`, `20260318_WBS_Dictionary.xlsx`, `UNSCHEDULED EVENT CODE.xlsx`, supplemental references
- Stakeholder interviews on domain conventions

### Activities
1. Load all source workbooks
2. Enumerate sheets, column schemas, row counts
3. Analyze missingness, duplicates, and key structure
4. Validate WBS hierarchy (L1–L5 parent-child consistency)
5. Validate well-name and campaign-name conventions
6. Document data quality issues and ambiguities

### Deliverables
- `reports/source_inventory.md` — workbook profiling, quality assessment
- Canonical schema specification (column mapping, naming rules)
- Assumption register seed: `docs/assumptions_register.md`

### Success Criteria
- [ ] All source workbooks profiled (sheets, rows, nulls documented)
- [ ] WBS hierarchy validated (no orphan L5 entries identified)
- [ ] Well/campaign naming conventions documented
- [ ] Data quality issues logged in assumption register

---

## Phase 2: Data Engineering & Canonicalization

### Goal
Standardize schema, canonicalize names, generate master reference tables.

### Input
- Profiled source workbooks
- Canonical schema specification from Phase 1

### Activities
1. Parse all source sheets into staging tables
2. Map source columns to canonical schema:
   ```
   wbs_level_1..5, wbs_code, activity, cost, duration, 
   well, campaign, event_code, classification,
   source_file, source_row, data_quality_flag
   ```
3. Standardize WBS labels/codes (strip whitespace, normalize case)
4. Create well-name canonicalization crosswalk (`well_alias_lookup.csv`)
5. Create campaign-name canonicalization crosswalk (`canonical_campaign_mapping.csv`)
6. Map unscheduled event codes to standardized vocabulary
7. Run QA checks:
   - Null counts by column, per-field (DARAJAT, SALAK)
   - Duplicate WBS codes
   - Orphan Level-5 entries (no valid L1–L4 parent)
   - Parent-child link integrity

### Deliverables
- `data/processed/well_master.csv` — canonical well reference
- `data/processed/well_alias_lookup.csv` — well name variants
- `data/processed/canonical_campaign_mapping.csv` — canonical campaign reference
- `reports/well_master_build_report.md` — well canonicalization detail
- `reports/campaign_well_mapping_report.md` — campaign mapping results
- Data quality report with pass/fail vs thresholds

### Success Criteria
- [ ] All source rows normalized to canonical schema
- [ ] Zero orphan Level-5 entries
- [ ] Well and campaign names canonicalized with 1-to-many deduplication
- [ ] Unscheduled events mapped to controlled vocabulary
- [ ] Data quality thresholds met (nulls, duplicates, hierarchy)

---

## Phase 3: Modeling & Estimation Prep

### Goal
Produce baseline calculations and prepare for statistical validation.

### Input
- Canonical cleaned data from Phase 2
- Phase 2 deliverables: well master, campaign master, quality report

### Activities
1. Separate data by field: DARAJAT records, SALAK records
2. For each field, compute deterministic baseline:
   - Historical median/quantile by WBS Level-5
   - Historical median/quantile by WBS Level-4
   - Check for rollup consistency (L5 sums = expected L4)
3. Classify Level-5 items:
   - `well_tied` — cost varies by well ID
   - `campaign_tied` — cost varies by campaign ID
   - `hybrid` — mixed variation
4. Create feature matrices (depth, section, operation type, event codes, campaign attributes)
5. Identify cost drivers per field:
   - Correlation analysis (continuous & categorical features)
   - Flag statistically significant features (p < 0.05 for each field)
6. Prepare validation split (holdout ~20% by field)

### Deliverables
- `data/processed/baseline_estimates_darajat.csv` — L5 baselines
- `data/processed/baseline_estimates_salak.csv` — L5 baselines
- `data/processed/wbs_lv5_classification.csv` — well_tied/campaign_tied/hybrid labels
- `reports/feature_correlation_darajat.md` — correlation evidence
- `reports/feature_correlation_salak.md` — correlation evidence
- Validation split (IDs)

### Success Criteria
- [ ] Deterministic baselines calculated per field
- [ ] Level-5 classification completed (well_tied, campaign_tied, hybrid)
- [ ] Cost driver candidates identified with statistical evidence
- [ ] Validation split created (holdout set prepared)

---

## Phase 4: Validation & Explainability

### Goal
Build and validate statistical models separately by field; generate confidence bands.

### Input
- Feature matrices and driver candidates from Phase 3
- Validation split from Phase 3

### Activities
1. **Per Field (DARAJAT, then SALAK):**
   - Train regression model: simple → multiple (justified features only)
   - OR apply grouped benchmarking (if insufficient sample)
   - Generate predictions on holdout set
   - Compute MAE, MAPE, bias, error spread by WBS level and cost tier
   - Validate confidence interval coverage (90%, 95%)

2. **Model Diagnostics:**
   - Residual plots (Q–Q plots, heteroscedasticity checks)
   - Calibration curves
   - Leverage analysis (outlier flag)

3. **Explainability Artifacts:**
   - Create drill-down traceback: estimate (L5) → drivers → source rows
   - Confidence interval tables by WBS section
   - Sensitivity analysis (e.g., cost impact if depth +500m)

### Deliverables
- `reports/validation_darajat.md` — MAE/MAPE, bias, error spread (DARAJAT)
- `reports/validation_salak.md` — MAE/MAPE, bias, error spread (SALAK)
- Model artifacts (pickled models or equations per field)
- Confidence band tables (`data/processed/confidence_bands.csv`)
- Explainability summary: drill-down examples, sensitivity tables
- Model version metadata: training date, feature set, assumptions

### Success Criteria
- [ ] DARAJAT model validated (MAE/MAPE acceptable, no systematic bias)
- [ ] SALAK model validated (separate metrics, independent results)
- [ ] 90% confidence interval coverage verified per field
- [ ] Explainability artifacts published (drill-down, sensitivity)
- [ ] Model version and assumptions documented

---

## Phase 5: Operationalization

### Goal
Operationalize refresh, build app, release to production.

### Input
- Validated models and confidence bands from Phase 4
- Canonical data and quality thresholds from Phases 2–3

### Activities
1. **Scheduling & Refresh:**
   - Document monthly/quarterly refresh triggers
   - Automate ingestion, QA, model refit (if needed)
   - Create rollback plan (previous model version on failure)

2. **App Development:**
   - Build Streamlit interface:
     - WBS tree navigator (expand/collapse L1 → L5)
     - Cost estimate display with confidence bands
     - Drill-down path: L1 total → L5 leaf items
     - Scenario builder: override well, depths, operation type → recalculate
   - Add assumptions register viewer
   - Add model version & metadata (training date, field, CI coverage)

3. **Release Bundle:**
   - Model binaries (per field)
   - Canonical data snapshot (well master, campaign master, baseline table)
   - QA checklist (data quality thresholds, validation metrics)
   - Assumptions register
   - Training documentation (how to interpret, limitations)
   - Monitoring dashboard (monthly refresh KPIs)

4. **Deployment & Training:**
   - Deploy app to production (Streamlit Cloud or internal server)
   - Configure monitoring (refresh success rate, estimate drift)
   - Conduct stakeholder training

### Deliverables
- Streamlit app (operational, URL published)
- Refresh runbook (`docs/refresh_runbook.md`)
- Release checklist and deployment guide
- Monitoring dashboard and alerting rules
- Stakeholder training materials

### Success Criteria
- [ ] Streamlit app deployed and accessible
- [ ] Refresh automation tested and documented
- [ ] All assumptions maintained and published with each release
- [ ] Model version control implemented
- [ ] Stakeholder training completed

---

## Cross-Phase Data Flow

```
Phase 1         → Phase 2          → Phase 3      → Phase 4        → Phase 5
(Discover)      (Canonicalize)     (Baseline)     (Validate)       (Deploy)

Source Data  →  Canonical CSVs  →  Feature Eng  →  Models &      →  App Release
WBS Dict     →  Well Master     →  Drivers      →  Validation    →  Refresh Auto
Event Codes  →  Campaign Mapping →  Baselines    →  Confidence    →  Monitoring
             →  QA Report        →  Splits       →  Explainability
```

---

## Phase Gate Criteria

| Gate | Condition |
|------|-----------|
| **Phase 1→2** | Canonical schema approved; data inventory complete |
| **Phase 2→3** | All canonical CSVs generated; QA thresholds met; orphan L5 = 0 |
| **Phase 3→4** | Baselines calculated; features identified; validation split created |
| **Phase 4→5** | Models validated per field; confidence bands published; explainability approved |
| **Phase 5 Complete** | App operational; refresh automated; assumptions maintained |

## Definition of Done
- All Level-5 estimates are traceable to source rows and valid WBS hierarchy.
- Event-code standardization applied to unscheduled-event impact modeling.
- Validation metrics and assumptions published with each release.
