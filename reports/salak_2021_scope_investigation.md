# SALAK_2021 Scope Investigation

## Objective
Assess whether SALAK_2021 can be moved from `legacy_reference` to `in_scope` for the Phase 4 pipeline.

## Evidence
- Structured.Cost Lv5 cost rows mapped to SALAK_2021 labels: **111**.
- Structured.Cost Lv5 cost rows for current in-scope labels (`DRJ - 2022`, `DRJ - 2024`, `SLK - 2025`): **646**.
- Non-Structured.Cost sheets with SALAK 2021 references: **DashBoard.Tab.Template, Drill.Campaign.Ref.Tidy, General.Camp.Data, NPT.Data, Piv.Struct.Cost, Pivot.Master, Sheet9**.

## Assessment
- Current Phase 4 ingestion contract requires cost-bearing Lv5 rows in `Structured.Cost`.
- SALAK_2021 appears as campaign scope in the dashboard history and remains available for benchmarking/reporting.

## Recommendation
- Keep `SALAK_2021` as dashboard-historical scope for estimator context.
- Continue field-specific reporting and avoid cross-field pooling without statistical validation.
