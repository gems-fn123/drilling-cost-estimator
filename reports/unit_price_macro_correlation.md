# Unit Price Macro Correlation

Ground-up yearly macro correlation support for the dashboard-driven unit-price estimator.

## Source Package
- Macro reference window: **2019-2026**.
- Source: **IMF World Economic Outlook (April 2026)** annual dataset, published **April 15, 2026**.
- Reference URL: `https://data.imf.org/en/datasets/IMF.RES%3AWEO`.
- Brent series uses `POILBRE`.
- Indonesia inflation context uses `PCPI` and `PCPIPCH`.
- Steel commodity input uses `PIORECR` iron ore as a steel-input proxy because a direct annual steel-HRC series was not available in the official annual files used here.
- The deeper WBS cluster layer uses fuzzy-matched Level 4 descriptions, with Level 5 acting only as a fallback when Level 4 is missing, so campaign structure drift stays inside the same audit bucket.

## Operational Rule
- Operational forecast weights are computed on the **pooled pricing-basis yearly series** only.
- Field-specific yearly Pearson outputs are retained for audit, but they are **diagnostic only** because DARAJAT has 3 overlap years, SALAK has 2, and WW has 1 in the current unit-price history window.
- The clustered WBS depth layer is published as a separate diagnostic and screening view; it is not yet wired into live estimator scaling even when a cluster has enough support to calculate weights.
- **Nominal/as-is Pearson** is the active weight basis. CPI-discounted 2026-equivalent comparisons are diagnostic only because the discounted treatment materially changes ordering/sign in several cells.
- Correlation direction is preserved for audit, but weight magnitudes use absolute Pearson values. Negative signs indicate historical co-movement in this sparse sample, not a recommended inverse causal escalator.

## Recommended Operational Weights
| pricing_basis | factor | pearson_nominal | pearson_discounted_2026 | forecast_weight | direction | overlap_years |
|---|---|---:|---:|---:|---|---|
| active_day_rate | Brent oil price | -0.318628 | -0.759517 | 0.223048 | negative | 2019,2021,2022,2024,2025 |
| active_day_rate | Indonesia CPI index | 0.854771 | n/a | 0.598362 | positive | 2019,2021,2022,2024,2025 |
| active_day_rate | Steel proxy commodity price | -0.255120 | -0.375408 | 0.178590 | negative | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | Brent oil price | -0.464327 | -0.372449 | 0.327101 | negative | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | Indonesia CPI index | -0.069988 | n/a | 0.049304 | negative | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | Steel proxy commodity price | -0.885208 | -0.598944 | 0.623595 | negative | 2019,2021,2022,2024,2025 |
| depth_rate | Brent oil price | -0.604405 | -0.320719 | 0.361759 | negative | 2019,2021,2022,2024,2025 |
| depth_rate | Indonesia CPI index | -0.588292 | n/a | 0.352115 | negative | 2019,2021,2022,2024,2025 |
| depth_rate | Steel proxy commodity price | -0.478042 | -0.141400 | 0.286126 | negative | 2019,2021,2022,2024,2025 |

## Clustered WBS Depth Layer
| pricing_basis | wbs_cluster | field_coverage_count | field_count_floor | overlap_year_count | support_status | factor | pearson_nominal | pearson_discounted_2026 | forecast_weight | direction |
|---|---|---:|---:|---:|---|---|---:|---:|---:|---|
| active_day_rate | services | 3 | 1 | 5 | operational | Brent oil price | -0.874515 | -0.548903 | 0.552373 | negative |
| active_day_rate | services | 3 | 1 | 5 | operational | Indonesia CPI index | -0.624727 | n/a | 0.394599 | negative |
| active_day_rate | services | 3 | 1 | 5 | operational | Steel proxy commodity price | 0.083954 | 0.282877 | 0.053028 | positive |
| campaign_scope_benchmark | construction | 3 | 1 | 5 | operational | Brent oil price | -0.297423 | -0.125778 | 0.201141 | negative |
| campaign_scope_benchmark | construction | 3 | 1 | 5 | operational | Indonesia CPI index | -0.586486 | n/a | 0.396627 | negative |
| campaign_scope_benchmark | construction | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.594773 | -0.379797 | 0.402232 | negative |
| campaign_scope_benchmark | drill cutting | 3 | 1 | 4 | operational | Brent oil price | -0.406029 | -0.508550 | 0.229482 | negative |
| campaign_scope_benchmark | drill cutting | 3 | 1 | 4 | operational | Indonesia CPI index | 0.718216 | n/a | 0.405926 | positive |
| campaign_scope_benchmark | drill cutting | 3 | 1 | 4 | operational | Steel proxy commodity price | -0.645084 | -0.555201 | 0.364593 | negative |
| campaign_scope_benchmark | drilling facilities support | 3 | 1 | 4 | operational | Brent oil price | -0.399761 | -0.489711 | 0.257957 | negative |
| campaign_scope_benchmark | drilling facilities support | 3 | 1 | 4 | operational | Indonesia CPI index | 0.605808 | n/a | 0.390914 | positive |
| campaign_scope_benchmark | drilling facilities support | 3 | 1 | 4 | operational | Steel proxy commodity price | -0.544153 | -0.541764 | 0.351130 | negative |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 5 | operational | Brent oil price | -0.325673 | -0.135264 | 0.208221 | negative |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 5 | operational | Indonesia CPI index | -0.584520 | n/a | 0.373715 | negative |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.653886 | -0.425995 | 0.418064 | negative |
| campaign_scope_benchmark | engineering | 3 | 1 | 4 | operational | Brent oil price | -0.508380 | -0.663279 | 0.248973 | negative |
| campaign_scope_benchmark | engineering | 3 | 1 | 4 | operational | Indonesia CPI index | 0.832472 | n/a | 0.407692 | positive |
| campaign_scope_benchmark | engineering | 3 | 1 | 4 | operational | Steel proxy commodity price | -0.701060 | -0.723252 | 0.343335 | negative |
| campaign_scope_benchmark | environmental monitoring | 3 | 1 | 4 | operational | Brent oil price | -0.003036 | -0.136921 | 0.003123 | flat |
| campaign_scope_benchmark | environmental monitoring | 3 | 1 | 4 | operational | Indonesia CPI index | 0.526659 | n/a | 0.541825 | positive |
| campaign_scope_benchmark | environmental monitoring | 3 | 1 | 4 | operational | Steel proxy commodity price | -0.442314 | -0.441670 | 0.455052 | negative |
| campaign_scope_benchmark | explosive | 3 | 1 | 4 | operational | Brent oil price | -0.172238 | -0.003658 | 0.229773 | negative |
| campaign_scope_benchmark | explosive | 3 | 1 | 4 | operational | Indonesia CPI index | -0.303697 | n/a | 0.405145 | negative |
| campaign_scope_benchmark | explosive | 3 | 1 | 4 | operational | Steel proxy commodity price | 0.273665 | 0.402269 | 0.365082 | positive |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 4 | operational | Brent oil price | 0.974152 | 0.991855 | 0.686289 | positive |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 4 | operational | Indonesia CPI index | -0.408787 | n/a | 0.287990 | negative |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 4 | operational | Steel proxy commodity price | 0.036510 | 0.106699 | 0.025721 | flat |
| campaign_scope_benchmark | interpad move | 3 | 1 | 5 | operational | Brent oil price | 0.035342 | 0.172308 | 0.024579 | flat |
| campaign_scope_benchmark | interpad move | 3 | 1 | 5 | operational | Indonesia CPI index | -0.460891 | n/a | 0.320536 | negative |
| campaign_scope_benchmark | interpad move | 3 | 1 | 5 | operational | Steel proxy commodity price | 0.941641 | 0.974536 | 0.654885 | positive |
| campaign_scope_benchmark | lih | 3 | 1 | 4 | operational | Brent oil price | -0.416278 | -0.178809 | 0.192924 | negative |
| campaign_scope_benchmark | lih | 3 | 1 | 4 | operational | Indonesia CPI index | -0.783703 | n/a | 0.363207 | negative |
| campaign_scope_benchmark | lih | 3 | 1 | 4 | operational | Steel proxy commodity price | 0.957752 | 0.941996 | 0.443869 | positive |
| campaign_scope_benchmark | pgpa | 3 | 1 | 5 | operational | Brent oil price | -0.533897 | -0.349454 | 0.307994 | negative |
| campaign_scope_benchmark | pgpa | 3 | 1 | 5 | operational | Indonesia CPI index | -0.540803 | n/a | 0.311978 | negative |
| campaign_scope_benchmark | pgpa | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.658765 | -0.450284 | 0.380028 | negative |
| campaign_scope_benchmark | procurement | 3 | 1 | 5 | operational | Brent oil price | -0.648186 | -0.446516 | 0.362382 | negative |
| campaign_scope_benchmark | procurement | 3 | 1 | 5 | operational | Indonesia CPI index | -0.541056 | n/a | 0.302489 | negative |
| campaign_scope_benchmark | procurement | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.599439 | -0.385751 | 0.335129 | negative |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 5 | operational | Brent oil price | 0.055965 | 0.015473 | 0.063921 | positive |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 5 | operational | Indonesia CPI index | 0.137047 | n/a | 0.156530 | positive |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 5 | operational | Steel proxy commodity price | -0.682519 | -0.555884 | 0.779549 | negative |
| campaign_scope_benchmark | security | 3 | 1 | 4 | operational | Brent oil price | -0.320135 | -0.070638 | 0.158307 | negative |
| campaign_scope_benchmark | security | 3 | 1 | 4 | operational | Indonesia CPI index | -0.765715 | n/a | 0.378647 | negative |
| campaign_scope_benchmark | security | 3 | 1 | 4 | operational | Steel proxy commodity price | 0.936391 | 0.940088 | 0.463046 | positive |
| campaign_scope_benchmark | services | 2 | 1 | 4 | operational | Brent oil price | -0.238209 | -0.219634 | 0.192966 | negative |
| campaign_scope_benchmark | services | 2 | 1 | 4 | operational | Indonesia CPI index | 0.163634 | n/a | 0.132555 | positive |
| campaign_scope_benchmark | services | 2 | 1 | 4 | operational | Steel proxy commodity price | 0.832614 | 0.887508 | 0.674478 | positive |
| campaign_scope_benchmark | well insurance | 3 | 1 | 5 | operational | Brent oil price | 0.522457 | 0.667256 | 0.295886 | positive |
| campaign_scope_benchmark | well insurance | 3 | 1 | 5 | operational | Indonesia CPI index | -0.693515 | n/a | 0.392762 | negative |
| campaign_scope_benchmark | well insurance | 3 | 1 | 5 | operational | Steel proxy commodity price | 0.549767 | 0.661639 | 0.311352 | positive |
| campaign_scope_benchmark | well testing | 2 | 1 | 5 | operational | Brent oil price | 0.350712 | 0.182708 | 0.240651 | positive |
| campaign_scope_benchmark | well testing | 2 | 1 | 5 | operational | Indonesia CPI index | 0.845816 | n/a | 0.580380 | positive |
| campaign_scope_benchmark | well testing | 2 | 1 | 5 | operational | Steel proxy commodity price | -0.260821 | -0.408586 | 0.178969 | negative |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 5 | operational | Brent oil price | -0.640794 | -0.680960 | 0.380085 | negative |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 5 | operational | Indonesia CPI index | 0.222904 | n/a | 0.132215 | positive |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.822225 | -0.716712 | 0.487700 | negative |
| depth_rate | material ll | 3 | 1 | 5 | operational | Brent oil price | -0.471491 | -0.147553 | 0.321642 | negative |
| depth_rate | material ll | 3 | 1 | 5 | operational | Indonesia CPI index | -0.913169 | n/a | 0.622946 | negative |
| depth_rate | material ll | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.081227 | 0.176593 | 0.055411 | negative |

## Cluster Coverage
| pricing_basis | wbs_cluster | field_coverage_count | field_count_floor | field_count_peak | overlap_year_count | support_status | observation_years |
|---|---|---:|---:|---:|---:|---|---|
| active_day_rate | services | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | construction | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | interpad move | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | pgpa | 3 | 1 | 1 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | procurement | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 1 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | well insurance | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | well testing | 2 | 1 | 1 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| depth_rate | material ll | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | drill cutting | 3 | 1 | 2 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | drilling facilities support | 3 | 1 | 2 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | engineering | 3 | 1 | 1 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | environmental monitoring | 3 | 1 | 2 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | explosive | 3 | 1 | 1 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 2 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | lih | 3 | 1 | 2 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | security | 3 | 1 | 1 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | services | 2 | 1 | 1 | 4 | operational | 2019,2021,2022,2025 |
| campaign_scope_benchmark | conductor casing installation material | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2021,2024,2025 |
| campaign_scope_benchmark | hardware supply | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| campaign_scope_benchmark | internet and it support service | 3 | 1 | 2 | 3 | diagnostic_only_thin_history | 2021,2022,2025 |
| campaign_scope_benchmark | project management cost | 3 | 1 | 2 | 3 | diagnostic_only_thin_history | 2021,2022,2025 |
| campaign_scope_benchmark | she permit | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2021,2022,2024 |
| depth_rate | material non ll | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| campaign_scope_benchmark | rig skid | 3 | 1 | 2 | 2 | insufficient_history | 2021,2024 |
| campaign_scope_benchmark | skid moving | 2 | 1 | 1 | 2 | insufficient_history | 2022,2025 |
| campaign_scope_benchmark | contingency | 1 | 1 | 1 | 1 | insufficient_history | 2025 |
| campaign_scope_benchmark | logging cost | 1 | 1 | 1 | 1 | insufficient_history | 2025 |
| campaign_scope_benchmark | material | 1 | 1 | 1 | 1 | insufficient_history | 2022 |
| campaign_scope_benchmark | pgpa security | 1 | 1 | 1 | 1 | insufficient_history | 2021 |
| per_well_job | conductor casing installation material | 1 | 1 | 1 | 1 | insufficient_history | 2021 |
| per_well_job | project management cost | 1 | 1 | 1 | 1 | insufficient_history | 2021 |

## Scope Support
| scope_type | field | pricing_basis | overlap_year_count | support_status |
|---|---|---|---:|---|
| field_pricing_basis | DARAJAT | active_day_rate | 3 | diagnostic_only_thin_history |
| field_pricing_basis | DARAJAT | campaign_scope_benchmark | 3 | diagnostic_only_thin_history |
| field_pricing_basis | DARAJAT | depth_rate | 3 | diagnostic_only_thin_history |
| field_pricing_basis | SALAK | active_day_rate | 2 | insufficient_history |
| field_pricing_basis | SALAK | campaign_scope_benchmark | 2 | insufficient_history |
| field_pricing_basis | SALAK | depth_rate | 2 | insufficient_history |
| field_pricing_basis | WAYANG_WINDU | active_day_rate | 1 | insufficient_history |
| field_pricing_basis | WAYANG_WINDU | campaign_scope_benchmark | 1 | insufficient_history |
| field_pricing_basis | WAYANG_WINDU | depth_rate | 1 | insufficient_history |
| field_pricing_basis | WAYANG_WINDU | per_well_job | 1 | insufficient_history |
| pooled_pricing_basis | ALL_FIELDS | active_day_rate | 5 | operational |
| pooled_pricing_basis | ALL_FIELDS | campaign_scope_benchmark | 5 | operational |
| pooled_pricing_basis | ALL_FIELDS | depth_rate | 5 | operational |
| pooled_pricing_basis | ALL_FIELDS | per_well_job | 1 | insufficient_history |

## Interpretation
- `active_day_rate` is the cleanest direct-well macro series after correcting the denominator to unique wells rather than repeated cost rows.
- `depth_rate` remains materially different from `active_day_rate`, which supports keeping material/depth and service/day logic separate in the estimator.
- `campaign_scope_benchmark` is the most steel-sensitive pooled basis in the current sample.
- `per_well_job` remains unsupported for macro weighting because only one in-range observation exists.
- The recurring cluster layer shows that casing, mud, rig, and other service-time families can be screened with the same annual macro proxies across all fields.

## Recommendation
- Keep macro weighting as a separate external-adjustment layer only.
- Use the pooled pricing-basis rows as the auditable weight source when an external scenario is requested.
- Use the clustered WBS layer to prioritize which subdrivers deserve future estimator promotion once the field-balanced signal is proven stable.
- Keep field-specific rows visible in processed outputs, but do not let them drive estimator scaling until more yearly history is added.
