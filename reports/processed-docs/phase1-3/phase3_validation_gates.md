# Phase 3 Validation Gate Specification

## Purpose
Define pass/fail controls required before Phase 4 implementation work.

## Baseline Snapshot (2026-04-02)
Observed from current canonical contracts:
- Total Lv.5 rows: **822**
- Field split: **DARAJAT 462**, **SALAK 360**
- Classification keys: **822 unique / 0 duplicates**
- Hierarchy blanks (`wbs_lvl1..wbs_lvl5`): **0**
- Campaign mapping blanks (`campaign_code` or `campaign_canonical`): **0**
- Known limitations: `well_canonical` blank **822/822**; `event_code_raw` blank **822/822**

## Gate Table
| gate_id | gate | threshold | observed | status | fail action |
|---|---|---:|---:|---|---|
| G1 | Hierarchy completeness (`wbs_lvl1..wbs_lvl5`) | 0 blank rows | 0 | PASS | Stop run; publish orphan/hierarchy defect list. |
| G2 | Campaign mapping completeness | 0 blank rows | 0 | PASS | Stop run; publish unmapped campaign rows. |
| G3 | Field membership validity | 100% in {DARAJAT,SALAK} | 822/822 | PASS | Stop run; quarantine invalid-field rows. |
| G4 | Classification key uniqueness | 0 duplicates | 0 | PASS | Stop run; publish duplicate key report. |
| G5 | Classification label validity | 100% in {well_tied,campaign_tied,hybrid} | 822/822 | PASS | Stop run; publish invalid classification labels. |
| G6 | Field-specific class coverage reported | mandatory report, not pass/fail blocker | Reported | PASS | Block phase exit if not published. |
| G7 | Well attribution coverage disclosure | mandatory disclosure if <100% | 0/822 populated | KNOWN LIMITATION | Continue with campaign/WBS-grain design only. |
| G8 | Event-code coverage disclosure | mandatory disclosure if <100% | 0/822 populated | KNOWN LIMITATION | Continue with campaign/WBS-grain design only. |

## Field-Specific Coverage (Reference)
| field | well_tied | campaign_tied | hybrid | total |
|---|---:|---:|---:|---:|
| DARAJAT | 352 | 32 | 78 | 462 |
| SALAK | 299 | 14 | 47 | 360 |

## Gate Ownership
| gate group | owner | cadence | output |
|---|---|---|---|
| Contract integrity (G1-G5) | Data engineering lead | each run | gate report snapshot |
| Coverage disclosures (G6-G8) | Analytics lead | each run | limitation + sufficiency section |
| Phase transition approval | Project lead | phase exit | phase exit memo |

## Enforcement Rule
A Phase 4 start recommendation is valid only if:
1. G1-G5 are PASS,
2. G6 report exists,
3. G7-G8 are explicitly carried in assumptions/limitations.
