# SALAK_2021 Scope Investigation

## Objective
Record the current scope posture for SALAK_2021 after adding the dashboard workbook to the canonical source package.

## Findings
- Structured.Cost Lv5 rows for SALAK_2021 labels (`SLK - 2021` / `SALAK CAMPAIGN 2021`): **111**.
- Structured.Cost Lv5 rows for current in-scope campaigns (`SLK - 2025`, `DRJ - 2022`, `DRJ - 2024`): **646**.
- Sheets with SALAK 2021 references but no direct Lv5 cost-row authority used by this pipeline: **DashBoard.Tab.Template, Drill.Campaign.Ref.Tidy, General.Camp.Data, NPT.Data, Piv.Struct.Cost, Pivot.Master, Sheet9**.

## Interpretation
- Dashboard Structured.Cost provides the active Lv5 cost-bearing source for SALAK_2021.
- The widened unit-price program now treats the dashboard workbook as an authoritative historical source for campaign and well scope, so SALAK_2021 is retained in canonical scope.

## Recommendation
- Keep SALAK_2021 included for dashboard-driven history, unit-price analysis, and macro trend work.
- Keep estimator refresh fully dashboard-driven and avoid fallback to legacy workbooks.
