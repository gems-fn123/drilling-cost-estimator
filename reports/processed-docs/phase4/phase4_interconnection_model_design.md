# Phase 4 Interconnection Model Design (Draft)

Date: 2026-04-02
Status: Draft for implementation handoff

## Objective
Define an auditable campaign-cost component design connecting:
- well cost,
- support cost,
- surface facilities cost,
while preserving strict field separation (DARAJAT vs SALAK).

## Design Principles
1. **Field-separated branches first:** run DARAJAT and SALAK independently.
2. **Evidence-only driver inclusion:** no component driver enters statistical models without significance evidence.
3. **Traceability:** each estimate row references canonical WBS and source lineage columns.
4. **Parsimonious inputs:** prefer low-parameter formulations and grouped benchmarks before complex models.

## Component Decomposition Contract
For each `(field, campaign_code)` pair:

`campaign_total = component_well + component_support + component_surface_facilities`

### 1) Well Component
- Primary source classes: `well_tied` + approved hybrid-to-well scope.
- Candidate explanatory features (when available): well count, depth family, section complexity.
- Fallback when sparse: median benchmark by `(field, wbs_lvl4/wbs_lvl5, class)`.

### 2) Support Component
- Primary source classes: `campaign_tied` + approved hybrid support families.
- Candidate features: campaign duration, logistics footprint proxies, support intensity proxies.
- Fallback when sparse: grouped benchmark by campaign type + WBS branch.

### 3) Surface Facilities Component
- Primary source classes: curated hybrid families mapped to facilities scope.
- Candidate features: facilities scope flags, project phase, tie-in complexity proxies.
- Fallback when sparse: quantile envelope with conservative confidence bands.

## Data Flow (No Modeling in this Draft)
1. Run preflight gates G1-G8.
2. Build class-aware component design tables by field.
3. Produce deterministic baseline anchors per component.
4. Publish sufficiency flags for each component table.
5. Hand off to validation track for component-level regression/benchmark selection.

## Required Artifact Interfaces
- `data/processed/baseline_estimates_darajat.csv`
- `data/processed/baseline_estimates_salak.csv`
- `data/processed/confidence_bands.csv` (next step contract; not produced in this draft)
- `reports/validation_darajat.md` (next step)
- `reports/validation_salak.md` (next step)

## Sufficiency and Control Gates
- Do not fit component regressions unless minimum sample thresholds are met per field/component/WBS branch.
- If thresholds fail, force grouped benchmark mode and mark in assumptions register.
- Any pooled-field component analysis requires explicit statistical justification and approval.

## Open Decisions for Next Iteration
1. Final confidence-band method (bootstrap quantile vs analytic interval) per component.
2. Holdout split policy granularity (campaign-level vs WBS-leaf stratified) per field.
3. Bias tolerance thresholds by component and cost tier.
