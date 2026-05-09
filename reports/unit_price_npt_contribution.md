# NPT Contribution Analysis

Field-level statistical support for what contributes most toward NPT, plus penalty references tied to the standard-well service-day benchmark.

## Coverage
- NPT event rows analyzed after active pool exclusions: **341**.
- Unresolved event rows with no field attribution kept out of contribution stats: **49**.
- Event context is strongest for **DARAJAT** and **SALAK** with direct context linkage.
- **WAYANG_WINDU** is currently supported at field level through well-name-prefix mapping, but campaign-specific WW attribution is not yet available in the local event context.

## Mapping Support
- `field_campaign_imputed_from_unique_context`: **13** rows
- `field_inferred_from_name_prefix`: **69** rows
- `source_full`: **319** rows

## Top Major Contributors
| field | major category | total NPT days | share of field NPT % | impacted wells | R^2 vs total field-well NPT |
|---|---|---:|---:|---:|---:|
| DARAJAT | WO | 14.374997 | 20.928542 | 5 | 0.601971 |
| DARAJAT | SP | 12.770822 | 18.593025 | 4 | 0.234008 |
| DARAJAT | EQP | 10.052094 | 14.634832 | 7 | 0.218583 |
| DARAJAT | SPWS | 9.250000 | 13.467065 | 1 | 0.078355 |
| DARAJAT | RREQ | 8.259719 | 12.025316 | 13 | 0.016378 |
| SALAK | WO | 15.218752 | 53.127280 | 4 | 0.985539 |
| SALAK | FSH | 5.125000 | 17.890909 | 1 | 0.980228 |
| SALAK | EQPS | 4.270833 | 14.909090 | 8 | 0.003956 |
| SALAK | RREQ | 2.645831 | 9.236356 | 10 | 0.003035 |
| SALAK | WP | 0.791667 | 2.763638 | 1 | 0.000547 |
| WAYANG_WINDU | SP | 10.166666 | 35.790246 | 3 | 0.705552 |
| WAYANG_WINDU | WP | 5.708333 | 20.095343 | 4 | 0.302131 |
| WAYANG_WINDU | RREQ | 5.229167 | 18.408510 | 9 | 0.000009 |
| WAYANG_WINDU | SCL | 2.083333 | 7.334066 | 2 | 0.005132 |
| WAYANG_WINDU | EQP | 1.625001 | 5.720576 | 4 | 0.260142 |

## Penalty Reference
| field | rank | major category | top detail | penalty p50 (USD) | penalty as % of median direct well cost |
|---|---:|---|---|---:|---:|
| DARAJAT | 1 | WO | ORDERS | 122586.470957 | 2.686533 |
| DARAJAT | 2 | SP | STUCK | 337765.059929 | 7.402262 |
| DARAJAT | 3 | EQP | BHA | 125194.778982 | 2.743696 |
| DARAJAT | 4 | SPWS | HOLE CLEAN | 1158051.705583 | 25.379185 |
| DARAJAT | 5 | RREQ | TOP DRIVE | 54772.715805 | 1.200367 |
| SALAK | 1 | WO | REG PERMIT | 105303.940018 | 3.303834 |
| SALAK | 2 | FSH | FSH ALL OH | 790984.354351 | 24.816551 |
| SALAK | 3 | EQPS | CIRSYS | 45015.266868 | 1.412321 |
| SALAK | 4 | RREQ | TOP DRIVE | 44211.395256 | 1.387100 |
| SALAK | 5 | WP | JUNK | 122184.626508 | 3.833453 |
| WAYANG_WINDU | 1 | SP | HOLE CLEAN | 262665.485913 | 6.519313 |
| WAYANG_WINDU | 2 | WP | TIGHT HOLE | 26266.548591 | 0.651931 |
| WAYANG_WINDU | 3 | RREQ | TOP DRIVE | 27517.376645 | 0.682977 |
| WAYANG_WINDU | 4 | SCL | GEOMETRY | 125078.782803 | 3.104434 |
| WAYANG_WINDU | 5 | EQP | CSG LN | 39399.882925 | 0.977898 |

## Interpretation
- Contribution rank is driven first by total NPT days and then supported with a per-well correlation/R^2 against total well NPT, so dominant categories are both frequent and explanatory rather than just one-off long events.
- Penalty references multiply field median active-day service rate by the median/p90 impacted-well NPT days for each category. They are intended as category-specific add-ons, not as the base direct well estimate.
- WW penalty support is field-level only at this stage; campaign-level WW penalty attribution should stay flagged as not yet supported.
