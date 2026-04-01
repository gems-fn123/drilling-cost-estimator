# WBS Level Structure & Technical Schema Reference

## Purpose
Define WBS hierarchy semantics, parent-child rules, and canonical data schema for all cost estimation work.

## Audience
Engineers, architects, data engineers, app developers.

## Prerequisites
- Read [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) section 5 (Data Contracts)
- Review [docs/WORKFLOW.md](docs/WORKFLOW.md) Phase 2 (Canonicalization)

---

## WBS Level Semantics

### Hierarchical Levels (L1 → L5)

| Level | Semantic | Typical Role | Estimation Grain | Count in Project |
|-------|----------|--------------|------------------|------------------|
| **L1** | Major campaign phase (e.g., Well Drilling, Completion, Testing) | Strategic milestone | Campaign-level rollup | ~5–10 per campaign |
| **L2** | Functional domain under phase (e.g., Surface, Intermediate, Production sections) | Work domain | Phase breakdown | ~3–5 per L1 |
| **L3** | Work package group (e.g., Casingrunning, Cementing, Pressure testing) | Activity family | Related work cluster | ~3–8 per L2 |
| **L4** | Executable activity block (e.g., Install 9-5/8" casing to 2000m, Squeeze test) | Specific operation | Operation scope | ~2–5 per L3 |
| **L5** | Atomic estimate item (individual cost lines with discrete cost/duration) | **Target forecast grain** | Single cost line | ~5–15 per L4 |

---

## Required Hierarchy Rules (Non-Negotiable)

### Parent-Child Structure
1. **Every Level-5 node must have exactly one Level-4 parent**
   ```
   wbs_code_lv5: e.g., "1.2.3.4.5"
   wbs_code_lv4: e.g., "1.2.3.4"
   → wbs_code_lv4 must be the prefix of wbs_code_lv5
   ```

2. **Every Level-4 node must have exactly one Level-3 parent** (and so on down to L1)
   ```
   wbs_code_lv4: "1.2.3.4"
   wbs_code_lv3: "1.2.3" (must be prefix)
   wbs_code_lv2: "1.2"
   wbs_code_lv1: "1"
   ```

3. **No orphan entries allowed**
   - Every Level-5 must have a complete chain to Level-1
   - Reject any row where any parent link is missing or invalid
   - Document orphans in data quality flag before remediation

### Cost Rollup Rules
- **Additive Upward:** Cost(Level-4) = SUM(Cost(Level-5 children))
- **No Double-Counting:** Every cost belongs to exactly one Level-5 leaf
- **Consistency Check:** Cost(L1) = SUM(Cost(L2 children)) = … = SUM(Cost(L5 children))
- **Validation:** Publish rollup verification table per phase-end report

---

## Minimum Required Fields Per WBS Node

### Identification
```
wbs_code (string, unique, immutable)
  Example: "1.2.3.4.5" for Level-5
  Format: dot-separated integers, no gaps
  
wbs_level_1 (string, non-null)
wbs_level_2 (string, non-null)
wbs_level_3 (string, non-null)
wbs_level_4 (string, non-null)
wbs_level_5 (string, non-null, if leaf)
```

### Metadata
```
activity (string)
  Human-readable activity description
  Example: "Install 9-5/8 inch casing to 2000m"

level (integer: 1–5)
  Hierarchical depth
  
is_leaf (boolean)
  True if Level-5, False otherwise
  
parent_wbs_code (string)
  Parent node code (e.g., "1.2.3.4" for L5 node "1.2.3.4.5")
```

### Financial
```
cost_actual (numeric, ≥0, nullable)
  Historical realized cost in campaign
  
cost_estimated (numeric, ≥0, nullable)
  Model-generated estimate
  
duration (numeric, ≥0, nullable)
  Days or months (field-dependent)
```

### Estimation Context
```
classification (enum: "well_tied" | "campaign_tied" | "hybrid")
  well_tied: cost varies primarily by well (depth, geology)
  campaign_tied: cost varies primarily by campaign scope
  hybrid: both factors significant
  
well_id (string, nullable)
  Link to well master (null if campaign_tied)
  
campaign_id (string, non-null for L1)
  Link to campaign master
  
field (enum: "DARAJAT" | "SALAK", non-null)
  Field context (separate models per field)
```

### Confidence & Uncertainty
```
confidence_low (numeric, nullable)
  Lower 90% confidence bound on estimate
  
confidence_high (numeric, nullable)
  Upper 90% confidence bound on estimate
  
confidence_pct (numeric: 0–100, nullable)
  Confidence level (e.g., 90, 95)
  
data_quality_flag (string, nullable)
  null: high confidence
  "flag_missing_cost": cost data absent
  "flag_missing_duration": duration absent
  "flag_ambiguous_wbs": hierarchy unclear
  "flag_outlier": statistical outlier detected
  "flag_insufficient_sample": <30 comparable records
```

### Lineage & Audit
```
source_file (string)
  Original workbook name
  
source_row (integer)
  Original row number in source sheet
  
source_sheet (string)
  Sheet name in source workbook
  
data_ingestion_date (date)
  When record was canonicalized
  
model_version (string)
  Version of estimation model used
  
assumptions_applied (JSON array, nullable)
  List of assumption override IDs (see assumptions_register.md)
```

---

## Sample WBS Tree (Well Drilling Example)

```
1.0: Well Drilling (L1)
├─ 1.1: Well Design & Planning (L2)
│  ├─ 1.1.1: Wellbore Plan (L3)
│  │  ├─ 1.1.1.1: Geological Input & Survey (L4)
│  │  │  └─ 1.1.1.1.1: Formation Characterization (L5) [LEAF]
│  │  └─ 1.1.1.2: Casing Design (L4)
│  │     └─ 1.1.1.2.1: Hydraulics Simulation & Optimization (L5) [LEAF]
│  └─ 1.1.2: Equipment Procurement (L3)
│     └─ 1.1.2.1: Rig Requirements (L4)
│        └─ 1.1.2.1.1: Rig Mobilization & Setup (L5) [LEAF]
├─ 1.2: Drilling Operations (L2)
│  ├─ 1.2.1: Surface Section (L3)
│  │  └─ 1.2.1.1: Shallow Hole Drilling (L4)
│  │     └─ 1.2.1.1.1: Drill 24" hole to 100m, DARAJAT Well A (L5) [LEAF]
│  ├─ 1.2.2: Intermediate Section (L3)
│  │  └─ 1.2.2.1: Intermediate Hole Drilling (L4)
│  │     └─ 1.2.2.1.1: Drill 17-1/2" hole 100–1000m (L5) [LEAF]
│  └─ 1.2.3: Production Section (L3)
│     └─ 1.2.3.1: Production Hole Drilling (L4)
│        └─ 1.2.3.1.1: Drill 8-1/2" hole 1000–2500m (L5) [LEAF]
└─ 1.3: Well Testing & Cleanup (L2)
   └─ 1.3.1: DST Operations (L3)
      └─ 1.3.1.1: Formation Testing (L4)
         └─ 1.3.1.1.1: Pressure Test & Analysis (L5) [LEAF]
```

---

## Hierarchy Validation Checklist

- [ ] No level skipped (e.g., L2 → L4 directly forbidden)
- [ ] No duplicate `wbs_code` values (uniqueness enforced)
- [ ] No orphan Level-5 entries (all have L1–L4 parents)
- [ ] Parent-child prefix rule validated (wbs_code_lv5 starts with wbs_code_lv4)
- [ ] Cost rollups additive upward
- [ ] No cycles or circular references
- [ ] Field context consistent (DARAJAT vs SALAK not mixed in single branch)

---

## Canonical Column Set (Full Schema)

**Master table: `data/processed/canonical_wbs_hierarchy.csv`**

```
wbs_code,
wbs_level_1, wbs_level_2, wbs_level_3, wbs_level_4, wbs_level_5,
level, is_leaf, parent_wbs_code,
activity,
cost_actual, cost_estimated, duration,
classification, well_id, campaign_id, field,
confidence_low, confidence_high, confidence_pct,
data_quality_flag,
source_file, source_row, source_sheet, data_ingestion_date,
model_version, assumptions_applied
```

---

## Example: Well Master Integration

**File: `data/processed/well_master.csv`**

```
well_id, well_name, field, depth_md, depth_tvd, 
  region, operator, status, start_date, end_date
A001, DARAJAT-0001, DARAJAT, 3200, 2800, North, PertaminaEP, drilled, 2025-01-15, 2025-03-20
A002, DARAJAT-0002, DARAJAT, 2950, 2600, North, PertaminaEP, drilled, 2025-02-01, 2025-04-10
…
```

**In WBS records, `well_id = "A001"` links to `well_master.csv` row with depth_md=3200, field=DARAJAT**

---

## Example: Campaign Master Integration

**File: `data/processed/canonical_campaign_mapping.csv`**

```
campaign_id, campaign_name, field, start_date, end_date, 
  actual_cost_total, num_wells, wbs_code_lv1
C001, Drilling_Campaign_2025_Q1, DARAJAT, 2025-01-01, 2025-03-31, 45000000, 3, 1
C002, Drilling_Campaign_2025_Q2, SALAK, 2025-04-01, 2025-06-30, 52000000, 4, 1
…
```

**In WBS records, `campaign_id = "C001"` links to row with total cost=$45M, field=DARAJAT**

---

## Key Points for App Developers

1. **Tree Navigation:**
   - Render collapsible tree from L1 root
   - Highlight leaf nodes (is_leaf=True, level=5)
   - Follow parent_wbs_code links for drill-down

2. **Cost Display:**
   - Show cost_estimated with [confidence_low, confidence_high] confidence bands
   - Show data_quality_flag if populated (user should be warned of uncertainty)
   - Rollup costs upward: L5 → L4 → L3 → L2 → L1

3. **Scenario Building:**
   - When user overrides a well or depth, mark in assumptions_applied
   - Recalculate affected L4–L5 costs using appropriate model
   - Update confidence_low/high based on user variance
   - Log override to assumptions_register.md

---

## References
- [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) section 5 (Data Contracts)
- [docs/WORKFLOW.md](docs/WORKFLOW.md) Phase 2 (Canonicalization)
- [docs/AGENT.md](docs/AGENT.md) section *Data Contracts*
