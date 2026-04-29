# Unit Price Macro Correlation

Ground-up yearly macro correlation support for the dashboard-driven unit-price estimator.

## Source Package
- Macro reference window: **2019-2026**.
- Source: **IMF World Economic Outlook (April 2026)** annual dataset, published **April 15, 2026**.
- Reference URL: `https://data.imf.org/en/datasets/IMF.RES%3AWEO`.
- Brent series uses `POILBRE`.
- Indonesia inflation context uses `PCPI` and `PCPIPCH`.
- Steel commodity input uses `PIORECR` iron ore as a steel-input proxy because a direct annual steel-HRC series was not available in the official annual files used here.
- The deeper WBS cluster layer uses normalized `level_4 | level_5` paths and equal-field yearly averaging so one field cannot dominate the signal.

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
| active_day_rate | services \| bits reamer and core heads | 3 | 1 | 5 | operational | Brent oil price | -0.287365 | -0.644687 | 0.204789 | negative |
| active_day_rate | services \| bits reamer and core heads | 3 | 1 | 5 | operational | Indonesia CPI index | 0.886192 | n/a | 0.631538 | positive |
| active_day_rate | services \| bits reamer and core heads | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.229670 | -0.386237 | 0.163673 | negative |
| active_day_rate | services \| casing installation | 3 | 1 | 5 | operational | Brent oil price | -0.526928 | -0.587730 | 0.408411 | negative |
| active_day_rate | services \| casing installation | 3 | 1 | 5 | operational | Indonesia CPI index | 0.288186 | n/a | 0.223367 | positive |
| active_day_rate | services \| casing installation | 3 | 1 | 5 | operational | Steel proxy commodity price | 0.475077 | 0.535091 | 0.368223 | positive |
| active_day_rate | services \| cement cementing pump fees | 3 | 1 | 5 | operational | Brent oil price | -0.326803 | -0.577739 | 0.301575 | negative |
| active_day_rate | services \| cement cementing pump fees | 3 | 1 | 5 | operational | Indonesia CPI index | 0.657913 | n/a | 0.607124 | positive |
| active_day_rate | services \| cement cementing pump fees | 3 | 1 | 5 | operational | Steel proxy commodity price | 0.098939 | 0.132290 | 0.091301 | positive |
| active_day_rate | services \| contract rig | 3 | 1 | 5 | operational | Brent oil price | -0.162577 | 0.052138 | 0.157749 | negative |
| active_day_rate | services \| contract rig | 3 | 1 | 5 | operational | Indonesia CPI index | -0.745281 | n/a | 0.723150 | negative |
| active_day_rate | services \| contract rig | 3 | 1 | 5 | operational | Steel proxy commodity price | 0.122746 | 0.323866 | 0.119101 | positive |
| active_day_rate | services \| directional drilling surveys | 3 | 1 | 5 | operational | Brent oil price | -0.785638 | -0.559644 | 0.460426 | negative |
| active_day_rate | services \| directional drilling surveys | 3 | 1 | 5 | operational | Indonesia CPI index | -0.380345 | n/a | 0.222903 | negative |
| active_day_rate | services \| directional drilling surveys | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.540344 | -0.276962 | 0.316671 | negative |
| active_day_rate | services \| drilling safety health environment | 3 | 1 | 5 | operational | Brent oil price | -0.577098 | -0.338411 | 0.330001 | negative |
| active_day_rate | services \| drilling safety health environment | 3 | 1 | 5 | operational | Indonesia CPI index | -0.688062 | n/a | 0.393454 | negative |
| active_day_rate | services \| drilling safety health environment | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.483614 | -0.249635 | 0.276545 | negative |
| active_day_rate | services \| equipment rental | 2 | 1 | 4 | operational | Brent oil price | -0.190895 | -0.077871 | 0.520708 | negative |
| active_day_rate | services \| equipment rental | 2 | 1 | 4 | operational | Indonesia CPI index | 0.032329 | n/a | 0.088185 | flat |
| active_day_rate | services \| equipment rental | 2 | 1 | 4 | operational | Steel proxy commodity price | 0.143382 | 0.414818 | 0.391107 | positive |
| active_day_rate | services \| land transportation | 3 | 1 | 5 | operational | Brent oil price | -0.537350 | -0.689081 | 0.386132 | negative |
| active_day_rate | services \| land transportation | 3 | 1 | 5 | operational | Indonesia CPI index | 0.408806 | n/a | 0.293762 | positive |
| active_day_rate | services \| land transportation | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.445466 | -0.470434 | 0.320106 | negative |
| active_day_rate | services \| mud chemical and engineering service | 3 | 1 | 5 | operational | Brent oil price | -0.727413 | -0.498689 | 0.409899 | negative |
| active_day_rate | services \| mud chemical and engineering service | 3 | 1 | 5 | operational | Indonesia CPI index | -0.465180 | n/a | 0.262130 | negative |
| active_day_rate | services \| mud chemical and engineering service | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.582021 | -0.310310 | 0.327971 | negative |
| active_day_rate | services \| mud logging service | 3 | 1 | 5 | operational | Brent oil price | -0.111346 | -0.444995 | 0.076369 | negative |
| active_day_rate | services \| mud logging service | 3 | 1 | 5 | operational | Indonesia CPI index | 0.905747 | n/a | 0.621230 | positive |
| active_day_rate | services \| mud logging service | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.440898 | -0.648376 | 0.302401 | negative |
| active_day_rate | services \| open hole electrical logging service | 3 | 1 | 5 | operational | Brent oil price | -0.381574 | -0.463613 | 0.313694 | negative |
| active_day_rate | services \| open hole electrical logging service | 3 | 1 | 5 | operational | Indonesia CPI index | 0.189548 | n/a | 0.155828 | positive |
| active_day_rate | services \| open hole electrical logging service | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.645268 | -0.616709 | 0.530478 | negative |
| active_day_rate | services \| other transportation | 3 | 1 | 4 | operational | Brent oil price | 0.526081 | 0.654957 | 0.270871 | positive |
| active_day_rate | services \| other transportation | 3 | 1 | 4 | operational | Indonesia CPI index | -0.773443 | n/a | 0.398234 | negative |
| active_day_rate | services \| other transportation | 3 | 1 | 4 | operational | Steel proxy commodity price | 0.642659 | 0.712094 | 0.330895 | positive |
| active_day_rate | services \| service lines communication | 3 | 1 | 5 | operational | Brent oil price | -0.845036 | -0.670167 | 0.550845 | negative |
| active_day_rate | services \| service lines communication | 3 | 1 | 5 | operational | Indonesia CPI index | -0.212501 | n/a | 0.138521 | negative |
| active_day_rate | services \| service lines communication | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.476535 | -0.234849 | 0.310634 | negative |
| active_day_rate | services \| supervision | 3 | 1 | 5 | operational | Brent oil price | -0.802588 | -0.358257 | 0.481524 | negative |
| active_day_rate | services \| supervision | 3 | 1 | 5 | operational | Indonesia CPI index | -0.580508 | n/a | 0.348284 | negative |
| active_day_rate | services \| supervision | 3 | 1 | 5 | operational | Steel proxy commodity price | 0.283671 | 0.455129 | 0.170192 | positive |
| campaign_scope_benchmark | construction | 3 | 1 | 5 | operational | Brent oil price | -0.223349 | -0.126453 | 0.173314 | negative |
| campaign_scope_benchmark | construction | 3 | 1 | 5 | operational | Indonesia CPI index | -0.346945 | n/a | 0.269221 | negative |
| campaign_scope_benchmark | construction | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.718403 | -0.531882 | 0.557465 | negative |
| campaign_scope_benchmark | construction \| installation hook up pre commisioning | 3 | 1 | 5 | operational | Brent oil price | -0.332847 | -0.133530 | 0.214921 | negative |
| campaign_scope_benchmark | construction \| installation hook up pre commisioning | 3 | 1 | 5 | operational | Indonesia CPI index | -0.661220 | n/a | 0.426953 | negative |
| campaign_scope_benchmark | construction \| installation hook up pre commisioning | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.554626 | -0.327515 | 0.358125 | negative |
| campaign_scope_benchmark | drill cutting \| drill cutting transport process | 3 | 1 | 4 | operational | Brent oil price | 0.578107 | 0.496510 | 0.277946 | positive |
| campaign_scope_benchmark | drill cutting \| drill cutting transport process | 3 | 1 | 4 | operational | Indonesia CPI index | 0.646536 | n/a | 0.310845 | positive |
| campaign_scope_benchmark | drill cutting \| drill cutting transport process | 3 | 1 | 4 | operational | Steel proxy commodity price | -0.855286 | -0.748865 | 0.411209 | negative |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 5 | operational | Brent oil price | -0.329202 | -0.133978 | 0.210731 | negative |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 5 | operational | Indonesia CPI index | -0.598334 | n/a | 0.383010 | negative |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.634654 | -0.407408 | 0.406259 | negative |
| campaign_scope_benchmark | engineering | 3 | 1 | 4 | operational | Brent oil price | -0.508380 | -0.663279 | 0.248973 | negative |
| campaign_scope_benchmark | engineering | 3 | 1 | 4 | operational | Indonesia CPI index | 0.832472 | n/a | 0.407692 | positive |
| campaign_scope_benchmark | engineering | 3 | 1 | 4 | operational | Steel proxy commodity price | -0.701060 | -0.723252 | 0.343335 | negative |
| campaign_scope_benchmark | explosive | 3 | 1 | 4 | operational | Brent oil price | -0.172238 | -0.003658 | 0.229773 | negative |
| campaign_scope_benchmark | explosive | 3 | 1 | 4 | operational | Indonesia CPI index | -0.303697 | n/a | 0.405145 | negative |
| campaign_scope_benchmark | explosive | 3 | 1 | 4 | operational | Steel proxy commodity price | 0.273665 | 0.402269 | 0.365082 | positive |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 4 | operational | Brent oil price | 0.974152 | 0.991855 | 0.686289 | positive |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 4 | operational | Indonesia CPI index | -0.408787 | n/a | 0.287990 | negative |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 4 | operational | Steel proxy commodity price | 0.036510 | 0.106699 | 0.025721 | flat |
| campaign_scope_benchmark | interpad move \| rig move | 3 | 1 | 5 | operational | Brent oil price | 0.035342 | 0.172308 | 0.024579 | flat |
| campaign_scope_benchmark | interpad move \| rig move | 3 | 1 | 5 | operational | Indonesia CPI index | -0.460891 | n/a | 0.320536 | negative |
| campaign_scope_benchmark | interpad move \| rig move | 3 | 1 | 5 | operational | Steel proxy commodity price | 0.941641 | 0.974536 | 0.654885 | positive |
| campaign_scope_benchmark | lih | 3 | 1 | 4 | operational | Brent oil price | -0.416278 | -0.178809 | 0.192924 | negative |
| campaign_scope_benchmark | lih | 3 | 1 | 4 | operational | Indonesia CPI index | -0.783703 | n/a | 0.363207 | negative |
| campaign_scope_benchmark | lih | 3 | 1 | 4 | operational | Steel proxy commodity price | 0.957752 | 0.941996 | 0.443869 | positive |
| campaign_scope_benchmark | pgpa | 3 | 1 | 5 | operational | Brent oil price | -0.533897 | -0.349454 | 0.307994 | negative |
| campaign_scope_benchmark | pgpa | 3 | 1 | 5 | operational | Indonesia CPI index | -0.540803 | n/a | 0.311978 | negative |
| campaign_scope_benchmark | pgpa | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.658765 | -0.450284 | 0.380028 | negative |
| campaign_scope_benchmark | procurement \| material ll | 3 | 1 | 5 | operational | Brent oil price | -0.659223 | -0.467059 | 0.368741 | negative |
| campaign_scope_benchmark | procurement \| material ll | 3 | 1 | 5 | operational | Indonesia CPI index | -0.517402 | n/a | 0.289413 | negative |
| campaign_scope_benchmark | procurement \| material ll | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.611140 | -0.407263 | 0.341846 | negative |
| campaign_scope_benchmark | procurement \| material non ll | 3 | 1 | 5 | operational | Brent oil price | -0.034961 | 0.008385 | 0.031851 | flat |
| campaign_scope_benchmark | procurement \| material non ll | 3 | 1 | 5 | operational | Indonesia CPI index | -0.167761 | n/a | 0.152836 | negative |
| campaign_scope_benchmark | procurement \| material non ll | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.894930 | -0.728383 | 0.815312 | negative |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 5 | operational | Brent oil price | 0.055965 | 0.015473 | 0.063921 | positive |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 5 | operational | Indonesia CPI index | 0.137047 | n/a | 0.156530 | positive |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 5 | operational | Steel proxy commodity price | -0.682519 | -0.555884 | 0.779549 | negative |
| campaign_scope_benchmark | security | 3 | 1 | 4 | operational | Brent oil price | -0.320135 | -0.070638 | 0.158307 | negative |
| campaign_scope_benchmark | security | 3 | 1 | 4 | operational | Indonesia CPI index | -0.765715 | n/a | 0.378647 | negative |
| campaign_scope_benchmark | security | 3 | 1 | 4 | operational | Steel proxy commodity price | 0.936391 | 0.940088 | 0.463046 | positive |
| campaign_scope_benchmark | well insurance \| insurance | 3 | 1 | 5 | operational | Brent oil price | 0.522457 | 0.667256 | 0.295886 | positive |
| campaign_scope_benchmark | well insurance \| insurance | 3 | 1 | 5 | operational | Indonesia CPI index | -0.693515 | n/a | 0.392762 | negative |
| campaign_scope_benchmark | well insurance \| insurance | 3 | 1 | 5 | operational | Steel proxy commodity price | 0.549767 | 0.661639 | 0.311352 | positive |
| campaign_scope_benchmark | well testing | 2 | 1 | 5 | operational | Brent oil price | 0.350712 | 0.182708 | 0.240651 | positive |
| campaign_scope_benchmark | well testing | 2 | 1 | 5 | operational | Indonesia CPI index | 0.845816 | n/a | 0.580380 | positive |
| campaign_scope_benchmark | well testing | 2 | 1 | 5 | operational | Steel proxy commodity price | -0.260821 | -0.408586 | 0.178969 | negative |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 5 | operational | Brent oil price | -0.640794 | -0.680960 | 0.380085 | negative |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 5 | operational | Indonesia CPI index | 0.222904 | n/a | 0.132215 | positive |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.822225 | -0.716712 | 0.487700 | negative |
| depth_rate | material ll \| casing | 3 | 1 | 5 | operational | Brent oil price | -0.552856 | -0.922338 | 0.376286 | negative |
| depth_rate | material ll \| casing | 3 | 1 | 5 | operational | Indonesia CPI index | 0.708035 | n/a | 0.481904 | positive |
| depth_rate | material ll \| casing | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.208353 | -0.252517 | 0.141810 | negative |
| depth_rate | material ll \| fuel lubricants | 3 | 1 | 5 | operational | Brent oil price | 0.616243 | 0.659295 | 0.506765 | positive |
| depth_rate | material ll \| fuel lubricants | 3 | 1 | 5 | operational | Indonesia CPI index | -0.259205 | n/a | 0.213156 | negative |
| depth_rate | material ll \| fuel lubricants | 3 | 1 | 5 | operational | Steel proxy commodity price | -0.340585 | -0.212243 | 0.280079 | negative |
| depth_rate | material ll \| well equipment surface | 3 | 1 | 4 | operational | Brent oil price | -0.411940 | -0.504892 | 0.292595 | negative |
| depth_rate | material ll \| well equipment surface | 3 | 1 | 4 | operational | Indonesia CPI index | 0.424418 | n/a | 0.301458 | positive |
| depth_rate | material ll \| well equipment surface | 3 | 1 | 4 | operational | Steel proxy commodity price | 0.571525 | 0.614509 | 0.405947 | positive |

## Cluster Coverage
| pricing_basis | wbs_cluster | field_coverage_count | field_count_floor | field_count_peak | overlap_year_count | support_status | observation_years |
|---|---|---:|---:|---:|---:|---|---|
| active_day_rate | services \| bits reamer and core heads | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| casing installation | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| cement cementing pump fees | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| contract rig | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| directional drilling surveys | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| drilling safety health environment | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| land transportation | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| mud chemical and engineering service | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| mud logging service | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| open hole electrical logging service | 3 | 1 | 1 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| service lines communication | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| supervision | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | construction | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | construction \| installation hook up pre commisioning | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | drilling operation water support | 3 | 1 | 1 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | interpad move \| rig move | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | pgpa | 3 | 1 | 1 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | procurement \| material ll | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | procurement \| material non ll | 3 | 1 | 1 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | rig mobilization | 2 | 1 | 1 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | well insurance \| insurance | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | well testing | 2 | 1 | 1 | 5 | operational | 2019,2021,2022,2024,2025 |
| campaign_scope_benchmark | wellsite geologist wsg | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| depth_rate | material ll \| casing | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| depth_rate | material ll \| fuel lubricants | 3 | 1 | 2 | 5 | operational | 2019,2021,2022,2024,2025 |
| active_day_rate | services \| equipment rental | 2 | 1 | 1 | 4 | operational | 2021,2022,2024,2025 |
| active_day_rate | services \| other transportation | 3 | 1 | 2 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | drill cutting \| drill cutting transport process | 3 | 1 | 2 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | engineering | 3 | 1 | 1 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | explosive | 3 | 1 | 1 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | hazardous waste | 3 | 1 | 2 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | lih | 3 | 1 | 2 | 4 | operational | 2021,2022,2024,2025 |
| campaign_scope_benchmark | security | 3 | 1 | 1 | 4 | operational | 2021,2022,2024,2025 |
| depth_rate | material ll \| well equipment surface | 3 | 1 | 2 | 4 | operational | 2019,2021,2022,2025 |
| active_day_rate | services \| api non api machine shop service | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| active_day_rate | services \| coring | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| active_day_rate | services \| explosive handling permitting | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| active_day_rate | services \| ndt inspection | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| active_day_rate | services \| rig inspection | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| active_day_rate | services \| vehicle inspection | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| active_day_rate | services \| welding service | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| campaign_scope_benchmark | internet and it support service | 3 | 1 | 2 | 3 | diagnostic_only_thin_history | 2021,2022,2025 |
| campaign_scope_benchmark | project management cost | 3 | 1 | 2 | 3 | diagnostic_only_thin_history | 2021,2022,2025 |
| campaign_scope_benchmark | she permit \| environment permit | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2021,2022,2024 |
| depth_rate | material ll \| asset transfer | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| depth_rate | material ll \| equipment rental | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2019,2021,2024 |
| depth_rate | material non ll \| consumables | 2 | 1 | 1 | 3 | diagnostic_only_thin_history | 2022,2024,2025 |
| active_day_rate | services \| others | 3 | 1 | 2 | 2 | insufficient_history | 2019,2021 |
| campaign_scope_benchmark | conductor casing installation material \| material | 2 | 1 | 1 | 2 | insufficient_history | 2024,2025 |
| campaign_scope_benchmark | conductor casing installation material \| service | 2 | 1 | 1 | 2 | insufficient_history | 2024,2025 |
| campaign_scope_benchmark | drill cutting \| heavy equipment for drill cutting | 1 | 1 | 1 | 2 | insufficient_history | 2022,2024 |
| campaign_scope_benchmark | drilling facilities support | 2 | 1 | 1 | 2 | insufficient_history | 2022,2025 |
| campaign_scope_benchmark | drilling facilities support \| hardware supply | 2 | 1 | 1 | 2 | insufficient_history | 2021,2024 |
| campaign_scope_benchmark | drilling operation water support \| drilling facilities support | 2 | 1 | 1 | 2 | insufficient_history | 2021,2024 |
| campaign_scope_benchmark | environmental monitoring | 1 | 1 | 1 | 2 | insufficient_history | 2022,2024 |
| campaign_scope_benchmark | environmental monitoring \| sampling and lab analysis | 2 | 1 | 2 | 2 | insufficient_history | 2021,2025 |
| campaign_scope_benchmark | hardware supply | 2 | 1 | 1 | 2 | insufficient_history | 2022,2025 |
| campaign_scope_benchmark | rig skid | 3 | 1 | 2 | 2 | insufficient_history | 2021,2024 |
| campaign_scope_benchmark | services \| service | 1 | 1 | 1 | 2 | insufficient_history | 2019,2022 |
| campaign_scope_benchmark | skid moving \| rig skid | 2 | 1 | 1 | 2 | insufficient_history | 2022,2025 |
| depth_rate | material ll \| casing repair modif | 2 | 1 | 1 | 2 | insufficient_history | 2024,2025 |
| active_day_rate | services \| drilling rig o m | 1 | 1 | 1 | 1 | insufficient_history | 2025 |
| campaign_scope_benchmark | conductor casing installation material \| others | 1 | 1 | 1 | 1 | insufficient_history | 2021 |
| campaign_scope_benchmark | construction \| new rig pavement | 1 | 1 | 1 | 1 | insufficient_history | 2025 |
| campaign_scope_benchmark | contingency | 1 | 1 | 1 | 1 | insufficient_history | 2025 |
| campaign_scope_benchmark | drilling facilities support \| other | 1 | 1 | 1 | 1 | insufficient_history | 2021 |
| campaign_scope_benchmark | environmental monitoring \| ipal | 1 | 1 | 1 | 1 | insufficient_history | 2022 |
| campaign_scope_benchmark | hardware supply \| permitting | 1 | 1 | 1 | 1 | insufficient_history | 2024 |
| campaign_scope_benchmark | logging cost | 1 | 1 | 1 | 1 | insufficient_history | 2025 |
| campaign_scope_benchmark | material | 1 | 1 | 1 | 1 | insufficient_history | 2022 |
| campaign_scope_benchmark | pgpa security | 1 | 1 | 1 | 1 | insufficient_history | 2021 |
| campaign_scope_benchmark | pgpa security \| other | 1 | 1 | 1 | 1 | insufficient_history | 2021 |
| campaign_scope_benchmark | service | 1 | 1 | 1 | 1 | insufficient_history | 2021 |
| campaign_scope_benchmark | services \| rig move | 1 | 1 | 1 | 1 | insufficient_history | 2025 |
| campaign_scope_benchmark | she permit \| andalalin | 1 | 1 | 1 | 1 | insufficient_history | 2022 |
| campaign_scope_benchmark | she permit \| others | 1 | 1 | 1 | 1 | insufficient_history | 2021 |
| campaign_scope_benchmark | skid moving \| rig move | 1 | 1 | 1 | 1 | insufficient_history | 2025 |
| depth_rate | material ll \| others | 1 | 1 | 1 | 1 | insufficient_history | 2021 |
| per_well_job | conductor casing installation material \| service | 1 | 1 | 1 | 1 | insufficient_history | 2021 |
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
