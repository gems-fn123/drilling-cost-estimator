# GPT Project Instructions

## Project Goal
Build a statistically valid drilling campaign cost estimator at WBS Level 5.

## Execution Sequence
1. Build data ingestion and cleaning layer.
2. Classify WBS Lv.5 items as `well_tied`, `campaign_tied`, or `hybrid`.
3. Validate cost drivers separately for DARAJAT and SALAK.
4. Build Streamlit app only after validated driver outputs exist.

## Constraints
- No modeling during ingestion task.
- Keep methods interpretable first (correlation, simple regression, justified multiple regression, grouped benchmarking).
- Record rationale, exclusions, uncertainty, and data sufficiency flags.
