# WBS Lv.5 Source Inventory

## Scope
Reviewed workbook structure and headers for classification-layer build.

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
- **WBS hierarchy:** `20260318_WBS_Dictionary.xlsx` → `WBS_Dictionary` (LEVEL/LVL 1..5, WBS CODE, tags).
- **Cost rows:** `20260327_WBS_Data.xlsx` → `Data.Summary` (`ACTUAL, USD`, WBS path fields).
- **Campaign mapping:** `data/processed/canonical_campaign_mapping.csv` + `Campaign` in `Data.Summary`.
- **Well naming context:** `data/processed/canonical_well_mapping.csv` + `1. WellName.Dictionary` for coverage checks.
- **Unscheduled/NPT reference:** `UNSCHEDULED EVENT CODE.xlsx` `Sheet1`; NPT classes are not row-addressable from `Data.Summary`, so left explicit-null in master table.

## Data Quality Observations
- `Data.Summary` has hierarchy rows across multiple WBS levels; only rows with populated `L5` are used for Lv.5 classification.
- Several workbook sheets contain explanatory header rows before tabular headers; parser identifies header row dynamically.
- `WBS_Dictionary` contains mixed sections; only rows where `LEVEL == 05` and `WBS CODE` is present are used as Lv.5 dictionary records.
- `Campaign` in cost rows is a label (e.g., `DRJ 2022`), requiring canonical mapping lookup by campaign label.

## Join Candidates
- Cost rows ↔ WBS dictionary via exact `WBS_ID` (`Data.Summary`) to `WBS CODE` (`WBS_Dictionary`).
- Cost rows ↔ canonical campaign via normalized `Campaign` label.
- Well-level context retained as nullable fields because `Data.Summary` is mostly campaign/WBS-grain, not explicit well-grain.
