# Phase 4 Gate Preflight Report

Generated at: 2026-05-10T01:13:07.421499+00:00

## Runtime Toggles
- group_by: `family`
- use_synthetic: `False`
- synthetic_policy: `not_applied`

## Snapshot
- `wbs_lv5_master.csv` rows: **848**
- `wbs_lv5_classification.csv` rows: **144**
- Gate recommendation (G1-G6): **PASS**

## Gate Results
| gate_id | gate | threshold | observed | status |
|---|---|---:|---:|---|
| G1 | Hierarchy completeness (wbs_lvl1..wbs_lvl5) | 0 blank rows | 0 | PASS |
| G2 | Campaign mapping completeness | 0 blank rows | 0 | PASS |
| G3 | Field membership validity | 100% in {DARAJAT,SALAK} | 848/848 | PASS |
| G4 | Classification key uniqueness | 0 duplicates | 0 | PASS |
| G5 | Classification label validity | 100% in {well_tied,campaign_tied,hybrid} | 144/144 | PASS |
| G6 | Field-specific class coverage reported | mandatory report | Reported | PASS |
| G7 | Well attribution coverage disclosure | mandatory disclosure if <100% | 681/848 populated | KNOWN LIMITATION |
| G8 | Event-code coverage disclosure | mandatory disclosure if <100% | 0/848 populated | KNOWN LIMITATION |

## Notes
- G7 and G8 are disclosure gates and remain non-blocking known limitations when coverage is incomplete.
- Baseline artifacts are generated only when G1-G6 pass.
