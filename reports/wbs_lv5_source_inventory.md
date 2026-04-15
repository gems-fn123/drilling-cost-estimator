# WBS Lv.5 Source Inventory

## Scope
Reviewed workbook structure and headers for the driver-alignment build.

## Snapshot Freeze
- This alignment run treats the current `data/raw/*.xlsx` workbook set as the frozen source snapshot.
- Driver alignment remains a classification/reference task only; no statistical driver validation is performed in this layer.

## Workbook / Sheet Inventory
### `20260327_WBS_Data.xlsx`
- `1. WellName.Dictionary`: 40 rows
- `2. Drilling.Data.History`: 56 rows
- `3. NPT.Data`: 431 rows
- `4. Depth.vs.Days.History`: 1456 rows
- `5. Well.Size.Data`: 308 rows
- `>>Graveyard`: 1 rows
- `Actual.SLK2025_26`: 9023 rows
- `Code_Dictionary`: 1312 rows
- `Commit.SLK2025_26`: 4373 rows
- `Cost & Technical Data`: 2427 rows
- `Cost>>`: 1 rows
- `Dashboard_x`: 51 rows
- `Data.Summary`: 2426 rows
- `Drilled.Well`: 10 rows
- `MoM`: 15 rows
- `Piv.Campaign`: 48 rows
- `Piv.Campaign (2)`: 27 rows
- `Piv.Well.Services.Material`: 87 rows
- `Sheet3`: 515 rows
- `Tech>>`: 1 rows
- `WBS.Tree`: 34 rows
- `WBS.structure`: 2429 rows
- `WBS.structure.x1`: 2429 rows
- `Well.Efficiency`: 31 rows
- `WellView.Data`: 21 rows

### `20260318_WBS_Dictionary.xlsx`
- `WBS.structure`: 2428 rows
- `WBS_Dictionary`: 1774 rows

### `UNSCHEDULED EVENT CODE.xlsx`
- `Sheet1`: 99 rows

### `WBS Reference for Drilling Campaign (Drilling Cost).xlsx`
- `Sheet1`: 7 rows

## Authoritative Sources Used
- **WBS hierarchy:** `20260318_WBS_Dictionary.xlsx` -> `WBS_Dictionary` (`LEVEL`, `LVL 1..5`, WBS tags).
- **Cost rows:** `20260327_WBS_Data.xlsx` -> `Data.Summary` (`ACTUAL, USD`, WBS path fields).
- **Campaign scope:** `data/processed/canonical_campaign_mapping.csv` plus explicit label aliases for `DRJ 2022`, `DRJ 2023`, and `SLK 2025`.
- **Curated driver policy:** `src/cleaning/wbs_lv5_family_policy.csv`.

## Data Quality Observations
- `Data.Summary` contains multiple WBS levels; ingestion keeps only `WBS_Level = 05` rows (Lv.5 leaf entries).
- Campaign labels in `Data.Summary` are short labels (`DRJ 2022`, `DRJ 2023`, `SLK 2025`), so driver alignment resolves them through explicit alias mapping before class assignment.
- `hybrid` is reserved for non-well scope that is estimable from structured campaign design/scope drivers. Missing evidence no longer defaults to `hybrid`.

## Join Candidates
- Cost rows -> WBS dictionary via exact `WBS_ID` (`Data.Summary`) to `WBS CODE` (`WBS_Dictionary`).
- Cost rows -> canonical campaign via label alias to official campaign code.
- Well-level context remains nullable because `Data.Summary` is still campaign/WBS grain rather than row-level well attribution.
