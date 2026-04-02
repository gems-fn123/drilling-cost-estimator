# Phase 4 Implementation Tracker

Date: 2026-04-02
Status: In Progress

## Scope
Implements the kickoff actions from `reports/phase4_execution_kickoff.md` and user feedback:
1. Gate-check runner (G1-G8)
2. Deterministic baselines by field
3. Interconnected campaign design draft
4. Execution tracking with owners, ETA, and risks
5. Feedback response: cross-campaign-year family aggregation + synthetic-data toggles + driver-to-cost aggregation report

## Work Items
| id | work item | owner | eta (UTC) | status | risks / notes |
|---|---|---|---|---|---|
| P4-01 | Build reusable gate runner for G1-G8 and publish gate report | Data Engineering | 2026-04-02 | Done | Depends on canonical contracts (`wbs_lv5_master`, `wbs_lv5_classification`). |
| P4-02 | Generate deterministic baseline estimates for DARAJAT | Analytics Engineering | 2026-04-02 | Done | Family-grain default improves sample coverage vs Lv5 singleton groups. |
| P4-03 | Generate deterministic baseline estimates for SALAK | Analytics Engineering | 2026-04-02 | Done | Same field-separated logic and grouping controls as DARAJAT. |
| P4-04 | Publish interconnection design (well/support/surface facilities) | Project Analytics | 2026-04-03 | Done | Design-only; no model fitting yet in this step. |
| P4-05 | Add synthetic-data runtime toggles and auditable manifest flags | Analytics Engineering | 2026-04-02 | Done | Toggle options: `--use-synthetic`, `--synthetic-policy`, `--group-by`. |
| P4-06 | Publish driver-to-cost aggregation report for estimator readiness | Analytics Engineering | 2026-04-02 | Done | Report path: `reports/phase4_driver_analysis.md`. |

## Current Risks and Mitigations
- **R1: Well attribution sparsity** (`well_canonical` not populated at Lv.5 grain).
  - **Mitigation:** Keep as explicit G7 limitation and avoid claiming well-level predictive validity.
- **R2: Event code sparsity** (`event_code_raw` not populated at Lv.5 grain).
  - **Mitigation:** Keep as explicit G8 limitation and avoid event-driver claims until bridged.
- **R3: Synthetic data misuse risk.**
  - **Mitigation:** Synthetic rows are opt-in via runtime toggles; manifest records whether they were used.

## Outputs Generated in This Tracker Cycle
- `data/processed/phase4_gate_results.csv`
- `reports/phase4_gate_preflight_report.md`
- `data/processed/baseline_estimates_darajat.csv`
- `data/processed/baseline_estimates_salak.csv`
- `reports/phase4_driver_analysis.md`
- `data/processed/phase4_run_manifest.json`
