# Task 001: Build data-ingestion layer

Read `AGENTS.md` and `GPT_PROJECT_INSTRUCTIONS.md` first.

## Requirements
- Read all Excel files from `data/raw`
- Discover all sheet names and save a sheet inventory report to `reports/source_inventory.md`
- Create canonical cleaned tables in `data/processed` as parquet or csv
- Standardize campaign names and well names
- Build a well-name crosswalk table
- Do not build any model yet
- Add a short README section explaining how to rerun ingestion

## Deliverables
- `src/io/*.py`
- `data/processed/*`
- `reports/source_inventory.md`
- Tests for ingestion where practical
