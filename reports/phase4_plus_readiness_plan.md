# Phase 4+ Readiness Plan and QA/Review Feedback

Date: 2026-04-02  
Status: Draft for execution approval

## 1) Purpose
Define a practical execution plan to reach **full Phase 4 readiness** (validation + explainability artifacts) and establish a controlled bridge into **Phase 5 operationalization** without violating current guardrails.

---

## 2) Current State Snapshot
### What is already in place
- Gate preflight runner (G1-G8) with fail-fast behavior for G1-G6.
- Deterministic baseline outputs split by field with configurable grouping granularity.
- Optional synthetic placeholder inclusion via runtime toggles.
- Driver-to-cost aggregation report for initial estimator-readiness interpretation.

### Known blockers (must be carried forward)
1. **Well attribution coverage gap (G7)**
   - `well_canonical` remains unpopulated at current Lv5 source grain.
2. **Event-code coverage gap (G8)**
   - `event_code_raw` remains unpopulated at current Lv5 source grain.

These are explicitly tracked as known limitations and currently non-blocking to deterministic baseline runs, but they block robust well-level/event-level inference.

---

## 3) Phase 4 Full-Readiness Target (Exit Conditions)
Phase 4 is considered execution-ready when all below are satisfied:

1. **Validation datasets are finalized by field**
   - DARAJAT and SALAK holdout contracts frozen.
   - No pooled training unless explicit statistical justification and approval.

2. **Model/benchmark track selected by sufficiency rule**
   - Regression path when minimum sample thresholds pass.
   - Grouped benchmarking fallback when thresholds fail.

3. **Metrics package published by field**
   - MAE, MAPE, bias, error spread by WBS level and cost tier.
   - CI coverage checks (90% and 95%).

4. **Explainability package complete**
   - Estimate traceback (estimate -> drivers -> source rows).
   - Sensitivity tables with documented assumptions.

5. **Assumption register updated**
   - Explicit entries for all sparse-coverage workarounds and synthetic-data usage policy.

---

## 4) Work Plan (Phase 4+)
## Track A — Data Sufficiency and Coverage Remediation
### A1. Well-attribution bridge design
- Build `wbs_row_to_well_bridge.csv` contract (`source_row_id`, `well_canonical`, `mapping_method`, `confidence`).
- Populate with highest-confidence deterministic matches first.
- Publish unmatched backlog for manual review.

### A2. Event-code bridge design
- Build `wbs_row_to_event_bridge.csv` contract (`source_row_id`, `event_code_raw`, `mapping_method`, `confidence`).
- Trace event sources and attach only auditable joins.

### A3. Coverage KPIs and thresholds
- KPI-1: well-attribution coverage % by field and campaign.
- KPI-2: event-code coverage % by field and campaign.
- KPI-3: high-confidence mapping share %.

**Definition of done (Track A):**
- Coverage KPIs are published and trendable; residual gaps are explicitly accepted or queued.

## Track B — Validation Pipeline Completion
### B1. Holdout contract
- Freeze field-separated holdout IDs and prevent leakage.

### B2. Estimation branch policy
- If sample sufficiency passes: simple/multiple regression with documented feature set.
- If fails: grouped benchmark with quantile bands.

### B3. Validation report generation
- Produce `reports/validation_darajat.md` and `reports/validation_salak.md` with:
  - MAE/MAPE/bias,
  - coverage diagnostics,
  - residual behavior,
  - risk commentary.

**Definition of done (Track B):**
- Both field reports published and reviewed; CI coverage results explicit.

## Track C — Explainability and Governance
### C1. Driver lineage table
- Publish row-level mapping: prediction bucket -> driver family -> source rows.

### C2. Sensitivity package
- Scenario deltas for dominant drivers (e.g., depth proxy, logistics proxy).

### C3. Governance docs
- Update assumptions register and model metadata with run timestamps, input hashes, and limitation flags.

**Definition of done (Track C):**
- Explainability package approved by analytics and project leads.

## Track D — Phase 5 Readiness Bridge
### D1. Operational contracts
- Define refresh trigger, rerun checklist, and rollback criteria.

### D2. App integration prerequisites
- Confirm required output schemas for app consumption and drill-down.

### D3. Monitoring skeleton
- Define KPI dashboard schema (coverage, drift, rerun health).

**Definition of done (Track D):**
- Phase 5 kickoff checklist signed off.

---

## 5) QA Checklist (Execution + Review)
## Data QA
- [ ] G1-G6 hard gates pass on every run.
- [ ] G7/G8 coverage values are updated and trend tracked.
- [ ] Synthetic-row usage is explicitly declared in run manifest.

## Statistical QA (Phase 4 validation track)
- [ ] Leakage checks pass for holdout split.
- [ ] Metric reproducibility confirmed for fixed run snapshot.
- [ ] CI coverage evaluated and documented by field.

## Documentation QA
- [ ] Reports include exact run timestamp and input hashes.
- [ ] Assumptions register updated for every override/exception.
- [ ] Field-separated outputs are not accidentally pooled.

## Review QA
- [ ] Engineering review (data contract + gate logic).
- [ ] Analytics review (driver evidence + metric interpretation).
- [ ] Product/stakeholder review (readability + decision utility).

---

## 6) Review Feedback Log (from current cycle)
1. **Feedback:** “Need meaningful mapping across campaign years inside a field.”
   - **Action already applied:** default family-grain grouping with readiness labels.
   - **Remaining action:** add explicit campaign-year trend tables by group key.

2. **Feedback:** “Need synthetic-data toggle controls.”
   - **Action already applied:** runtime toggles and manifest declaration.
   - **Remaining action:** formal policy note for training/validation inclusion criteria.

3. **Feedback:** “Need stronger driver-to-cost analysis for estimation readiness.”
   - **Action already applied:** driver/classification cost-share report.
   - **Remaining action:** add statistical significance and incremental lift checks in validation reports.

4. **Feedback:** “Clarify unresolved coverage limitations.”
   - **Action in progress:** bridge-table plan defined in Track A.
   - **Remaining action:** implement mapping pipeline + publish coverage trend KPIs.

---

## 7) Recommended Execution Order (Next 2 Sprints)
### Sprint 1 (coverage + contracts)
- A1, A2, A3, B1
- Deliverables:
  - bridge contracts,
  - coverage KPI report,
  - frozen holdout split contract.

### Sprint 2 (validation + explainability)
- B2, B3, C1, C2, C3, D1
- Deliverables:
  - field validation reports,
  - explainability package,
  - operational refresh draft.

### Phase 5 kickoff gate
- D2, D3 and final sign-off checklist.

---

## 8) Risks and Mitigations
- **Risk:** persistent low coverage prevents robust well/event driver validation.
  - **Mitigation:** enforce benchmark fallback and publish confidence limitations prominently.
- **Risk:** synthetic placeholders over-influence decisions.
  - **Mitigation:** keep synthetic opt-in and default-off; report synthetic share in every run.
- **Risk:** accidental field pooling.
  - **Mitigation:** enforce field-specific branches and review checks before report publication.

---

## 9) Approval Needed
Please confirm whether to execute Sprint 1 immediately with:
1. **Strict real-data mode only**, or
2. **Hybrid mode** (real-data plus synthetic placeholders for sensitivity-only diagnostics).
