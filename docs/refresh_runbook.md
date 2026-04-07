# Phase 5 Refresh Runbook

## Purpose
Operational runbook for monthly/quarterly refresh of the drilling cost estimator package.

## Scope
- Produces app-ready baseline dataset and monitoring KPI snapshot.
- Keeps DARAJAT and SALAK separated in all outputs.
- Preserves known limitation disclosure from phase gates.

## Trigger Cadence
- Monthly: monitoring snapshot refresh.
- Quarterly: full gate + baseline + operational asset refresh.

## Commands
1. Rebuild canonical mappings and classification:
   - `python src/io/build_canonical_mappings.py`
   - `python src/cleaning/build_wbs_lv5_classification.py`
2. Run phase-4 gate + baseline generation:
   - `python src/modeling/phase4_preflight_and_baseline.py --group-by family`
3. Build phase-5 operational assets:
   - `python src/app/build_phase5_operational_assets.py`

## Validation Checklist
- Confirm `data/processed/phase4_gate_results.csv` has PASS for G1-G6.
- Confirm `data/processed/phase5_app_dataset.csv` contains both fields.
- Confirm `data/processed/phase5_monitoring_kpis.csv` updates `snapshot_ts_utc`.
- Confirm reports:
  - `reports/phase5_app_integration_prerequisites.md`
  - `reports/phase5_monitoring_skeleton.md`

## Rollback
If any hard gate (G1-G6) fails:
1. Keep previous approved phase-5 artifacts in place.
2. Log issue in assumptions register.
3. Re-run only after data remediation.
