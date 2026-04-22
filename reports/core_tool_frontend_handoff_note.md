# Core Tool Front-End Handoff Note

Date: 2026-04-22
Owner: Data/Estimator Core Team
Audience: Front-End Team

## Handoff Scope
This handoff covers the current Streamlit core tool behavior and the contracts needed to implement or wrap it in a front-end experience.

Included surfaces:
- Calculator flow
- Detail WBS audit view
- WBS chart viewer
- Runtime refresh behavior

## Runtime Behavior (Current)

### Calculator
File: src/app/streamlit_app.py

On `CALCULATE DRILLING COST`, the app currently runs:
1. `build_validation_artifacts()`
2. `estimate_campaign(campaign_input, well_rows)`

Important: `build_validation_artifacts()` defaults to `refresh_pipeline=True` in src/modeling/phase5_estimation_core.py, which triggers a full pipeline refresh before estimating.

Pipeline refresh includes:
- canonical mappings build
- WBS Lv5 alignment build
- dashboard refresh outputs
- phase 4 preflight/baseline
- phase 5 operational assets

This means calculator runs are currently rebuild-first, then estimate.

### WBS Viewer
File: src/app/components/wbs_tree_tab.py

Current mode:
- `Load Excel`: builds WBS payload directly from selected workbook/sheet

The WBS viewer does not need a separate refresh button for normal use because the selected workbook already rebuilds the WBS mapping path in-memory for that session.

## Front-End Input Contracts

### Campaign Input
From src/app/components/input_panel.py and estimator normalization:
- year: integer
- field: `DRJ` or `SLK`
- no_pads: integer
- no_wells: integer
- no_pad_expansion: integer
- use_external_forecast: boolean
- use_synthetic_data: boolean

### Well Rows
List of objects:
- well_label
- pad_label
- depth_ft
- leg_type
- drill_rate_mode

## Front-End Output Contracts

Primary estimator response object (from src/modeling/phase5_estimation_core.py):
- campaign_input
- well_outputs
- campaign_summary
- detail_wbs
- audit_rows
- run_manifest
- warnings

Used by current UI:
- calculator summary + per-well matrix: src/app/components/calculator_tab.py
- detailed audit grid/download: src/app/components/detail_tab.py

## Field Partition Rule (Non-Negotiable)
- DARAJAT and SALAK must remain separated in estimator and analysis logic.
- Do not pool fields in a single estimate path unless a separate approved statistical justification is implemented.

## WBS Interaction Contract (Current)
File: src/app/components/wbs_tree_tab.py

Selector sequence:
1. Field selector
2. Campaign tier selector
3. Cascade node selector

Rules:
- Campaign tier selector is direct descendants only of selected field node
- Cascade selector can traverse descendants from selected campaign tier
- Selector labels are compact: `node_id - short_desc | compact_sum` when available

## Artifact Dependencies for FE Integration

Core processed artifacts:
- data/processed/historical_cost_mart.csv
- data/processed/phase5_app_dataset.csv
- data/processed/confidence_bands.csv
- data/processed/estimator_method_registry.csv
- data/processed/app_estimate_audit.csv
- data/processed/app_estimate_summary.json
- data/processed/app_run_manifest.json

WBS artifacts:
- data/processed/wbs_tree_interactive.json
- data/processed/wbs_tree_field_darajat.json
- data/processed/wbs_tree_field_salak.json
- reports/wbs_tree_interactive.html

## Recommended FE Integration Modes

### Mode A: Rebuild-First (Current Parity)
Use when strict parity with current Streamlit behavior is required.
- Trigger full refresh before estimate.
- Higher latency, highest consistency with latest raw inputs.

### Mode B: Fast Estimate (Recommended for UX)
Use when FE requires responsive interactions.
- Skip rebuild for normal estimate calls.
- Add explicit `Refresh Data` action for users/admins.
- Clearly show last-refresh timestamp from manifest.

## Operational Risks and Notes
- Legacy/enterprise Excel files may route through COM fallback on Windows.
- COM path requires thread-level COM initialization; this has been patched in src/io/build_canonical_mappings.py.
- If FE wraps Python workers, maintain Windows COM compatibility for Excel fallback paths.

## FE Acceptance Checklist
- Calculator request uses the exact campaign/well contract.
- Field selection is single-field scoped per estimate request.
- Response rendering supports:
  - total campaign summary
  - per-well output table
  - category matrix
  - detail WBS rows
  - audit download
- WBS viewer honors selector hierarchy and compact labels.
- Refresh action and estimate action are clearly separated in UI copy.
- Last artifact refresh timestamp is visible to users.

## Suggested API Layer (If Extracting from Streamlit)
- POST /estimate
  - body: campaign_input + well_rows + runtime_toggles
  - response: estimator response object
- POST /refresh
  - body: refresh options (group_by, synthetic flags)
  - response: pipeline manifest summary
- GET /wbs
  - query: field, campaign_tier, focus_node
  - response: focused WBS payload/html fragment

## Handoff Decision Needed
Front-end team should confirm one runtime mode for calculator:
1. Keep rebuild-first parity
2. Switch to fast estimate + explicit refresh

Recommended default: Option 2 for production UX, with admin-only or manual refresh controls.
