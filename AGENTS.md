# Working Rules & Startup Guide

## Purpose
Quick reference for core working rules and startup sequence for all contributors and agents.

## Audience
All project contributors, AI agents, and development teams.

## Prerequisites
- First time? Read [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) section 1–3
- Quick onboarding? See [docs/QUICK_START_CHECKLIST.md](docs/QUICK_START_CHECKLIST.md)

## Read First (Sequence)
1. This file (`AGENTS.md`) — core rules
2. [GPT_PROJECT_INSTRUCTIONS.md](GPT_PROJECT_INSTRUCTIONS.md) — scope & phases
3. [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) — full reference

## Core Working Rules (Non-Negotiable)

### Field Specificity
- ✓ Keep outputs field-specific: analyze DARAJAT and SALAK **separately** where required
- ✓ Do not pool fields without statistical justification
- Rationale: Different geology, operations, and cost structures require independent validation

### Evidence-Based Drivers
- ✓ Do not invent cost drivers without data validation
- ✓ Record rationale, exclusions, uncertainty, and data sufficiency flags
- Rationale: Credible estimates require data support, not assumptions

### Stepwise Delivery
- ✓ Strict sequence: Ingestion → Classification → Driver Validation → App
- ✗ No modeling during ingestion task
- ✗ No app development before Phase 5 (Demonstrate) completion
- Rationale: Premature modeling on unvalidated data produces unreliable estimates

### Auditability
- ✓ Prefer clear, auditable artifacts in `data/processed/` and `reports/`
- ✓ Every estimate traceable to source rows
- ✓ Persist model version, data timestamp, assumptions register
- Rationale: Stakeholders must understand and trust the estimates

## Success Criteria
- [ ] All outputs saved in designated locations with canonical column names
- [ ] No cost driver claimed without supporting correlation/regression evidence
- [ ] Separate validation metrics for DARAJAT and SALAK reported
- [ ] Assumption register maintained and published with deliverables
