# Agent Guide: Using Current Data Assets

## Data Assets in This Repository (`data/raw/`)
- `20260327_WBS_Data.xlsx`
  - Primary workbook with `WBS.Tree`, `Data.Summary`, and `Cost & Technical Data` sheets.
- `20260318_WBS_Dictionary.xlsx`
  - Dictionary and structure reference (`WBS_Dictionary`, `WBS.structure`).
- `UNSCHEDULED EVENT CODE.xlsx`
  - Controlled vocabulary for unscheduled event classification.
- `WBS Reference for Drilling Campaign (Drilling Cost).xlsx`
  - Supplemental campaign reference.

## Agent Workflow
1. **Read first**: `AGENTS.md`, then `GPT_PROJECT_INSTRUCTIONS.md`.
2. **Load and profile** each workbook (sheet list, row counts, missingness, duplicate keys).
3. **Normalize schema** to canonical columns:
   - `wbs_level_1..wbs_level_5`, `wbs_code`, `activity`, `cost`, `duration`, `well`, `campaign`, `event_code`.
4. **Validate hierarchy**:
   - No orphan Level-5 entries.
   - Parent-child consistency from L1 -> L5.
5. **Map unscheduled events**:
   - Join event records to standardized codes from `UNSCHEDULED EVENT CODE.xlsx`.
6. **Generate ingestion outputs**:
   - Canonical cleaned tables in `data/processed/`.
   - Well-name crosswalk table.
   - `reports/source_inventory.md`.
7. **Do not build model yet** during ingestion stage.

## Guardrails
- Never estimate a Level-5 item without a valid Level-1..4 path.
- Reject rows with ambiguous WBS mapping until remediated.
- Keep an assumption register for manual overrides.
- Maintain field specificity for DARAJAT vs SALAK during validation phases.
