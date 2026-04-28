# Unit Price Macro Correlation

Ground-up yearly macro correlation support for the dashboard-driven unit-price estimator.

## Source Package
- Macro reference window: **2019-2026**.
- Source: **IMF World Economic Outlook (April 2026)** annual dataset, published **April 15, 2026**.
- Reference URL: `https://data.imf.org/en/datasets/IMF.RES%3AWEO`.
- Brent series uses `POILBRE`.
- Indonesia inflation context uses `PCPI` and `PCPIPCH`.
- Steel commodity input uses `PIORECR` iron ore as a steel-input proxy because a direct annual steel-HRC series was not available in the official annual files used here.

## Operational Rule
- Operational forecast weights are computed on the **pooled pricing-basis yearly series** only.
- Field-specific yearly Pearson outputs are retained for audit, but they are **diagnostic only** because DARAJAT has 3 overlap years, SALAK has 2, and WW has 1 in the current unit-price history window.
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

## Recommendation
- Keep macro weighting as a separate external-adjustment layer only.
- Use the pooled pricing-basis rows as the auditable weight source when an external scenario is requested.
- Keep field-specific rows visible in processed outputs, but do not let them drive estimator scaling until more yearly history is added.
