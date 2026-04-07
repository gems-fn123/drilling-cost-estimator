# Phase 5 Streamlit Demo Review Pack

Date: 2026-04-07  
Status: **Ready for design review (prototype)**

## 1) Is the app ready yet?
Short answer: **Ready for UX/design review; not yet ready for production release**.

### Ready now
- Field-separated data contract for app consumption is available (`phase5_app_dataset.csv`).
- Monitoring feed contract is available (`phase5_monitoring_kpis.csv`).
- Prototype shell exists in `src/app/phase5_streamlit_demo.py`.

### Still pending before production go-live (excluding G7/G8)
1. Validation publication gap:
   - `reports/validation_darajat.md` and `reports/validation_salak.md` are not yet published in active artifacts.
2. CI-coverage publication gap:
   - Decision-facing confidence-coverage evidence (90%/95%) is not packaged in a dedicated release report.
3. Scenario engine evidence gap:
   - No audited coefficient table/rulebook yet for scenario calculations in-app.
4. Release governance bundle gap:
   - Deployment guide + signed release checklist + training pack not yet packaged in one release folder.

## 2) Demo wireframe (for review)

```text
+--------------------------------------------------------------------------------+
| Phase 5 Demo - Drilling Cost Estimator                                        |
| [Field: DARAJAT v]                                                             |
+----------------------+----------------------+----------------------------------+
| Groups: 61           | Ready Share: 72.13% | Hard Gate Failures: 0            |
+--------------------------------------------------------------------------------+
| Estimator Group View                                                           |
| group_key | class | driver_family | sample | P10 | P50 | P90 | confidence ... |
| ...                                                                            |
+--------------------------------------------------------------------------------+
| Scenario Controls (design-only)                                                |
| Depth adjustment [% slider]   Operation mode [base/accelerated/conservative] |
| Preview note: coefficients pending validation package                           |
+--------------------------------------------------------------------------------+
| Known Limits banner (includes G7/G8 disclosure and release caveats)            |
+--------------------------------------------------------------------------------+
```

## 3) What to review now (actionable)
1. **Information architecture**
   - Confirm the default field-first flow and non-pooled behavior.
2. **Table semantics**
   - Confirm `P10/P50/P90`, `confidence_tier`, and `estimator_readiness` labels are decision-friendly.
3. **Scenario panel expectations**
   - Confirm expected user inputs and acceptable placeholders until coefficients are approved.
4. **Monitoring KPI cards**
   - Confirm thresholds (`ready_share`, `hard_gate_failures`, `known_limitations`) and escalation rules.
5. **Governance language**
   - Approve banner/disclaimer wording for pre-production demos.

## 4) Recommended next prep sprint (non-G7/G8)
- Publish validation reports per field with MAE/MAPE/bias and CI coverage tables.
- Add a versioned scenario-rules contract (`data/processed/phase5_scenario_rules.csv`).
- Finalize release checklist + deployment/training package under `docs/` and `reports/`.
