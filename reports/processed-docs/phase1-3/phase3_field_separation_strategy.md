# Phase 3 Field Separation Strategy (DARAJAT vs SALAK)

## Goal
Operationalize strict field separation for design, validation, and reporting so field-specific geology/operations are not conflated.

## Scope
Applies to all Phase 3+ artifacts that involve baseline summaries, driver screening, validation splits, or estimation outputs.

## Separation Principles
1. **Independent processing branches:** DARAJAT and SALAK are split immediately after gate validation.
2. **Independent evidence claims:** Driver claims must be field-specific unless pooled analysis is explicitly justified.
3. **Independent validation reporting:** Accuracy/error metrics are published separately by field.
4. **Shared schema, separate metrics:** Same column contracts are used, but statistics are computed independently.

## Execution Rules

### Rule A — Data Branching
- Create field partitions from canonical contracts using `field`.
- Reject rows with null/unknown field before branch execution.

### Rule B — Baseline Generation
- Compute baseline summaries separately for DARAJAT and SALAK.
- Do not average/merge field summaries into a single baseline table without explicit waiver.

### Rule C — Driver Screening
- Run feature association/correlation screening per field.
- Require field-labeled outputs and p-value/effect-size reporting by field.

### Rule D — Holdout Strategy
- Create independent holdout identifiers per field.
- Prohibit cross-field leakage between training and holdout artifacts.

### Rule E — Reporting
- Publish each phase output with either:
  - separate files per field, or
  - single file containing explicit `field` partitions and sectioned interpretation.

## Planned Output Convention
- `data/processed/baseline_estimates_darajat.csv`
- `data/processed/baseline_estimates_salak.csv`
- `reports/feature_correlation_darajat.md`
- `reports/feature_correlation_salak.md`
- `reports/validation_darajat.md`
- `reports/validation_salak.md`

## Pooled-Analysis Exception Policy
Pooling is disallowed by default. An exception requires all of the following:
1. Documented statistical test and result supporting pooling.
2. Business justification in `docs/assumptions_register.md`.
3. Explicit sign-off in phase exit memo.

## Current-Layer Constraints (2026-04-02)
- `well_canonical` is blank at current Lv.5 row-grain; therefore well-level analysis must remain design-scoped until a richer grain is added.
- `event_code_raw` is blank at current Lv.5 row-grain; event-driver claims must be deferred or marked insufficient-evidence.

## Phase 3 Completion Check for Separation
- [x] Field split rules documented.
- [x] Output naming strategy documented.
- [x] Pooled-analysis exception workflow documented.
- [x] Current data-grain constraints carried forward.
