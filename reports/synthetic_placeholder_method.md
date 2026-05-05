# Synthetic Placeholder Method

This staging layer is placeholder-only for future old/new campaign integration and is **excluded from training and validation**.

## Macro factor
`synthetic_cost = base_cost * macro_factor`
`macro_factor = 0.7 * (CPI_target / CPI_base) + 0.3 * (Brent_target / Brent_base)`

## Generated synthetic campaigns
| synthetic_campaign_id | base_campaign | target_year | macro_factor |
|---|---|---:|---:|
| SLK_2020 | SALAK_2025_2026 | 2020 | 0.728420 |
| DRJ_2019 | DARAJAT_2022 | 2019 | 0.802693 |
| SLK_2012 | SALAK_2025_2026 | 2012 | 0.929206 |
| DRJ_2011 | DARAJAT_2022 | 2011 | 0.868776 |
| SLK_2026 | SALAK_2025_2026 | 2026 | 1.017005 |
| DRJ_2027 | DARAJAT_2023_2024 | 2027 | 1.052253 |

## Output counts
- synthetic campaign rows: **6**
- synthetic WBS Lv.5 placeholder rows: **1382**

## Notes
- Non-cost structural fields are copied from nearest same-field real campaign templates.
- Only cost-like numeric fields are scaled by macro factor.
- All synthetic rows set `include_for_training = no` and `include_for_validation = no`.
