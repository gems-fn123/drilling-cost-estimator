# GPT Project Instructions

You are working on a drilling campaign cost estimator repository.

## Goal
Build a field-specific estimator for DARAJAT and SALAK using historical WBS level 5 actual spending and drilling statistics. Final product: a web app design that estimates drilling campaign cost for a new well and for a planned campaign.

## Main deliverables
1. Identify the main cost driver for every relevant WBS Lv.5 item.
2. Classify each item as `well_tied`, `campaign_tied`, or `hybrid`.
3. Estimate well-tied items for a new well using valid well cost drivers.
4. Estimate campaign-tied items using number of wells, number of pads, and other obvious campaign drivers.
5. Keep every estimate field-specific for DARAJAT or SALAK unless pooling is proven valid.
6. Produce a web app design and app-ready estimation tables.

## Source priority
Primary file: `20260327_WBS_Data.xlsx`
Support files:
- `WBS Reference for Drilling Campaign (Drilling Cost).xlsx`
- `UNSCHEDULED EVENT CODE.xlsx`
- `20260318_WBS_Dictionary.xlsx` only as backup/validation

Trusted sheets from the primary file:
- `Data.Summary`
- `Cost & Technical Data`
- `WellView.Data`
- `1. WellName.Dictionary`
- `2. Drilling.Data.History`
- `3. NPT.Data`
- `4. Depth.vs.Days.History`
- `5. Well.Size.Data`

Do not use pivot sheets, dashboards, or `Well.Efficiency` as source-of-truth.

## Working method
Start simple and explainable.
- Build canonical campaign and well keys.
- Standardize well names using `1. WellName.Dictionary`.
- Build a clean WBS Lv.5 fact table with actual cost, campaign, field, and well linkage.
- Build well-level technical features: depth, drilling days, NPT, casing complexity, phase metrics.
- Build campaign-level features: number of wells, number of pads, total depth, total drilling days.

## Cost-driver logic
Test obvious drivers first.
- Well-tied: actual depth, drilling days, NPT days, casing strings, final hole size, well type.
- Campaign-tied: number of wells, number of pads, mobilization scope, total campaign days, total campaign depth.
- Hybrid: items that are booked at campaign level but scale with wells, depth, or days.

## Modeling standard
For every WBS Lv.5 item:
- report sample size
- report exclusions and missingness
- test at least one baseline and one fitted model
- prefer interpretable methods first: scatter review, Pearson/Spearman, robust regression, GLM
- use cross-validation or leave-one-out when data is small
- report MAE and another suitable percentage metric when valid
- mark confidence as high/medium/low
- never claim causality, only cost association unless clearly justified

## Field rule
Separate DARAJAT and SALAK by default. Only pool data if validation shows similar behavior and better performance.

## Expected repo structure
- `src/data/`
- `src/features/`
- `src/models/`
- `src/app/`
- `data/raw/`
- `data/processed/`
- `reports/`
- `tests/`

## Required outputs
- WBS Lv.5 item catalog with classification and driver rationale
- validated estimator tables for well-tied, campaign-tied, and hybrid items
- model validation summary
- web app spec and app scaffold

## App expectation
Design for a Streamlit app with inputs such as:
- field
- planned wells
- planned pads
- per-well depth
- per-well drilling days
- expected NPT
- optional casing/well design inputs

Outputs should include:
- estimated total campaign cost
- breakdown by WBS Lv.5
- breakdown by well vs campaign vs hybrid cost
- confidence flags
- driver explanation for each estimate

## Guardrails
Do not silently join ambiguous wells.
Do not use partial ongoing campaign actuals without flagging them.
Do not overfit with complex ML when sample size is small.
Do not mix budget and actual in the same target unless explicitly required.
