# Canonical Campaign and Well Mapping Report

## Scope
This milestone only builds canonical campaign + well mapping from raw Excel files. No modeling or app work is included.

## Join Rules
1. **Campaign canonicalization**
   - `campaign_canonical` is uppercase, whitespace-normalized, with aliases normalized (`DRJ -> DARAJAT`, `SLK -> SALAK`).
   - `asset_canonical` is normalized to `DARAJAT`, `SALAK`, or `WAYANG WINDU` where applicable.
2. **Campaign key precedence**
   - Primary key candidate: `campaign_code_canonical` from `WBS CODE` or `WBS Drilling Campaign`.
   - Fallback key candidate: `(campaign_canonical, asset_canonical)` when code is absent.
3. **Well canonicalization**
   - `well_canonical` is uppercase, whitespace-normalized, and dash-spacing normalized.
   - Multi-line cells (e.g., Drilled.Well) are split into one row per well.
4. **Well-to-campaign assignment**
   - If a canonical campaign name maps to exactly one campaign code, that code is assigned as `campaign_code_inferred`.
   - If the campaign maps to multiple codes, mapping is marked ambiguous.

## Unresolved ambiguities
- Campaign rows with multiple campaign codes for a single `campaign_canonical`: **0**.
- Well rows unresolved (missing inferred code or ambiguous campaign mapping): **164**.

### Notes
- Empty campaign in source rows remains unresolved by design at this milestone.
- `canonical_well_mapping.csv` preserves source provenance (`source_file`, `source_sheet`, and source well column).

### Unresolved sample (first 10 rows)
| well_canonical | campaign_canonical | source_sheet | note |
|---|---|---|---|
| AWI 9-10RD | SALAK 2025 | Data.Summary | No campaign code could be inferred |
| AWI 23-2 | SALAK 2025 | Data.Summary | No campaign code could be inferred |
| AWI 21-8 | SALAK 2025 | Data.Summary | No campaign code could be inferred |
| AWI 3-9 | SALAK 2025 | Data.Summary | No campaign code could be inferred |
| AWI 9-11 | SALAK 2025 | Data.Summary | No campaign code could be inferred |
| AWI 23-1 | SALAK 2025 | Data.Summary | No campaign code could be inferred |
| AWI 21-7 | SALAK 2025 | Data.Summary | No campaign code could be inferred |
| AWI 2-7 ML | SALAK 2025 | Data.Summary | No campaign code could be inferred |
| AWI 2-6 | SALAK 2025 | Data.Summary | No campaign code could be inferred |
| 14-1 | DARAJAT 2022 | Data.Summary | No campaign code could be inferred |
