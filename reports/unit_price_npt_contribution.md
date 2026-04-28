# NPT Contribution Analysis

Field-level statistical support for what contributes most toward NPT, plus penalty references tied to the standard-well service-day benchmark.

## Coverage
- NPT event rows analyzed after active pool exclusions: **373**.
- Unresolved event rows with no field attribution kept out of contribution stats: **17**.
- Event context is strongest for **DARAJAT** and **SALAK** with direct context linkage.
- **WAYANG_WINDU** is currently supported at field level through well-name-prefix mapping, but campaign-specific WW attribution is not yet available in the local event context.

## Mapping Support
- `field_inferred_from_name_prefix`: **69** rows
- `source_full`: **332** rows

## Top Major Contributors
| field | major category | total NPT days | share of field NPT % | impacted wells | R^2 vs total field-well NPT |
|---|---|---:|---:|---:|---:|
| DARAJAT | WO | 14.374997 | 19.228449 | 5 | 0.532040 |
| DARAJAT | SP | 12.770822 | 17.082654 | 4 | 0.345079 |
| DARAJAT | EQP | 11.895844 | 15.912255 | 7 | 0.269687 |
| DARAJAT | SPWS | 9.250000 | 12.373091 | 1 | 0.060284 |
| DARAJAT | RREQ | 8.301386 | 11.104195 | 13 | 0.006403 |
| SALAK | WO | 15.218752 | 53.127280 | 4 | 0.985539 |
| SALAK | FSH | 5.125000 | 17.890909 | 1 | 0.980228 |
| SALAK | EQPS | 4.270833 | 14.909090 | 8 | 0.003956 |
| SALAK | RREQ | 2.645831 | 9.236356 | 10 | 0.003035 |
| SALAK | WP | 0.791667 | 2.763638 | 1 | 0.000547 |
| WAYANG_WINDU | SP | 29.916666 | 57.670683 | 3 | 0.984472 |
| WAYANG_WINDU | RREQ | 6.354167 | 12.248997 | 9 | 0.105445 |
| WAYANG_WINDU | WP | 6.062500 | 11.686747 | 4 | 0.931409 |
| WAYANG_WINDU | SCL | 2.083333 | 4.016064 | 2 | 0.007113 |
| WAYANG_WINDU | EQP | 1.729168 | 3.333336 | 5 | 0.010197 |

## Penalty Reference
| field | rank | major category | top detail | penalty p50 (USD) | penalty as % of median direct well cost |
|---|---:|---|---|---:|---:|
| DARAJAT | 1 | WO | ORDERS | 122586.470957 | 2.686533 |
| DARAJAT | 2 | SP | STUCK | 337765.059929 | 7.402262 |
| DARAJAT | 3 | EQP | BHA | 156493.473728 | 3.429620 |
| DARAJAT | 4 | SPWS | HOLE CLEAN | 1158051.705583 | 25.379185 |
| DARAJAT | 5 | RREQ | TOP DRIVE | 54772.715805 | 1.200367 |
| SALAK | 1 | WO | REG PERMIT | 105303.940018 | 3.303834 |
| SALAK | 2 | FSH | FSH ALL OH | 790984.354351 | 24.816551 |
| SALAK | 3 | EQPS | CIRSYS | 45015.266868 | 1.412321 |
| SALAK | 4 | RREQ | TOP DRIVE | 44211.395256 | 1.387100 |
| SALAK | 5 | WP | JUNK | 122184.626508 | 3.833453 |
| WAYANG_WINDU | 1 | SP | STUCK | 725456.976280 | 18.005719 |
| WAYANG_WINDU | 2 | RREQ | TOP DRIVE | 45028.369014 | 1.117596 |
| WAYANG_WINDU | 3 | WP | TIGHT HOLE | 26266.548591 | 0.651931 |
| WAYANG_WINDU | 4 | SCL | GEOMETRY | 125078.782803 | 3.104434 |
| WAYANG_WINDU | 5 | EQP | CSG LN | 12507.920307 | 0.310444 |

## Interpretation
- Contribution rank is driven first by total NPT days and then supported with a per-well correlation/R^2 against total well NPT, so dominant categories are both frequent and explanatory rather than just one-off long events.
- Penalty references multiply field median active-day service rate by the median/p90 impacted-well NPT days for each category. They are intended as category-specific add-ons, not as the base direct well estimate.
- WW penalty support is field-level only at this stage; campaign-level WW penalty attribution should stay flagged as not yet supported.
