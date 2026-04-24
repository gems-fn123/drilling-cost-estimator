# Dashboard Well Cost Driver Analysis

**Date:** 2026-04-24  
**Source:** `data/raw/20260422_Data for Dashboard.xlsx`  
**Comparison:** Current `historical_cost_mart.csv` + `well_instance_context.csv`

---

## Executive Summary

The new dashboard workbook expands historical coverage from **3 campaigns to 7 campaigns**, adding **$70.1M** of cost history (`DRJ - 2019`, `SLK - 2021`, `WW - 2018`, `WW - 2021`). For DARAJAT and SALAK only, coverage increases from **$106.6M to $176.6M (+65.7%)**.

**Biggest finding:** Direct **Well Cost** remains the dominant bucket (65-66% of field total), with **Services** dominating within Well Cost (75-76%). The primary well-cost driver is **drilling duration (days)**, not depth, especially for DARAJAT.

---

## 1. Where the Biggest Cost Chunk Lies

### 1.1 Field-Level Cost Breakdown (Dashboard `Structured.Cost`)

| Field | Total USD | Well Cost | % Well | Tie-in | Rig Mobilization | Rig Move |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `DARAJAT` | 110,040,018.70 | 72,245,593.49 | 65.65% | 8.80% | 8.43% | 4.10% |
| `SALAK` | 66,573,573.31 | 43,839,629.28 | 65.85% | 5.84% | 6.85% | 6.38% |

**Interpretation:**
- Two-thirds of spend is direct well execution
- One-third is shared/campaign scope (tie-in, mobilization, pad work)
- **Estimator implication:** Keep well model separate from campaign/hybrid allocator

### 1.2 Well Cost Internal Structure

| Field | Services | Material-LL | Material-NonLL |
| --- | ---: | ---: | ---: |
| `DARAJAT` | 76.30% | 23.43% | 0.28% |
| `SALAK` | 75.38% | 24.31% | 0.31% |

**Interpretation:**
- Services drive 3/4 of well cost, not materials
- **Estimator implication:** Time-driven components should dominate the formula

### 1.3 Top Service Items (Level 5)

**DARAJAT Services (n=12 top items, 76.30% of well cost):**

| Level 5 | USD | % of Services |
| --- | ---: | ---: |
| Contract Rig | 15,297,336.06 | 27.75% |
| Cement, Cementing & Pump Fees | 8,564,060.02 | 15.54% |
| Mud, Chemical and Engineering Service | 7,513,359.76 | 13.63% |
| Directional Drilling & Surveys | 6,532,895.17 | 11.85% |
| Equipment Rental | 5,622,229.63 | 10.20% |
| Bits, Reamer and Core heads | 2,687,536.76 | 4.88% |

**SALAK Services (n=12 top items, 75.38% of well cost):**

| Level 5 | USD | % of Services |
| --- | ---: | ---: |
| Cement, Cementing & Pump Fees | 5,875,073.33 | 17.78% |
| Contract Rig | 5,771,257.57 | 17.46% |
| Mud, Chemical and Engineering Service | 3,773,120.96 | 11.42% |
| Directional Drilling & Surveys | 3,690,678.63 | 11.17% |
| Equipment Rental | 3,617,368.42 | 10.95% |
| **Drilling Rig O&M** | 3,415,573.27 | 10.34% |

**Field-specific insight:**
- `DARAJAT`: Contract Rig is #1 (27.75% vs 17.46% for SALAK)
- `SALAK`: Cementing is #1, and Drilling Rig O&M appears as a unique top-6 item (10.34%)
- **Estimator implication:** Field-specific service priors are justified

---

## 2. Well-Cost Driver Signal Analysis

### 2.1 Dashboard Workbook Well-Level Correlations

| Field | n wells | Corr(Cost, Days) | Corr(Cost, Depth) |
| --- | ---: | ---: | ---: |
| `DARAJAT` | 15 | 0.2854 | 0.0406 |
| `SALAK` | 14 | 0.3434 | 0.1330 |

**Interpretation:**
- Weak correlations across expanded history
- Days signal stronger than depth for both fields
- Depth signal nearly flat for DARAJAT

### 2.2 Current Mapped Well Context Correlations

| Field | n wells | Corr(Cost, Days) | Corr(Cost, Depth) | Corr(Cost, NPT) |
| --- | ---: | ---: | ---: | ---: |
| `DARAJAT` | 5 | **0.8024** | -0.2897 | -0.3517 |
| `SALAK` | 9 | **0.8927** | **0.7728** | 0.1111 |

**Interpretation:**
- Current mapped wells show very strong day-driven signal (0.80-0.89)
- SALAK shows strong depth signal (0.77); DARAJAT does not (-0.29)
- NPT signal is unstable (negative for DARAJAT, weak positive for SALAK)
- **Estimator implication:** Days should be the primary driver; depth secondary for SALAK

### 2.3 Why the Difference?

Dashboard correlations are weaker because:
1. Includes `DRJ - 2019` and `SLK - 2021` with different operational regimes
2. Campaign-level allocations repeated per well in `DashBoard.Tab.Template`
3. Depth values are zero for some wells (inflates noise)

Current mapped wells are stronger because:
1. Only in-scope campaigns with consistent data quality
2. Explicit well attribution from `Data.Summary` Lv5 rows
3. NPT and depth are better curated

**Recommendation:** Use current mapped wells for coefficient estimation; use dashboard for scope validation and historical range checks.

---

## 3. Engineering-Intuitive Estimation Structure

### 3.1 Recommended Formula

```text
Well Cost = Service-Time Cost + Material-Depth Cost + NPT Penalty + Complexity Multiplier
```

**Component mapping to WBS:**

| Component | Driver | WBS Level 5 examples | Estimation layer |
| --- | --- | --- | --- |
| Service-Time | `actual_days` | Contract Rig, Directional Drilling, Mud Service, Equipment Rental, Bits | Per-well model |
| Material-Depth | `actual_depth` | Casing, Cement materials, Well Equipment | Per-well model |
| NPT Penalty | `npt_days` or NPT ratio | Unscheduled events, remediation | Scenario layer |
| Complexity | `deviation_type` | Multileg, side-tracked, redrill flags | Multiplier/segment |

**Excluded from per-well model (campaign/hybrid layer):**
- Tie-in
- Rig Mobilization
- Rig Move
- Road & Pad
- Special Requirement Existing Pad
- Conductor Casing Installation (unless well-tied)

### 3.2 Field-Specific Engineering Priors (Dashboard-Derived)

| Field | Service cost per day | Material cost per ft MD | All-in well cost per day | All-in well cost per ft MD |
| --- | ---: | ---: | ---: | ---: |
| `DARAJAT` | $119,483 | $191 | $156,605 | $807 |
| `SALAK` | $154,789 | $134 | $205,348 | $544 |

**Derivation:**
- Service cost per day = Services USD / sum(Duration_days)
- Material cost per ft = Material-LL USD / sum(TotalDepth_ft)
- All-in per day = Well Cost USD / sum(Duration_days)
- All-in per ft = Well Cost USD / sum(TotalDepth_ft)

**Interpretation:**
- `DARAJAT` is more depth-intensive (higher $/ft, lower $/day)
- `SALAK` is more time-intensive (higher $/day, lower $/ft)
- **Estimator implication:** Field-split models are justified

### 3.3 Suggested Coefficient Initialization

**DARAJAT well model:**
```python
well_cost_usd = (119_000 * actual_days) + (190 * actual_depth) + complexity_factor
```

**SALAK well model:**
```python
well_cost_usd = (155_000 * actual_days) + (135 * actual_depth) + complexity_factor
```

**Complexity factor examples:**
- `multileg`: +15-25%
- `side-tracked`: +20-30%
- `redrill`: +10-20%
- `standard`: baseline

**NPT penalty (optional, scenario layer):**
```python
npt_penalty = npt_days * 50_000  # field-specific day rate
```

---

## 4. Primary Obstacles and Mitigations

### 4.1 One-Third of Cost is Not Well-Attributed

**Problem:**
- `DARAJAT`: 34.35% of field total is General/shared rows
- `SALAK`: 34.15% of field total is General/shared rows

**Mitigation:**
- Keep two-layer estimator:
  - Well model for direct well scope (65-66% of spend)
  - Campaign/hybrid allocator for shared scope (34-35%)
- Do not force shared costs into per-well coefficients

### 4.2 Current Mart Has Unmapped Well Spend

**Problem:**
- `DARAJAT`: 24.24% of rows unmapped, $18.2M actual USD
- `SALAK`: 17.50% of rows unmapped, $9.5M actual USD

**Mitigation:**
- Make `well_instance_id` mandatory for well-model training
- Hold unresolved spend in campaign/hybrid pools until bridge is complete
- Prioritize well-mapping for highest-spend Lv5 codes first

### 4.3 DARAJAT Campaign Linkage Incomplete

**Problem:**
- `well_instance_context.csv` has blank `campaign_canonical` for 5 DARAJAT wells (`DRJ-53` to `DRJ-57`)

**Mitigation:**
- Backfill from `General.Camp.Data` + canonical campaign mapping
- Use dashboard `Campaign` column as cross-check

### 4.4 NPT/Event Linkage Still Weak

**Problem:**
- NPT correlation unstable (negative for DARAJAT mapped wells)
- Event-to-cost attribution not yet deterministic

**Mitigation:**
- Use NPT as scenario penalty first, not core driver
- Promote to core driver only after event->well->campaign linkage is auditable

### 4.5 DARAJAT Workbook Alias Inconsistency

**Problem:**
- Dashboard wells like `DRJ-44OH`, `DRJ-45OH` don't match canonical `DRJ-XX`
- Only 7/15 DARAJAT wells matched with exact alias join

**Mitigation:**
- Normalize `OH` suffix in canonical well mapping
- Use `Well Name Actual/SAP/Alt1/Alt2` from `General.Camp.Data`
- Codify suffix/alias rules before driver validation

---

## 5. Priority Recommendations

### 5.1 Immediate (Low Risk, High Value)

1. **Expand canonical campaign coverage**
   - Add `DARAJAT_2019` and `SALAK_2021` to mapping
   - Update scope flags in assumptions register

2. **Strengthen well estimator structure**
   - Split `Well Cost` into:
     - Service-time component (days-driven)
     - Material-depth component (depth-driven)
     - Explicit NPT penalty (scenario layer)
   - Keep field-specific coefficients

3. **Add dashboard benchmark cards to Streamlit**
   - Historical well cost ranges by campaign
   - Service vs material split visualization
   - Top 10 service items per field

### 5.2 Medium-Term (Requires Data Prep)

4. **Backfill DARAJAT campaign linkage**
   - Use `General.Camp.Data` for `DRJ-53` to `DRJ-57`
   - Validate against dashboard campaign labels

5. **Normalize well aliases**
   - Handle `OH` suffix, `ML` suffix, `STEAM` aliases
   - Update `well_alias_lookup.csv` with dashboard-derived mappings

6. **Improve well bridge coverage**
   - Target top 20 Lv5 codes by spend
   - Resolve $18.2M DARAJAT and $9.5M SALAK unmapped spend

### 5.3 Long-Term (Architectural)

7. **Build two-layer estimator**
   - Well model: per-well, days + depth + complexity
   - Campaign/hybrid model: shared scope allocator

8. **Event-driven NPT module**
   - Link `NPT.Data` to cost rows
   - Build event frequency and cost-per-event models

9. **Depth/section driver enrichment**
   - Integrate `Drill.Depth.Days` and `5. Well.Size.Data`
   - Build section-length and intensity drivers

---

## 6. Integration Decision

**Do NOT replace `Data.Summary` as the authoritative raw source.**

**Reason:**
- Dashboard lacks `WBS_ID`, `WBS_Level`, raw code hierarchy
- Current estimator and WBS tree require code-level lineage
- Dashboard is presentation-layer optimized, not raw ingestion optimized

**Recommended integration path:**
1. Use dashboard as **benchmark mart** and **enrichment source**
2. Keep `Data.Summary` -> `historical_cost_mart.csv` as estimator backbone
3. Add dashboard-derived wells to canonical mapping after alias normalization
4. Use dashboard priors for coefficient initialization, not final statistical fits

---

## Appendix A: Campaign Coverage Expansion

| Field | Current campaigns | Added by dashboard | Added USD | New field total | Uplift |
| --- | --- | --- | ---: | ---: | ---: |
| `DARAJAT` | 2022, 2023/2024 | 2019 | 42,003,384.16 | 152,043,402.86 | +38.1% |
| `SALAK` | 2025/2026 | 2021 | 28,051,247.74 | 94,624,821.05 | +42.2% |
| **Combined** | 3 campaigns | 2 campaigns | 70,054,631.90 | 246,668,223.91 | +39.6% |

**Note:** `Wayang Windu` (2018, 2021; $54.1M) remains excluded unless project scope is widened.

---

## Appendix B: Data Quality Notes

- Dashboard `DashBoard.Tab.Template` repeats campaign-level shared costs per well row
- Use `Structured.Cost` for fact-level analysis, not `DashBoard.Tab.Template`
- Some wells have zero depth/duration; filter before coefficient estimation
- NPT attribution is campaign-level in dashboard, not well-level

---

**Prepared by:** Drilling Cost Workflow Steward  
**Validation status:** Field-specific analysis complete; ready for Phase 5 estimator engine integration
