# Dashboard_x Snapshot Extract

## Scope
- Source sheet: `Dashboard_x` from `20260327_WBS_Data.xlsx`.
- This extract preserves dashboard-style historical cost facts as auditable CSV rows.
- The extract is a source snapshot, not a model output.

## Extracted Sections
- summary metrics: **8**
- cost by well rows: **9**
- L3 breakdown rows: **14**

## Notes
- Field is inferred from the dashboard title (`SLK` -> `SALAK`, `DRJ` -> `DARAJAT`).
- Each extracted row includes a deterministic `source_row_id` for lineage.
- This snapshot is intended to expand the auditable historical pool used by downstream estimator work.
