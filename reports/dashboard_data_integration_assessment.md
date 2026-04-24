# Dashboard Data Integration Assessment

Date: 2026-04-24

## Scope
- Compare `data/raw/20260422_Data for Dashboard.xlsx` to `20260327_WBS_Data.xlsx` sheet `Data.Summary`.
- Assess how the new workbook can be integrated into the current Streamlit app without breaking the existing auditable pipeline.

## Current Authoritative Raw Contract

The current pipeline is tightly coupled to `20260327_WBS_Data.xlsx` -> `Data.Summary`.

- `src/cleaning/build_wbs_lv5_classification.py`
- `src/cleaning/wbs_lv5_driver_alignment.py`
- `src/modeling/wbs_tree_diagram.py`

Those modules expect a `Data.Summary`-style table with these key fields:

- `Asset`
- `Campaign`
- `WBS_Level`
- `WBS_ID`
- `Description`
- `ACTUAL, USD`
- `L1`
- `L2`
- `L3`
- `L4`
- `L5`

Observed `Data.Summary` profile:

- Used range: `2426` rows x `19` columns
- Header row: row `10`
- Distinct campaigns present: `DRJ 2022`, `DRJ 2023`, `SLK 2025`
- Lv.5 (`WBS_Level = 05`) rows: `815`

Lv.5 campaign totals from `Data.Summary`:

| Asset | Campaign | Lv.5 rows | Actual USD |
| --- | --- | ---: | ---: |
| `DRJ` | `DRJ 2022` | 206 | 30,669,524.90 |
| `DRJ` | `DRJ 2023` | 249 | 37,367,109.64 |
| `SLK` | `SLK 2025` | 360 | 38,522,325.57 |

## New Workbook Structure

The new workbook is not a raw `Data.Summary` replacement. It is a dashboard-oriented workbook with multiple derived tables.

Most relevant sheets:

| Sheet | Grain | Notes |
| --- | --- | --- |
| `Structured.Cost` | `Asset + Campaign + Level 2..5 + Well` | Best fact-like dashboard sheet; label-based, not code-based |
| `Structured.Cost (2)` | Same as `Structured.Cost` | Duplicate of the same useful table with fewer trailing blank columns |
| `DashBoard.Tab.Template` | `Asset + Campaign + Well` | Presentation-layer benchmark table with repeated campaign-level metrics |
| `General.Camp.Data` | `Asset + Campaign + Well` | Well context: aliases, depth, drilling duration, NPT |
| `NPT.Data` | Event rows | Useful enrichment, not wired into current estimator |
| `Drill.Depth.Days` | Time/depth history | Useful enrichment, not wired into current estimator |
| `Phase.Summary` | Phase rows | Useful enrichment, not wired into current estimator |
| `Check.Total` | Campaign totals | Reconciliation sheet |

Observed `Structured.Cost` profile:

- Data rows: `1138`
- Useful columns: `Asset`, `Campaign`, `Level 2`, `Level 3`, `Level 4`, `Level 5`, `Well`, `Actual Cost USD`
- Campaigns present:
  - `DRJ - 2019`
  - `DRJ - 2022`
  - `DRJ - 2024`
  - `SLK - 2021`
  - `SLK - 2025`
  - `WW - 2018`
  - `WW - 2021`

`Structured.Cost` campaign totals:

| Asset | Campaign | Rows | General rows | Named-well rows | Actual USD |
| --- | --- | ---: | ---: | ---: | ---: |
| `Darajat` | `DRJ - 2019` | 91 | 13 | 78 | 42,003,384.16 |
| `Darajat` | `DRJ - 2022` | 166 | 36 | 130 | 30,669,524.90 |
| `Darajat` | `DRJ - 2024` | 195 | 60 | 135 | 37,367,109.64 |
| `Salak` | `SLK - 2021` | 111 | 25 | 86 | 28,051,247.74 |
| `Salak` | `SLK - 2025` | 285 | 33 | 252 | 38,522,325.57 |
| `Wayang Windu` | `WW - 2018` | 134 | 44 | 90 | 26,986,999.90 |
| `Wayang Windu` | `WW - 2021` | 156 | 21 | 135 | 27,074,998.19 |

## What Matches

For the three campaigns that the current app currently uses, the new workbook matches campaign totals exactly.

Comparison against current app mart (`data/processed/historical_cost_mart.csv`):

| Field | Canonical campaign | Current mart rows | New `Structured.Cost` rows | Current actual USD | New actual USD | Delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `DARAJAT` | `DARAJAT_2022` | 206 | 166 | 30,669,524.90 | 30,669,524.90 | 0.00 |
| `DARAJAT` | `DARAJAT_2023_2024` | 256 | 195 | 37,367,109.64 | 37,367,109.64 | 0.00 |
| `SALAK` | `SALAK_2025_2026` | 360 | 285 | 38,522,325.57 | 38,522,325.57 | 0.00 |

Interpretation:

- The new workbook is materially consistent with the current app totals.
- The new workbook is more aggregated than the current raw/canonical mart.
- The new workbook also carries extra historical campaigns not currently in the app mart.

## What Does Not Match

The new workbook cannot directly replace `Data.Summary`.

### 1. Missing code-level hierarchy required by the pipeline

`Structured.Cost` does **not** carry:

- `WBS_ID`
- `WBS_Level`
- `L1`
- raw WBS code chain used by the current estimator and WBS tree viewer

This breaks direct compatibility with:

- `src/cleaning/build_wbs_lv5_classification.py`
- `src/cleaning/wbs_lv5_driver_alignment.py`
- `src/modeling/wbs_tree_diagram.py`

### 2. Different label conventions

The new workbook uses presentation labels:

- `Darajat` instead of `DRJ` / `DARAJAT`
- `Salak` instead of `SLK` / `SALAK`
- `DRJ - 2024` instead of the current canonical mapping path that lands on `DARAJAT_2023_2024`
- `SLK - 2025` instead of `SALAK_2025_2026`

This needs an explicit alias layer before integration.

### 3. Dashboard sheets are partly presentation-layer outputs

`DashBoard.Tab.Template` is not a normalized fact table:

- one row per well
- campaign-level shared/support/surface metrics are repeated per well row
- suitable for UI benchmarks
- not suitable as a source of record for raw estimator ingestion

### 4. Current app scope is narrower than the new workbook

The current app mart only contains:

- `DARAJAT_2022`
- `DARAJAT_2023_2024`
- `SALAK_2025_2026`

The new workbook additionally includes:

- `DRJ - 2019`
- `SLK - 2021`
- `WW - 2018`
- `WW - 2021`

That means integration needs a scope decision:

- keep current estimator scope unchanged, or
- deliberately widen it and update gates, mapping, and reports

## Integration Recommendation

### Recommendation 1: Do not replace `Data.Summary` in the current raw pipeline

Keep `Data.Summary` as the authoritative raw ingestion source for:

- WBS code lineage
- Lv.5 auditability
- WBS tree generation
- current canonical campaign/well mapping workflow

Reason:

- the current estimator and audit outputs rely on code-level WBS lineage that the new workbook no longer exposes

### Recommendation 2: Treat the new workbook as a dashboard mart and enrichment source

Use the new workbook in a separate adapter layer, not as a raw-source swap.

Suggested outputs:

1. `dashboard_structured_cost_mart.csv`
   - Source: `Structured.Cost`
   - Purpose: normalized dashboard fact table for UI benchmarking

2. `dashboard_well_benchmarks.csv`
   - Source: `DashBoard.Tab.Template`
   - Purpose: campaign/well benchmark cards and quick summary tables

3. `dashboard_well_context.csv`
   - Source: `General.Camp.Data`
   - Purpose: well depth, duration, aliases, and campaign metadata

### Recommendation 3: Normalize labels before any join

Minimum alias rules needed:

- Asset:
  - `Darajat` -> `DARAJAT`
  - `Salak` -> `SALAK`
  - `Wayang Windu` -> `EXCLUDED` or separate scope

- Campaign:
  - `DRJ - 2022` -> `DARAJAT_2022`
  - `DRJ - 2024` -> `DARAJAT_2023_2024`
  - `SLK - 2025` -> `SALAK_2025_2026`
  - `DRJ - 2019` -> `DARAJAT_2019`
  - `SLK - 2021` -> `SALAK_2021`
  - `WW - 2018` / `WW - 2021` -> excluded from estimator unless project scope is widened

### Recommendation 4: Integrate by app surface, not all at once

Safest path for the current app:

1. **Calculator tab**
   - add historical benchmark cards from `DashBoard.Tab.Template`
   - show comparable campaign totals, well costs, and per-well benchmark ranges

2. **Detail tab**
   - add optional “historical structured cost” reference table from `Structured.Cost`
   - keep existing estimator audit rows as the primary output

3. **WBS Tree tab**
   - keep current `Data.Summary` / processed JSON path for now
   - only support the new workbook after a separate label-tree mode is built

4. **Estimator core**
   - only consume the new workbook after building a deterministic bridge from `Structured.Cost` labels to existing canonical campaign / well mappings
   - do not bypass `historical_cost_mart.csv` until lineage and reconciliation are preserved

## Practical Next Step

If this workbook is meant to inform the current app immediately, the lowest-risk implementation is:

1. Build a dashboard adapter from `Structured.Cost`, `DashBoard.Tab.Template`, and `General.Camp.Data`
2. Add a new read-only “Historical Dashboard Benchmarks” section in Streamlit
3. Keep the estimator engine and WBS tree on the existing canonical pipeline

If this workbook is meant to become a new core source, then a larger refactor is required:

1. define a new data contract
2. rebuild code-level WBS lineage or accept label-level lineage
3. update campaign alias logic
4. re-run reconciliation and field-specific validation

## Conclusion

The new workbook is a **good integration candidate as a dashboard mart and enrichment pack**, but it is **not a direct substitute for `Data.Summary`**.

Best fit with the current app:

- use it to enrich UI benchmarks and well context now
- keep `Data.Summary`-derived processed artifacts as the estimator’s authoritative backbone

## Local Data Context Addendum

This addendum repeats the assessment using the local workbook plus current processed artifacts:

- `data/raw/20260422_Data for Dashboard.xlsx`
- `data/processed/historical_cost_mart.csv`
- `data/processed/dashboard_rebuild_well_cost.csv`
- `data/processed/well_instance_context.csv`
- `data/processed/cost_mart_coverage_report.csv`

### Coverage Expansion Unlocked by the Workbook

For current in-scope fields only, the workbook expands DARAJAT/SALAK history from `3` campaigns to `5` campaigns.

| Field | Current estimator scope | Added by workbook | Added actual USD | Uplift vs current field scope |
| --- | --- | --- | ---: | ---: |
| `DARAJAT` | `DRJ - 2022`, `DRJ - 2024` | `DRJ - 2019` | 42,003,384.16 | 61.7% |
| `SALAK` | `SLK - 2025` | `SLK - 2021` | 28,051,247.74 | 72.8% |

Combined DARAJAT + SALAK historical cost rises from `106,558,960.11` to `176,613,591.96`, an increase of `65.7%`.

`Wayang Windu` is also present in the workbook but remains outside the current estimator scope and should stay excluded unless the project intentionally widens field scope.

### Where the Biggest Cost Chunk Lies

Across both the new workbook and the canonical mart, the largest cost block is still direct **well execution**.

| Field | Workbook `Structured.Cost` Level 3 `Well Cost` | Share of workbook field total | Current mart `well_tied` share |
| --- | ---: | ---: | ---: |
| `DARAJAT` | 72,245,593.49 | 65.65% | 73.49% |
| `SALAK` | 43,839,629.28 | 65.85% | 75.63% |

Largest non-well buckets in the workbook:

- `DARAJAT`: `Tie-in` 8.80%, `Rig Mobilization` 8.43%, `Rig Move` 4.10%
- `SALAK`: `Rig Mobilization` 6.85%, `Rig Move` 6.38%, `Tie-in` 5.84%

Inside `Well Cost`, the dominant sub-bucket is `Services`, not materials:

| Field | Services share of well cost | Material (`LL` + `Non LL`) share of well cost |
| --- | ---: | ---: |
| `DARAJAT` | 76.30% | 23.70% |
| `SALAK` | 75.38% | 24.62% |

Top `Well Cost` items from the workbook:

- `DARAJAT`: `Contract Rig` 21.17%, `Cement, Cementing & Pump Fees` 11.85%, `Equipment Rental` 11.77%, `Mud, Chemical and Engineering Service` 10.40%, `Casing` 10.07%, `Directional Drilling & Surveys` 9.04%, `Fuel & Lubricants` 8.29%
- `SALAK`: `Casing` 15.93%, `Cement, Cementing & Pump Fees` 13.40%, `Contract Rig` 13.16%, `Mud, Chemical and Engineering Service` 8.61%, `Directional Drilling & Surveys` 8.42%, `Equipment Rental` 8.25%, `Drilling Rig O&M` 7.79%

Interpretation:

- The best estimator improvement is still to strengthen the `well_scope` / `Well Cost` logic first.
- Within that well bucket, the biggest practical levers are **rig-time services**, **cementing**, **mud/engineering services**, **directional services**, and **casing/materials**.

### Where to Improve the Main Well-Cost Drivers

Observed driver signal from local data stays field-specific and should not be pooled by default.

Current mapped well context (`dashboard_rebuild_well_cost.csv` joined to `well_instance_context.csv`):

- `DARAJAT` mapped wells `n=10`: `actual_days` correlation to well cost `0.8042`, `actual_depth` `-0.0684`, `npt_days` `0.5856`
- `SALAK` mapped wells `n=9`: `actual_days` correlation to well cost `0.8927`, `actual_depth` `0.7728`, `npt_days` `0.1111`

Expanded workbook history (`DashBoard.Tab.Template` joined to `General.Camp.Data`):

- `DARAJAT` wells `n=15`: `actual_days` correlation to well cost `0.7658`, `actual_depth` `0.0449`, `npt_days` `0.0416`
- `SALAK` wells `n=14`: `actual_days` correlation to well cost `0.6926`, `actual_depth` `0.3299`, `npt_days` `-0.0815`

Recommended driver stack:

1. `actual_days` as the primary well-cost driver for both fields.
2. `actual_depth` as a secondary structural/material driver, especially for `SALAK`.
3. `deviation_type` / sidetrack flag as a complexity segment or multiplier, not the first driver.
4. `npt_days` or NPT ratio as a penalty/scenario driver, not the base estimator driver yet.
5. Keep `tie-in`, `rig move`, `rig mobilization`, `pad expansion`, and similar scope outside the core per-well model.

Interpretation:

- `DARAJAT` currently behaves more like a **time-driven** well-cost system than a depth-driven one.
- `SALAK` shows a more intuitive **time + depth** signal.
- NPT is operationally important, but current linkage quality and signal stability are not strong enough to make it the lead driver.

### Engineering-Intuitive Estimation Structure

The local data supports a split estimator for well cost:

```text
Well Cost
= Service-Time Cost
+ Material-Depth Cost
+ NPT Penalty
+ Complexity Multiplier
```

Suggested field-specific engineering priors from the workbook:

| Field | Service cost per drilling day | Material cost per ft MD | All-in well cost per drilling day | All-in well cost per ft MD |
| --- | ---: | ---: | ---: | ---: |
| `DARAJAT` | 119,482.74 | 191.23 | 156,605.26 | 806.73 |
| `SALAK` | 154,789.27 | 134.01 | 205,347.86 | 544.27 |

Use those as starting engineering priors, not final statistical coefficients.

Practical structure:

1. Estimate the **service bucket** from `actual_days`.
2. Estimate the **material bucket** from `actual_depth`.
3. Add a limited complexity factor for `multileg`, `side-tracked`, or `redrill`.
4. Add NPT as an explicit penalty only when attribution is reliable.
5. Estimate `Tie-in`, `Rig Mobilization`, `Rig Move`, and other shared scope in a separate campaign/hybrid layer.

This keeps the formula aligned with how drilling cost is actually consumed:

- time drives rig/services/crew exposure
- depth drives casing/material/consumable burden
- complexity changes the mix and inefficiency
- campaign-shared scope should not be forced into the per-well coefficient

### Primary Obstacles and Mitigations

#### 1. One-third of workbook cost is still not directly well-attributed

Even in the dashboard workbook, `General` / shared rows still account for:

- `DARAJAT`: 34.35% of field total
- `SALAK`: 34.15% of field total

Primary mitigation:

- Keep a two-layer estimator by design:
  - well model for direct well scope
  - campaign/hybrid allocator for shared scope

#### 2. Current mart still has material unmapped well spend

Current coverage report:

- `DARAJAT`: 75.76% mapped well rows, `18,177,107.68` unmapped actual USD
- `SALAK`: 82.50% mapped well rows, `9,528,869.58` unmapped actual USD

Primary mitigation:

- Make the `well_instance_id` / well bridge mandatory for well-level training.
- Hold unresolved spend in campaign/hybrid pools until the bridge is complete.

#### 3. Darajat workbook aliases are inconsistent across sheets

Using a simple exact alias join, only `7 / 15` DARAJAT dashboard wells matched to `General.Camp.Data`.

The mismatch is mostly deterministic:

- `DRJ-44OH`, `DRJ-45OH`, `DRJ-46OH`, `DRJ-47OH`
- `DRJ-49OH`, `DRJ-50OH`, `DRJ-51OH`, `DRJ-52OH`

After normalizing the `OH` suffix and using `Well Name Actual/SAP/Alt1/Alt2`, workbook join coverage becomes:

- `DARAJAT`: `15 / 15`
- `SALAK`: `14 / 14`

Primary mitigation:

- Codify this suffix/alias normalization into canonical well mapping before using the new workbook for driver validation.

#### 4. DARAJAT campaign linkage is still incomplete in current well context

`well_instance_context.csv` has blank `campaign_canonical` for `5 / 10` DARAJAT rows (`DRJ-53` to `DRJ-57`).

Primary mitigation:

- Backfill DARAJAT `campaign_canonical` from `General.Camp.Data` + canonical campaign mapping before field-specific driver validation.

#### 5. NPT/event linkage is still weak for primary estimation

The workbook provides `NPT.Data`, but current cost-to-event attribution is not yet strong enough to make NPT a stable lead driver.

Primary mitigation:

- Use NPT as a scenario penalty / diagnostic first.
- Promote it to a core driver only after event -> well -> campaign linkage becomes deterministic and auditable.

### Priority Recommendation

If the goal is to improve estimate quality with the new workbook, the best next move is:

1. Expand canonical campaign coverage to `DRJ - 2019` and `SLK - 2021`.
2. Strengthen the well estimator by splitting `Well Cost` into:
   - service-time component
   - material-depth component
   - explicit NPT penalty
3. Keep `Tie-in`, `Rig Mobilization`, `Rig Move`, `Pad` work, and other shared scope in a separate hybrid/campaign layer.
4. Validate DARAJAT and SALAK independently before any pooled logic is introduced.
