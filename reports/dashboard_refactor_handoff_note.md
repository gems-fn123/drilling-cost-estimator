# Dashboard-Anchored Historical Estimator Refactor — Handoff Note

## What changed in the data model
- Added a canonical historical mart at `data/processed/historical_cost_mart.csv` built from `wbs_lv5_master.csv` + `wbs_lv5_classification.csv` with full WBS lineage, field/campaign metadata, and source row IDs.
- Added explicit bridge datasets:
  - `data/processed/wbs_row_to_well_bridge.csv`
  - `data/processed/wbs_row_to_campaign_bridge.csv`
  - `data/processed/cost_mart_coverage_report.csv`
- Added dashboard reconstruction outputs:
  - `data/processed/dashboard_rebuild_well_cost.csv`
  - `data/processed/dashboard_rebuild_l2_cost.csv`
  - `data/processed/dashboard_rebuild_l3_cost.csv`
  - `reports/dashboard_rebuild_check.md`

## How well attribution was bridged
- Deterministic bridge order:
  1. existing `well_canonical` from master rows,
  2. `well_alias_lookup.csv` alias match,
  3. `canonical_well_mapping.csv` alias match,
  4. otherwise left unmapped and flagged `requires_manual_review=yes`.
- Each row carries `mapping_method`, `mapping_confidence`, and `mapping_source`.
- Unmapped rows are retained in mart and coverage reporting (not dropped).

## How estimator now ties to historical WBS structure
- Estimator now consumes `historical_cost_mart.csv` directly.
- Estimates are generated per L5 branch template and rolled up, rather than top-down campaign-only spreading.
- Every estimated detail row includes source campaign-year tags, source wells, source row IDs/count, method label, uncertainty logic, synthetic/external flags, and reconciliation grouping.
- Calculator view now surfaces total, per-well table, L2 breakdown, and top WBS contributors per well.

## Remaining limitations
- Workbook dashboard tabs are not directly parsed in current environment (xlsx reader package unavailable), so rebuild check compares against `Data.Summary`-derived proxy aggregates.
- Regression branch is not yet enabled; current branch policy uses empirical analog when row sufficiency is present, otherwise explicit fallback benchmark.
- External forecast adjustment remains transparent fallback-off (formula recorded, not silently applied).
