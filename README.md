# drilling-cost-estimator

Using historical drilling campaign data, this project targets statistically valid **Level-5 WBS cost estimation**.

## Read First
1. `AGENTS.md`
2. `GPT_PROJECT_INSTRUCTIONS.md`

## Repository Structure
- `data/raw/` - source Excel files
- `data/processed/` - cleaned/canonical datasets and derived tables
- `src/io/` - ingestion and source parsing
- `src/cleaning/` - cleaning and standardization
- `src/features/` - feature prep for validated drivers
- `src/modeling/` - estimator logic (after driver validation)
- `src/app/` - Streamlit app (after validated outputs)
- `reports/` - data inventory, validation, and method docs
- `tests/` - automated tests
- `scripts/setup.sh` - environment setup script

## Current Data Inputs (`data/raw/`)
- `20260327_WBS_Data.xlsx`
- `20260318_WBS_Dictionary.xlsx`
- `UNSCHEDULED EVENT CODE.xlsx`
- `WBS Reference for Drilling Campaign (Drilling Cost).xlsx`

## Setup (for environment setup scripts)
Run:

```bash
bash scripts/setup.sh
```

## Suggested Task Sequence
1. **Ingestion** (see `reports/tasks/001_ingestion_task.md`)
2. **WBS Lv.5 classification** (`well_tied`, `campaign_tied`, `hybrid`)
3. **Field-specific driver validation** (DARAJAT and SALAK separately)
4. **Streamlit app prototype** using only validated drivers
