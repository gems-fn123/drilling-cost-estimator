# Unit Price Scope Coverage

Ground-up canonical scope for the dashboard-driven unit-price build.

| field | campaign_id | campaign_code | include_for_estimator | actual_cost_total | canonical_well_count | source_file | source_sheet |
|---|---|---|---|---:|---:|---|---|
| DARAJAT | DARAJAT_2019 | E530-30101-D19001 | yes | 42003384.16 | 5 | 20260327_WBS_Data.xlsx | Drilled.Well |
| DARAJAT | DARAJAT_2022 | E530-30101-D225301 | yes | 30669524.90 | 6 | 20260327_WBS_Data.xlsx | Drilled.Well |
| DARAJAT | DARAJAT_2023_2024 | E530-30101-D235301 | yes | 37367109.64 | 6 | 20260327_WBS_Data.xlsx | Drilled.Well |
| SALAK | SALAK_2021 | E540-30101-D20001 | yes | 28051247.74 | 5 | 20260327_WBS_Data.xlsx | Drilled.Well |
| SALAK | SALAK_2025_2026 | E540-30101-D245401 | yes | 38522325.57 | 9 | 20260327_WBS_Data.xlsx | Drilled.Well |
| WAYANG_WINDU | WAYANG_WINDU_2018 | E500-2-0-8501-185003 | yes | 26986999.90 | 4 | 20260327_WBS_Data.xlsx | Drilled.Well |
| WAYANG_WINDU | WAYANG_WINDU_2021 | E500-30101-D205011 | yes | 27074998.19 | 6 | 20260327_WBS_Data.xlsx | Drilled.Well |

## Notes
- Campaign scope is workbook-driven and no longer limited to the legacy three-campaign estimator subset.
- Canonical well names come from the combined alias layer: primary workbook observations, dashboard workbook General.Camp.Data, and manual alias rules.
- `DRJ-STEAM 1` remains in estimator scope but excluded from well-level training until confirmed.
