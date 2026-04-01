# Project Instructions — Executive Summary

## Purpose
Define project goal, execution sequence, and non-negotiable constraints for all development work.

## Audience
Project leadership, AI agents, and core development teams.

## Prerequisites
For detail: See [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md)

## Project Goal
Build a **statistically valid drilling campaign cost estimator at WBS Level 5** with separate field validation (DARAJAT, SALAK) and auditable lineage to source data.

## Execution Sequence (6 Phases)
1. **Discover** — Align data sources, naming conventions, hierarchy
2. **Define** — Lock canonical schema and data contracts
3. **Design** — Architect pipeline: ingest → validate → normalize → model
4. **Develop** — Implement transforms, generate canonical datasets
5. **Demonstrate** — Validate models separately by field, publish uncertainty bands
6. **Deploy** — Operationalize refresh process, release Streamlit app

## Core Constraints (Non-Negotiable)

### Development Constraints
- **No modeling during ingestion task** — Phases 1–4 are data engineering only
- **Separate field analysis** — DARAJAT and SALAK must have independent validation metrics
- **Hierarchy validation first** — Every L5 item must map to valid L1–L4 path
- **Stop before app** — Streamlit development only after Phase 5 completion

### Data Constraints
- **Evidence-based drivers** — Cost drivers require correlation/regression evidence
- **Interpretability first** — Methods: correlation → simple regression → grouped benchmarking
- **Uncertainty required** — Every estimate must have confidence bands
- **Traceability** — Every estimate must link back to source rows

### Documentation Constraints
- **Record rationale** — Document all assumptions, overrides, exclusions
- **Data sufficiency flags** — Mark confidence for each driver (sample size, variance, missing %)
- **Assumption register** — Maintain `docs/assumptions_register.md` for manual interventions
- **Auditable outputs** — All artifacts in `data/processed/` and `reports/` with version, timestamp

## Success Metrics
- ✓ Canonical well-mapping and campaign-mapping complete (Phases 2–4)
- ✓ Driver validation completed separately for DARAJAT and SALAK (Phase 5)
- ✓ Estimates published with MAE/MAPE and confidence intervals by WBS level (Phase 5)
- ✓ Streamlit app operational with drill-down and scenario builder (Phase 6)
