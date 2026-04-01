# Agent Guide: Using Current Data Assets

## Data Assets in This Repository
- `20260327_WBS_Data.xlsx`
  - Primary workbook with `WBS.Tree`, `Data.Summary`, and `Cost & Technical Data` sheets.
- `20260318_WBS_Dictionary.xlsx`
  - Dictionary and structure reference (`WBS_Dictionary`, `WBS.structure`).
- `UNSCHEDULED EVENT CODE.xlsx`
  - Controlled vocabulary for unscheduled event classification.
- `WBS Reference for Drilling Campaign (Drilling Cost).xlsx`
  - Supplemental campaign reference.

## Agent Workflow
1. **Load and profile** each workbook (sheet list, row counts, missingness, duplicate keys).
2. **Normalize schema** to canonical columns:
   - `wbs_level_1..wbs_level_5`, `wbs_code`, `activity`, `cost`, `duration`, `well`, `campaign`, `event_code`.
3. **Validate hierarchy**:
   - No orphan Level-5 entries.
   - Parent-child consistency from L1 -> L5.
4. **Map unscheduled events**:
   - Join event records to standardized codes from `UNSCHEDULED EVENT CODE.xlsx`.
5. **Generate estimator dataset**:
   - Base deterministic rollups by WBS code.
   - Feature-ready table for statistical modeling.
6. **Run estimation and QA**:
   - Split train/validation by campaign or time.
   - Report MAE/MAPE and variance by WBS level.
7. **Publish outputs**:
   - Estimate table, confidence range, data quality report, and assumptions log.

## Guardrails
- Never estimate a Level-5 item without a valid Level-1..4 path.
- Reject rows with ambiguous WBS mapping until remediated.
- Keep an assumption register for manual overrides.
