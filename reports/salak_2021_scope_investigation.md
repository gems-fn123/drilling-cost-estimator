# SALAK_2021 Scope Investigation

## Objective
Assess whether SALAK_2021 can be moved from `legacy_reference` to `in_scope` for the Phase 4 pipeline.

## Evidence
- Data.Summary Lv5 cost rows mapped to SALAK_2021 labels: **0**.
- Data.Summary Lv5 cost rows for current in-scope labels (`DRJ 2022`, `DRJ 2023`, `SLK 2025`): **822**.
- Non-Data.Summary sheets with SALAK 2021 references: **1. WellName.Dictionary, 2. Drilling.Data.History, Drilled.Well**.

## Assessment
- Current Phase 4 ingestion contract requires cost-bearing Lv5 rows in `Data.Summary`.
- SALAK_2021 appears as campaign/well reference context outside the active in-scope cost-bearing Lv5 path.

## Recommendation
- Keep `SALAK_2021` as **`legacy_reference`** in this phase.
- Do not promote to `in_scope` and do not synthesize SALAK_2021 cost rows unless authoritative Lv5 cost-bearing rows are available.
