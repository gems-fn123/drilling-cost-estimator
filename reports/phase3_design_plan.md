# Phase 3 Design Plan (Kickoff)

## Context
- Date started: **2026-04-02**.
- Phase objective reference: architect the end-to-end estimator pipeline and define field-specific validation gates before any new development implementation.
- Gate baseline: Phase 2 quality thresholds are marked **READY FOR PHASE 3 DESIGN** in `reports/phase2_define_quality_thresholds.md`.

## Phase 3 Scope (Design Only)
This phase is planning and architecture. It focuses on:
1. Pipeline blueprint from canonical inputs to reporting outputs.
2. Deterministic rollup design separated from statistical estimation design.
3. Field-specific strategy for DARAJAT and SALAK (no pooled evaluation by default).
4. Validation gate definitions for progression into implementation.

Out of scope in this phase:
- Production model training.
- Streamlit/app implementation.
- Any non-auditable transformation that cannot trace back to canonical source rows.

## Entry Criteria Check (Phase 2 -> Phase 3)
| gate item | source evidence | status |
|---|---|---|
| Canonical Lv.5 row-grain contract published | `data/processed/wbs_lv5_master.csv` | READY |
| Classification contract published | `data/processed/wbs_lv5_classification.csv` | READY |
| Feature families defined with lineage and limitations | `docs/feature_families.md` | READY |
| Quality threshold report published | `reports/phase2_define_quality_thresholds.md` | READY |
| Driver alignment summary available | `reports/wbs_lv5_driver_alignment_report.md` | READY |

## Architecture Workplan

### Workstream A — Pipeline Architecture Spec
**Goal:** publish a single architecture specification document that defines stages, controls, and handoffs.

Planned artifacts:
- `reports/phase3_pipeline_architecture.md`
- Supporting diagram (Mermaid inside markdown)

Required sections:
- Inputs and contracts (`wbs_lv5_master`, `wbs_lv5_classification`, campaign/well masters)
- Stages: ingest snapshot -> quality gate -> feature assembly -> deterministic baseline -> statistical track -> reporting
- Lineage keys and traceability design (`source_file`, `source_row`, canonical keys)
- Failure behavior when gate checks fail

### Workstream B — Validation Gate Specification
**Goal:** define measurable pass/fail checks required before implementation (Phase 4).

Planned artifact:
- `reports/phase3_validation_gates.md`

Planned checks:
- Field split integrity (100% rows assigned to DARAJAT or SALAK)
- Hierarchy continuity checks at L1->L5
- Classification consistency checks (`well_tied`, `campaign_tied`, `hybrid`)
- Data sufficiency pre-check definitions for later driver validation
- Known-limitation carry-forward checks (well attribution and event-code sparsity)

### Workstream C — Field Separation Strategy
**Goal:** finalize explicit rules for DARAJAT vs SALAK processing and reporting.

Planned artifact:
- `reports/phase3_field_separation_strategy.md`

Planned rules:
- Independent baseline summaries by field
- Independent feature screening and significance reporting by field
- No pooled driver claims without documented statistical justification
- Separate holdout definitions and validation summaries per field

## Decision Log for Kickoff
1. Use the existing Phase 2 implemented contracts as immutable interfaces for Phase 3 planning.
2. Carry forward known limitations (missing well-level attribution and event-code sparsity at current Lv.5 source grain) as explicit gate constraints.
3. Keep hybrid class handling campaign-scope in design until data supports defensible per-well allocation.

## Deliverables to Complete Phase 3
- [x] `reports/phase3_pipeline_architecture.md`
- [x] `reports/phase3_validation_gates.md`
- [x] `reports/phase3_field_separation_strategy.md`
- [x] Update `docs/assumptions_register.md` with any architecture-level assumptions/overrides
- [ ] Phase 3 exit memo with Phase 4 readiness recommendation

## Immediate Next Actions (Execution Order)
1. Draft architecture spec and include explicit stage boundaries.
2. Draft validation gate table with threshold + owner + fail action.
3. Draft field separation strategy with independent artifacts for DARAJAT and SALAK.
4. Cross-check all three documents against project non-negotiables before sign-off.
