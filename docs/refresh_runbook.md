# Phase 5 Refresh Runbook

## Purpose
Operational runbook for monthly/quarterly refresh of the drilling cost estimator package.

## Scope
- Produces app-ready baseline dataset and monitoring KPI snapshot.
- Keeps DARAJAT and SALAK separated in all outputs.
- Preserves known limitation disclosure from phase gates.

## Trigger Cadence
- Monthly: monitoring snapshot refresh.
- Quarterly: full ETL refresh and endpoint contract refresh.

## Commands
1. Refresh full ETL package (single entrypoint):
   - `python src/modeling/streamlined_etl_pipeline.py --refresh-only`
2. Refresh and produce estimator endpoint output:
   - `python src/modeling/streamlined_etl_pipeline.py --request-json <request_json_path>`

Request JSON contract:
```json
{
  "campaign_input": {
    "year": 2026,
    "field": "SLK",
    "no_pads": 2,
    "no_wells": 2,
    "no_pad_expansion": 1,
    "use_external_forecast": true,
    "use_synthetic_data": false
  },
  "well_rows": [
    {
      "well_label": "Well-1",
      "pad_label": "Pad-1",
      "depth_ft": 7000,
      "leg_type": "Standard-J",
      "drill_rate_mode": "Standard"
    }
  ]
}
```

## Validation Checklist
- Confirm `data/processed/etl_pipeline_manifest.json` is present and recent.
- Confirm `data/processed/phase4_gate_results.csv` has PASS for G1-G6.
- Confirm `data/processed/phase5_app_dataset.csv` contains both fields.
- Confirm `data/processed/phase5_monitoring_kpis.csv` updates `snapshot_ts_utc`.
- Confirm endpoint payload exists at `data/processed/etl_pipeline_endpoint_output.json` when request mode is used.
- Confirm WBS tree outputs exist: `data/processed/wbs_tree_interactive.json` and `reports/wbs_tree_interactive.html`.

## Rollback
If any hard gate (G1-G6) fails:
1. Keep previous approved phase-5 artifacts in place.
2. Log issue in assumptions register.
3. Re-run only after data remediation.
