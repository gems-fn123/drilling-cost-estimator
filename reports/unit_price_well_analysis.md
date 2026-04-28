# Unit Price Well Analysis

Standard-only direct well analysis for the dashboard-driven estimator path.

## Rules Applied
- All new estimated wells are treated as `Standard-J` in the estimator path.
- Base well time uses `active_operational_days = actual_days - npt_days`.
- Service-time bands are field-specific terciles on `active_operational_days per 1000 ft`.
- Historical complexity is not used to split the direct well benchmark in this branch.

## Coverage
- Direct well profiles built: **39** wells.
- Estimator-pool direct wells after exclusions: **36** wells.
- Fields covered: **DARAJAT, SALAK, WAYANG_WINDU**.

## Direct Well Cost Mix
| field | service/time share % | material/depth share % | per-well job share % |
|---|---:|---:|---:|
| DARAJAT | 76.29 | 23.71 | 0.00 |
| SALAK | 75.50 | 24.50 | 0.00 |
| WAYANG_WINDU | 77.56 | 21.27 | 1.17 |

## Benchmark Medians
| field | active day rate (USD/day) | depth rate (USD/ft) | total direct well cost (USD/well) |
|---|---:|---:|---:|
| DARAJAT | 125194.778982 | 191.159354 | 4562998.050000 |
| SALAK | 154338.410605 | 151.651953 | 3187325.840000 |
| WAYANG_WINDU | 120075.650703 | 162.564208 | 4029036.510000 |

## Service-Time Bands
| field | fast | standard | careful | observation_count |
|---|---|---|---|---:|
| DARAJAT | <= 3.849287 days/1000ft | > 3.849287 and < 5.226638 days/1000ft | >= 5.226638 days/1000ft | 15 |
| SALAK | <= 2.334871 days/1000ft | > 2.334871 and < 3.393044 days/1000ft | >= 3.393044 days/1000ft | 11 |
| WAYANG_WINDU | <= 3.365819 days/1000ft | > 3.365819 and < 5.744854 days/1000ft | >= 5.744854 days/1000ft | 9 |

## Interpretation
- The dominant direct-well cost chunk remains the service/time side (`active_day_rate`) across all three fields.
- DARAJAT and WW show slower pace bands than SALAK, which is why field-specific service-time references are retained even though complexity splitting was removed.
- These outputs are suitable as the standard-well direct benchmark layer; shared/campaign scope should stay outside this file and remain in campaign/hybrid logic.
