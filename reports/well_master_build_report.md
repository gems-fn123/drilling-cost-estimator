# Well Master Build Report

## Build outcome
- In-scope well master rows: **20**
- Alias lookup rows: **125**
- Alias catalog rows: **22**

## Required counts
- Reassigned history rows: **22**
- Unresolved rows: **32**
- Remaining exclusions: **39**

## Rules enforced
1. Campaign scope unchanged from current definition (3 in-scope, 2 legacy, others excluded).
2. `DRJ-Steam 1` kept in scope and excluded from well-level training.
3. `20-1` under DRJ 2023 treated as posting exception only.
4. History rows (`2. Drilling.Data.History`) are reassigned to campaign when canonical well maps to exactly one in-scope master well.
