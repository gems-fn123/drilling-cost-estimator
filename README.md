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

## Streamlit App + Audit Layer (Phase 5)
Run the app:

```bash
streamlit run src/app/streamlit_app.py
```

Run validation artifact build:

```bash
python src/modeling/build_phase5_validation_artifacts.py
```

### Toggle behavior
- `EXTN. DATA`: attempts external forecast adjustment; if no auditable external series is available, app explicitly falls back to historical-only mode.
- `SYNTH DATA`: allows synthetic placeholders only for sparse buckets and always records synthetic usage in audit output.

### Uncertainty method
- Current app branch is `grouped_benchmark` with quantile uncertainty proxy (`P10/P50/P90`) and explicit method labels.
- No predictive-validity claim is made until regression sufficiency thresholds are met and validated.

### Source references
- Every detail row carries `source_field_campaign_years` and `source_row_count` and is written to `data/processed/app_estimate_audit.csv`.

### Current limitations
- Well/event coverage gaps (G7/G8) remain disclosed.
- External macro adjustment remains disabled-by-fallback unless auditable external series are added.
- Validation branch is benchmark fallback (not regression) unless sufficiency gates are met.
