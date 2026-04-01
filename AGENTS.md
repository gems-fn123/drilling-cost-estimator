# AGENTS.md

## Project objective
Build a field-specific drilling campaign cost estimator for DARAJAT and SALAK using historical WBS level 5 actual spending and drilling statistics. The end product is a web app design plus a reproducible estimation pipeline.

## What good output looks like
- Every estimate is traceable to a clear WBS Lv.5 item.
- Every cost driver is testable, statistically justified, and easy to explain.
- Results stay separated by field unless there is evidence pooling is valid.
- Outputs are usable by non-coders in a web app.

## Primary data sources
Use these files in this priority order:
1. `20260327_WBS_Data.xlsx` as primary source.
2. `WBS Reference for Drilling Campaign (Drilling Cost).xlsx` for campaign scope.
3. `UNSCHEDULED EVENT CODE.xlsx` for NPT/event decoding.
4. `20260318_WBS_Dictionary.xlsx` only for WBS parsing validation or backup.

## Trusted sheets
From `20260327_WBS_Data.xlsx`, prioritize:
- `Data.Summary`
- `Cost & Technical Data`
- `WellView.Data`
- `1. WellName.Dictionary`
- `2. Drilling.Data.History`
- `3. NPT.Data`
- `4. Depth.vs.Days.History`
- `5. Well.Size.Data`

Do not use pivot, dashboard, or `Well.Efficiency` sheets as source-of-truth.

## Core modeling tasks
1. Classify each WBS Lv.5 item as:
   - `well_tied`
   - `campaign_tied`
   - `hybrid`
2. Find the main cost driver for each item.
3. Build field-specific estimation logic for DARAJAT and SALAK.
4. Produce estimator-ready tables and web-app-ready outputs.

## Cost-driver rules
Prefer simple, defensible drivers first:
- Well-tied: actual depth, drilling days, NPT days, casing complexity, well type.
- Campaign-tied: number of wells, number of pads, total campaign depth, total campaign drilling days.
- Hybrid: campaign item whose cost scales with wells, depth, or days.

Never claim a driver is valid without testing it.

## Statistical standards
For every modeled WBS Lv.5 item:
- Report sample size.
- Show missingness and exclusions.
- Test driver relationship with simple interpretable methods first.
- Prefer correlation, rank correlation, scatter review, robust regression, or GLM before complex ML.
- Check outliers and influential points.
- Compare at least one baseline against one fitted model.
- Use cross-validation or leave-one-out when sample size is small.
- Report error metrics clearly, including MAE and MAPE when valid.
- Flag items with too little history as low-confidence.

## Field-specific rules
- Default to separate models for DARAJAT and SALAK.
- Only pool fields when a comparison shows similar cost behavior and pooling improves validation.
- Always preserve field as an explicit feature and reporting slice.

## Join and naming rules
- Standardize campaign labels before analysis.
- Standardize well names using `1. WellName.Dictionary`.
- Keep a canonical well key and campaign key in every derived table.
- Do not silently merge ambiguous wells.

## Required outputs
Create and maintain:
- `data/processed/wbs_l5_cost_table.parquet`
- `data/processed/well_master.parquet`
- `data/processed/campaign_master.parquet`
- `data/processed/wbs_l5_driver_tests.parquet`
- `reports/wbs_l5_item_catalog.md`
- `reports/model_validation_summary.md`
- `reports/web_app_spec.md`

## Coding rules
- Use Python.
- Prefer pandas, numpy, scipy, statsmodels, scikit-learn, plotly, and streamlit.
- Keep functions small and typed when reasonable.
- Put reusable logic in `src/`, not notebooks.
- Save intermediate outputs so work is reproducible.
- Do not hardcode one-off spreadsheet row numbers.

## Workflow rules
Before large edits or new modules:
- write or update a short plan in `PLANS.md`
- state assumptions
- list files to change

After changes:
- run relevant tests
- update docs if behavior changed
- summarize remaining risks and data limitations

## Review focus
Flag as high priority:
- field leakage between DARAJAT and SALAK
- wrong well-name joins
- using derived dashboard sheets as source data
- invalid statistical claims
- estimates produced without confidence or validation notes
