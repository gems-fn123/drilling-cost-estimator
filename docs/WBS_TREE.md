# WBS Level Structure Reference

Use this structure for app navigation, aggregation, and estimation rollups.

## Level Semantics
- **Level 1:** Major campaign phase.
- **Level 2:** Functional domain under the phase.
- **Level 3:** Work package group.
- **Level 4:** Executable activity block.
- **Level 5:** Atomic estimate item (target estimation grain).

## Required Hierarchy Rules
1. Every Level-5 node must have exactly one Level-4 parent.
2. Every Level-4 node must have exactly one Level-3 parent.
3. Cost rollups must be additive upward (L5 -> L1).
4. Dictionary labels and WBS codes must be canonicalized before aggregation.

## Minimum Fields Per Node
- `wbs_code`
- `level`
- `label`
- `parent_wbs_code`
- `is_leaf`
- `cost_actual` (historical)
- `cost_estimate` (model output)
- `confidence_low` / `confidence_high`
