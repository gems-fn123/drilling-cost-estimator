# WBS Tree Diagram Report

Generated: 2026-04-24T10:26:51.445225+00:00

## Source Contract
- Source dataset: `data/processed/historical_cost_mart.csv`
- Included rows: mapped `Data.Summary` rows with complete L1-L5 path and non-empty `campaign_canonical`.
- Field handling: DARAJAT and SALAK are built as separate trees.

## Field Snapshot
- **DARAJAT**: node_count=697, leaf_count=462, r=462, c=2, sum=68036634.54, spr=444724.08 (1084.12%).
- **SALAK**: node_count=514, leaf_count=360, r=360, c=1, sum=38522325.57, spr=330391.61 (1925.30%).

## Output Artifacts
- `data/processed/wbs_tree_interactive.json`
- `data/processed/wbs_tree_field_darajat.json`
- `data/processed/wbs_tree_field_salak.json`
- `reports/wbs_tree_interactive.html`
