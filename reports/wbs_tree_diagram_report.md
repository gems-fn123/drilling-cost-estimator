# WBS Tree Diagram Report

Generated: 2026-05-05T03:30:10.664599+00:00

## Source Contract
- Source dataset: `data/processed/unit_price_history_mart.csv`
- Included rows: `Structured.Cost` lineage rows with complete campaign + Level 2..5 hierarchy.
- Field handling: DARAJAT, SALAK, and WAYANG_WINDU are built as separate trees.

## Field Snapshot
- **DARAJAT**: node_count=289, leaf_count=151, r=452, c=3, sum=110040018.70, spr=637011.56 (1028.82%).
- **SALAK**: node_count=211, leaf_count=104, r=396, c=2, sum=66573573.31, spr=482943.42 (1254.97%).
- **WAYANG_WINDU**: node_count=136, leaf_count=70, r=290, c=2, sum=54061998.09, spr=478421.39 (656.22%).

## Output Artifacts
- `data/processed/wbs_tree_interactive.json`
- `data/processed/wbs_tree_field_darajat.json`
- `data/processed/wbs_tree_field_salak.json`
- `data/processed/wbs_tree_field_wayang_windu.json`
- `reports/wbs_tree_interactive.html`
