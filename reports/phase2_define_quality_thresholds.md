# Phase 2 Define Quality Thresholds

## Gate Authority
- `docs/PROJECT_INSTRUCTION.md` is the authoritative Phase 2 gate reference.
- Gate recommendation: **READY FOR PHASE 3 DESIGN**.
- Material review flags are informational only when unresolved keys remain at zero.

## Threshold Results
| check | threshold | observed | status | notes |
|---|---|---|---|---|
| Hierarchy completeness | 0 rows with blank `wbs_lvl1..wbs_lvl5` | 0 / 848 blank | PASS | Required for L1->L5 auditability. |
| Campaign mapping completeness | 0 rows with blank campaign mapping fields | 0 / 848 blank | PASS | Requires both `campaign_code` and `campaign_canonical`. |
| In-scope campaign alias mapping | All in-scope labels mapped | 646 / 646 mapped | PASS | Checks dashboard campaign aliases for current in-scope campaigns. |
| Duplicate classification keys | 0 duplicate `classification_key` values | 0 | PASS | Classification grain is the implemented Lv5 canonical key. |
| Duplicate campaign master codes | 0 duplicate `campaign_code` values | 0 | PASS | Campaign master must remain one row per canonical campaign code. |
| Duplicate well master keys | 0 duplicate (`well_id`, `campaign_code`) pairs | 0 | PASS | Well master is one row per canonical well within a campaign. |
| Well attribution coverage | Report coverage; not a Phase 2 blocker at campaign/WBS grain | 681 / 848 (80.31%) | KNOWN LIMITATION | Structured.Cost contains mixed well/general rows; deterministic attribution is reported, not forced. |
| Event-code coverage | Report coverage; not a Phase 2 blocker at campaign/WBS grain | 0 / 848 (0.00%) | KNOWN LIMITATION | Event-code family is defined, but row-addressable values are not present in the current Lv5 build. |

## Null Coverage Snapshot
| field | blank_rows | blank_pct |
|---|---:|---:|
| wbs_lvl1 | 0 | 0.00% |
| wbs_lvl2 | 0 | 0.00% |
| wbs_lvl3 | 0 | 0.00% |
| wbs_lvl4 | 0 | 0.00% |
| wbs_lvl5 | 0 | 0.00% |
| campaign_code | 0 | 0.00% |
| campaign_canonical | 0 | 0.00% |
| cost_actual | 0 | 0.00% |
| well_canonical | 167 | 19.69% |
| event_code_raw | 848 | 100.00% |

## Current Grain Limitation
- `wbs_lv5_master.csv` is complete for hierarchy and campaign mapping, with deterministic well-attribution capture where auditable from `Well Name` and label aliases.
- `event_code_raw` and `event_code_desc` remain blank in this Define layer because NPT context is bridged separately and not asserted as row-level Lv5 attribution.
- These limitations do not block Phase 3 design, but they do constrain later well-level driver validation until a richer source grain is introduced.
