# Canonical Campaign and Well Mapping Report

## Simplified mapping rules applied
1. Campaign source of truth uses official campaign codes.
2. Estimator scope is strictly limited to:
   - DARAJAT_2022 (`E530-30101-D225301`)
   - DARAJAT_2023_2024 (`E530-30101-D235301`)
   - SALAK_2025_2026 (`E540-30101-D245401`)
3. Legacy reference only: DARAJAT_2019 and SALAK_2021.
4. Wayang Windu, Hamiding, and unknown categories are excluded from estimator modeling.
5. Explicit well alias crosswalk is enforced from the provided canonical pairs.

## Exported campaign contract
- `canonical_campaign_mapping.csv` carries the canonical campaign key fields `campaign_code`, `campaign_id`, `campaign_name`, `field`, and `campaign_wbs_code`.
- `start_date`, `end_date`, and `actual_cost_total` remain intentionally blank in the Define layer because the current source package does not support an auditable canonical fill.

## Excluded records and unresolved anomalies
- Excluded campaign codes: **2**.
- Legacy-only campaign codes: **2**.
- In-scope well mapping rows: **54**.
- Well rows excluded from estimator: **48**.
- Detected posting exceptions / anomalies: **1**.

### Anomaly detail
| anomaly_type | campaign_raw | well_raw | source_sheet | note |
|---|---|---|---|---|
| posting_exception | DRJ 2023 | 20-1 | Data.Summary | 20-1 under DRJ 2023 treated as posting exception; not remapped to DARAJAT_2023_2024 well roster. |

### Training holdout rule
- `DRJ-Steam 1` is kept under `DARAJAT_2023_2024` campaign context but excluded from well-level training until confirmed.
