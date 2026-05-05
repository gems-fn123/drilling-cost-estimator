# WBS Lv.5 Source Inventory

## Scope
Reviewed workbook structure and headers for the driver-alignment build.

## Snapshot Freeze
- This alignment run treats `20260422_Data for Dashboard.xlsx` as the frozen source snapshot.
- Driver alignment remains a classification/reference task only; no statistical driver validation is performed in this layer.

## Workbook / Sheet Inventory
### `20260422_Data for Dashboard.xlsx`
- `$_day`: 0 rows
- `$_ft`: 0 rows
- `Archives>>`: 0 rows
- `Charts`: 1 rows
- `Check.Total`: 9 rows
- `Compared`: 41 rows
- `DashBoard.Tab.Template`: 41 rows
- `Drill.Campaign.Ref.Tidy`: 9 rows
- `Drill.Depth.Days`: 1454 rows
- `General.Camp.Data`: 40 rows
- `NPT.Data`: 403 rows
- `Phase.Summary`: 471 rows
- `Piv.Struct.Cost`: 95 rows
- `Pivot.Master`: 45 rows
- `Pivots>>`: 0 rows
- `Sheet3`: 29 rows
- `Sheet4`: 3 rows
- `Sheet6`: 1 rows
- `Sheet7`: 4 rows
- `Sheet9`: 28 rows
- `Source.Data>>`: 0 rows
- `Structured.Cost`: 1139 rows
- `Structured.Cost (2)`: 1139 rows

## Authoritative Sources Used
- **Cost rows:** `20260422_Data for Dashboard.xlsx` -> `Structured.Cost` (`Actual Cost USD`, `Level 2..5`, `Well`).
- **WBS tags:** `data/processed/wbs_lv5_tag_reference.csv` (built once from prior processed outputs when available, then refreshed dashboard-first).
- **Campaign scope:** `data/processed/canonical_campaign_mapping.csv` plus explicit label aliases for in-scope campaign labels.
- **Curated driver policy:** `src/cleaning/wbs_lv5_family_policy.csv`.

## Data Quality Observations
- `Structured.Cost` rows are already at Level 5 granularity (`Level 2..5`) and are normalized into a deterministic `WBS_ID` for lineage continuity.
- Campaign labels are resolved through explicit alias mapping before class assignment.
- `hybrid` is reserved for non-well scope that is estimable from structured campaign design/scope drivers. Missing evidence no longer defaults to `hybrid`.

## Join Candidates
- Cost rows -> Lv5 tag reference via deterministic `WBS_ID` and `Level 2..5` path matching.
- Cost rows -> canonical campaign via label alias to official campaign code.
- Well-level context is inferred from `Well` in `Structured.Cost`, `General.Camp.Data`, and `NPT.Data` where applicable.
