# SALAK_2021 Scope Investigation (No Scope Change Applied)

## Question
Can `SALAK_2021` (`E540-30101-D20001`) be upgraded from `legacy_reference` to `in_scope` based on available raw workbook evidence?

## Search method
Searched all sheets in all raw workbooks for:
- exact campaign code: `E540-30101-D20001`
- aliases: `Salak Campaign 2021`, `Salak 2021`, `SLK 2021`, `2021 Salak`

## Where matches were found
1. `20260327_WBS_Data.xlsx` / `1. WellName.Dictionary`
   - Contains campaign-code-to-well-name dictionary rows (AWI 21-06, AWI 21-05, AWI 16-09, AWI 16-08, AWI 9-10).
   - No budget/actual/commit value columns.
2. `20260327_WBS_Data.xlsx` / `2. Drilling.Data.History`
   - Contains operational history rows for `2021 Salak` (dates, depth, drilling days).
   - No WBS-level financial measures (`Budget USD`, `Actual USD`, commitments) usable for WBS Lv.5 cost estimation.
3. `20260327_WBS_Data.xlsx` / `Drilled.Well`
   - Contains code-to-campaign-to-well roster mapping only.
   - No financial amounts.
4. `WBS Reference for Drilling Campaign (Drilling Cost).xlsx` / `Sheet1`
   - Contains campaign reference mapping only.
   - No financial amounts.

## Where matches were NOT found
- No `E540-30101-D20001` / Salak-2021 hits in financial sheets used for current campaign cost measures (e.g., current commit/actual extracts are for later campaigns and do not include this code).
- No identified rows with both this campaign code and WBS-level budget/actual/commit fields suitable for estimator training inputs.

## Assessment for estimator use
`SALAK_2021` currently lacks the required WBS-level financial records (actual/commit/budget) in the raw sources for estimator-grade training data assembly.

## Recommendation
Keep `SALAK_2021` as `legacy_reference` for now.

**Decision:** Do **not** upgrade to `in_scope` at this stage (no scope change applied).
