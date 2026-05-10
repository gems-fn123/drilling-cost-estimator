# Unit Price Macro Correlation

Ground-up yearly macro correlation support for the dashboard-driven unit-price estimator.

## Source Package
- Macro reference window: **2019-2026**.
- Source: **IMF World Economic Outlook (April 2026)** annual dataset, published **April 15, 2026**.
- Reference URL: `https://www.worldbank.org/en/research/commodity-markets`.
- Brent series uses `POILBRE`.
- Indonesia CPI level uses IMF `PCPI`. Indonesia inflation rate (`PCPIPCH`) is retained in the reference file but excluded from operational weighting (it is collinear with CPI level and adds no independent signal).
- Steel input uses **World Bank Pink Sheet Steel Products composite** (HRC, CRC, rebar average, USD/MT) as the direct casing cost proxy. This replaces the prior iron-ore (`PIORECR`) proxy, which is an upstream input, not a finished-steel price.
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
| active_day_rate | Brent oil price | -0.318628 | -0.759517 | 0.201038 | negative | 2019,2021,2022,2024,2025 |
| active_day_rate | Indonesia CPI index | 0.854771 | n/a | 0.539316 | positive | 2019,2021,2022,2024,2025 |
| active_day_rate | Steel (HRC composite, USD/t) | -0.411518 | -0.533915 | 0.259646 | negative | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | Brent oil price | -0.464327 | -0.372449 | 0.314255 | negative | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | Indonesia CPI index | -0.069988 | n/a | 0.047368 | negative | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | Steel (HRC composite, USD/t) | -0.943232 | -0.680583 | 0.638377 | negative | 2019,2021,2022,2024,2025 |
| depth_rate | Brent oil price | -0.604405 | -0.320719 | 0.336051 | negative | 2019,2021,2022,2024,2025 |
| depth_rate | Indonesia CPI index | -0.588292 | n/a | 0.327092 | negative | 2019,2021,2022,2024,2025 |
| depth_rate | Steel (HRC composite, USD/t) | -0.605854 | -0.282765 | 0.336857 | negative | 2019,2021,2022,2024,2025 |

## Clustered WBS Depth Layer
| pricing_basis | wbs_cluster | field_coverage_count | field_count_floor | overlap_year_count | support_status | factor | pearson_nominal | pearson_discounted_2026 | forecast_weight | direction |
|---|---|---:|---:|---:|---|---|---:|---:|---:|---|
| active_day_rate | services | 3 | 1 | 5 | operational | Brent oil price | -0.874515 | -0.548903 | 0.521859 | negative |
| active_day_rate | services | 3 | 1 | 5 | operational | Indonesia CPI index | -0.624727 | n/a | 0.372800 | negative |
| active_day_rate | services | 3 | 1 | 5 | operational | Steel (HRC composite, USD/t) | -0.176528 | 0.040184 | 0.105342 | negative |
| campaign_scope_benchmark | construction | 3 | 1 | 5 | operational | Brent oil price | -0.297423 | -0.125778 | 0.202645 | negative |
| campaign_scope_benchmark | construction | 3 | 1 | 5 | operational | Indonesia CPI index | -0.586486 | n/a | 0.399593 | negative |
| campaign_scope_benchmark | construction | 3 | 1 | 5 | operational | Steel (HRC composite, USD/t) | -0.583800 | -0.421806 | 0.397763 | negative |
| campaign_scope_benchmark | drill cutting | 3 | 1 | 4 | operational | Brent oil price | -0.406029 | -0.508550 | 0.228901 | negative |
| campaign_scope_benchmark | drill cutting | 3 | 1 | 4 | operational | Indonesia CPI index | 0.718216 | n/a | 0.404899 | positive |
| campaign_scope_benchmark | drill cutting | 3 | 1 | 4 | operational | Steel (HRC composite, USD/t) | -0.649573 | -0.543357 | 0.366200 | negative |
| campaign_scope_benchmark | drilling facilities support | 3 | 1 | 4 | operational | Brent oil price | -0.399761 | -0.489711 | 0.260720 | negative |
| campaign_scope_benchmark | drilling facilities support | 3 | 1 | 4 | operational | Indonesia CPI index | 0.605808 | n/a | 0.395101 | positive |
| campaign_scope_benchmark | drilling facilities support | 3 | 1 | 4 | operational | Steel (HRC composite, USD/t) | -0.527729 | -0.521817 | 0.344179 | negative |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 5 | operational | Brent oil price | -0.325673 | -0.135264 | 0.221756 | negative |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 5 | operational | Indonesia CPI index | -0.584520 | n/a | 0.398008 | negative |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 5 | operational | Steel (HRC composite, USD/t) | -0.558420 | -0.401648 | 0.380236 | negative |
| campaign_scope_benchmark | engineering | 3 | 1 | 4 | operational | Brent oil price | -0.508380 | -0.663279 | 0.238354 | negative |
| campaign_scope_benchmark | engineering | 3 | 1 | 4 | operational | Indonesia CPI index | 0.832472 | n/a | 0.390304 | positive |
| campaign_scope_benchmark | engineering | 3 | 1 | 4 | operational | Steel (HRC composite, USD/t) | -0.792031 | -0.793024 | 0.371343 | negative |
| campaign_scope_benchmark | environmental monitoring | 3 | 1 | 4 | operational | Brent oil price | -0.003036 | -0.136921 | 0.002653 | flat |
| campaign_scope_benchmark | environmental monitoring | 3 | 1 | 4 | operational | Indonesia CPI index | 0.526659 | n/a | 0.460301 | positive |
| campaign_scope_benchmark | environmental monitoring | 3 | 1 | 4 | operational | Steel (HRC composite, USD/t) | -0.614466 | -0.577095 | 0.537045 | negative |
| campaign_scope_benchmark | explosive | 3 | 1 | 4 | operational | Brent oil price | -0.172238 | -0.003658 | 0.197850 | negative |
| campaign_scope_benchmark | explosive | 3 | 1 | 4 | operational | Indonesia CPI index | -0.303697 | n/a | 0.348856 | negative |
| campaign_scope_benchmark | explosive | 3 | 1 | 4 | operational | Steel (HRC composite, USD/t) | 0.394615 | 0.496242 | 0.453294 | positive |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 4 | operational | Brent oil price | 0.974152 | 0.991855 | 0.522950 | positive |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 4 | operational | Indonesia CPI index | -0.408787 | n/a | 0.219447 | negative |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 4 | operational | Steel (HRC composite, USD/t) | 0.479864 | 0.461988 | 0.257603 | positive |
| campaign_scope_benchmark | interpad move | 3 | 1 | 5 | operational | Brent oil price | 0.035342 | 0.172308 | 0.026901 | flat |
| campaign_scope_benchmark | interpad move | 3 | 1 | 5 | operational | Indonesia CPI index | -0.460891 | n/a | 0.350821 | negative |
| campaign_scope_benchmark | interpad move | 3 | 1 | 5 | operational | Steel (HRC composite, USD/t) | 0.817515 | 0.858457 | 0.622277 | positive |
| campaign_scope_benchmark | lih | 3 | 1 | 4 | operational | Brent oil price | -0.416278 | -0.178809 | 0.216158 | negative |
| campaign_scope_benchmark | lih | 3 | 1 | 4 | operational | Indonesia CPI index | -0.783703 | n/a | 0.406948 | negative |
| campaign_scope_benchmark | lih | 3 | 1 | 4 | operational | Steel (HRC composite, USD/t) | 0.725824 | 0.752971 | 0.376894 | positive |
| campaign_scope_benchmark | pgpa | 3 | 1 | 5 | operational | Brent oil price | -0.533897 | -0.349454 | 0.303978 | negative |
| campaign_scope_benchmark | pgpa | 3 | 1 | 5 | operational | Indonesia CPI index | -0.540803 | n/a | 0.307910 | negative |
| campaign_scope_benchmark | pgpa | 3 | 1 | 5 | operational | Steel (HRC composite, USD/t) | -0.681668 | -0.521542 | 0.388112 | negative |
| campaign_scope_benchmark | procurement | 3 | 1 | 5 | operational | Brent oil price | -0.648186 | -0.446516 | 0.351335 | negative |
| campaign_scope_benchmark | procurement | 3 | 1 | 5 | operational | Indonesia CPI index | -0.541056 | n/a | 0.293267 | negative |
| campaign_scope_benchmark | procurement | 3 | 1 | 5 | operational | Steel (HRC composite, USD/t) | -0.655681 | -0.485269 | 0.355398 | negative |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 5 | operational | Brent oil price | 0.055965 | 0.015473 | 0.063734 | positive |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 5 | operational | Indonesia CPI index | 0.137047 | n/a | 0.156073 | positive |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 5 | operational | Steel (HRC composite, USD/t) | -0.685083 | -0.573071 | 0.780193 | negative |
| campaign_scope_benchmark | security | 3 | 1 | 4 | operational | Brent oil price | -0.320135 | -0.070638 | 0.181496 | negative |
| campaign_scope_benchmark | security | 3 | 1 | 4 | operational | Indonesia CPI index | -0.765715 | n/a | 0.434112 | negative |
| campaign_scope_benchmark | security | 3 | 1 | 4 | operational | Steel (HRC composite, USD/t) | 0.678014 | 0.746863 | 0.384391 | positive |
| campaign_scope_benchmark | services | 2 | 1 | 4 | operational | Brent oil price | -0.238209 | -0.219634 | 0.238495 | negative |
| campaign_scope_benchmark | services | 2 | 1 | 4 | operational | Indonesia CPI index | 0.163634 | n/a | 0.163831 | positive |
| campaign_scope_benchmark | services | 2 | 1 | 4 | operational | Steel (HRC composite, USD/t) | 0.596956 | 0.674492 | 0.597674 | positive |
| campaign_scope_benchmark | well insurance | 3 | 1 | 5 | operational | Brent oil price | 0.522457 | 0.667256 | 0.268168 | positive |
| campaign_scope_benchmark | well insurance | 3 | 1 | 5 | operational | Indonesia CPI index | -0.693515 | n/a | 0.355969 | negative |
| campaign_scope_benchmark | well insurance | 3 | 1 | 5 | operational | Steel (HRC composite, USD/t) | 0.732272 | 0.776270 | 0.375862 | positive |
| campaign_scope_benchmark | well testing | 2 | 1 | 5 | operational | Brent oil price | 0.350712 | 0.182708 | 0.237524 | positive |
| campaign_scope_benchmark | well testing | 2 | 1 | 5 | operational | Indonesia CPI index | 0.845816 | n/a | 0.572839 | positive |
| campaign_scope_benchmark | well testing | 2 | 1 | 5 | operational | Steel (HRC composite, USD/t) | -0.280005 | -0.375439 | 0.189637 | negative |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 5 | operational | Brent oil price | -0.640794 | -0.680960 | 0.359807 | negative |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 5 | operational | Indonesia CPI index | 0.222904 | n/a | 0.125161 | positive |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 5 | operational | Steel (HRC composite, USD/t) | -0.917239 | -0.822904 | 0.515032 | negative |
| depth_rate | material ll | 3 | 1 | 5 | operational | Brent oil price | -0.471491 | -0.147553 | 0.307397 | negative |
| depth_rate | material ll | 3 | 1 | 5 | operational | Indonesia CPI index | -0.913169 | n/a | 0.595358 | negative |
| depth_rate | material ll | 3 | 1 | 5 | operational | Steel (HRC composite, USD/t) | -0.149155 | 0.068178 | 0.097245 | negative |

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
