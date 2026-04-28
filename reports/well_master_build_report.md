# Well Master Build Report

## Build outcome
- In-scope well master rows: **41**
- Alias lookup rows: **286**
- Alias catalog rows: **35**

## Required counts
- Reassigned history rows: **42**
- Unresolved rows: **12**
- Remaining exclusions: **19**

## Rules enforced
1. Campaign scope widened to all seven dashboard campaigns across DARAJAT, SALAK, and WAYANG_WINDU.
2. `DRJ-Steam 1` kept in scope and excluded from well-level training.
3. `20-1` under DRJ 2023 treated as posting exception only.
4. History rows (`2. Drilling.Data.History`) are reassigned to campaign when canonical well maps to exactly one in-scope master well.
5. Dashboard workbook aliases (`OH`, `RD`, SAP/Alt names, WW spacing variants) are normalized into canonical well names before estimator use.

## Exported contract
- `well_master.csv` now carries both estimator roster fields (`campaign_code`, `campaign_id`, training flags) and stable master keys (`well_id`, `well_name`, `well_aliases`).
- `status` is scoped to estimator roster membership (`in_scope_estimator`) rather than real-world well lifecycle.
- `region` and `operator` remain blank in this Define layer because the current source package does not provide a reliable authoritative value for every in-scope well.
