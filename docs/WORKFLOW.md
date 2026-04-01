# Integrated Project Workflow (Obra + Current Assets)

This workflow integrates the Obra development corridor with repository assets and the WBS level model.

## Phase 1 — Discovery & Contracting
- Inventory sheets from all source workbooks.
- Build source-to-target mapping into the canonical schema.
- Confirm dictionary alignment between WBS tree and WBS dictionary.

**Deliverables**
- Data inventory report
- Canonical schema contract

## Phase 2 — Data Engineering
- Ingest workbook sheets into staging tables.
- Standardize WBS labels/codes and event codes.
- Run quality checks (null keys, duplicate WBS code paths, invalid parent links).

**Deliverables**
- Clean conformed dataset
- Data quality report with pass/fail thresholds

## Phase 3 — Modeling & Estimation
- Produce baseline deterministic estimates (historical median/quantile by WBS leaf).
- Train statistical estimator for Level-5 costs.
- Add uncertainty bands and campaign-level calibration.

**Deliverables**
- Versioned model artifact
- WBS-level estimate table (L1-L5)

## Phase 4 — Validation & Explainability
- Validate on holdout campaign(s).
- Publish MAE/MAPE, bias, and error spread by WBS level.
- Provide drill-down from L1 totals to L5 leaf drivers.

**Deliverables**
- Validation report
- Explainability summary

## Phase 5 — Operationalization
- Define runbook for periodic refresh.
- Persist assumptions, model version, data timestamp, and QA outputs.
- Expose outputs for product/app consumption.

**Deliverables**
- Runbook
- Release checklist
- Production-ready output bundle

## Definition of Done
- All Level-5 estimates are traceable to source rows and valid WBS hierarchy.
- Event-code standardization applied to unscheduled-event impact modeling.
- Validation metrics and assumptions published with each release.
