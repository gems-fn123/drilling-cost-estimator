# Agent Workflow Guide

## Purpose
Operational guide for AI agents executing data ingestion, validation, and classification tasks.

## Audience
AI agents, automation specialists, and Phase 2–4 engineers.

## Prerequisites
1. Read [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) sections 1–3
2. Read [AGENTS.md](AGENTS.md)
3. Review your assigned phase in [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) section 3

## Data Assets in This Repository (`data/raw/`)

### Primary Workbooks
- **20260327_WBS_Data.xlsx**
  - Sheets: `WBS.Tree`, `Data.Summary`, `Cost & Technical Data`
  - Primary source for WBS hierarchy and cost records
  
- **20260318_WBS_Dictionary.xlsx**
  - Sheets: `WBS_Dictionary`, `WBS.structure`
  - Dictionary and structure reference

### Supporting Assets
- **UNSCHEDULED EVENT CODE.xlsx**
  - Controlled vocabulary for unscheduled event classification
  - Use for mapping event records to standardized codes

- **WBS Reference for Drilling Campaign (Drilling Cost).xlsx**
  - Supplemental campaign reference
  - Validate against primary workbook hierarchies

## Core Workflow (Phases 2–4)

1. **Load and Profile** (Phase 1)
   - Sheet inventory (list all sheets, row counts)
   - Missingness analysis (null counts per column)
   - Check for duplicate keys and orphan entries
   - **Output:** Profile summary to `reports/source_inventory.md`

2. **Normalize Schema** (Phase 2)
   - Map source columns to canonical schema:
     ```
     wbs_level_1, wbs_level_2, wbs_level_3, wbs_level_4, wbs_level_5,
     wbs_code, activity, cost, duration, well, campaign, event_code,
     source_file, source_row, data_quality_flag
     ```
   - Standardize naming conventions (remove special chars, whitespace)
   - Create well-name and campaign-name canonicalization crosswalks

3. **Validate Hierarchy** (Phase 3)
   - Every Level-5 entry must have valid L1–L4 parents
   - Every node must have exactly one parent (except L1)
   - Cost rollups must be additive upward (L5 → L1)
   - Record violations in `data_quality_flag` column

4. **Map Unscheduled Events** (Phase 3)
   - Join event records to `UNSCHEDULED EVENT CODE.xlsx`
   - Standardize event codes
   - Flag unmapped events for manual review

5. **Generate Outputs** (Phase 4)
   - Save canonical tables in `data/processed/`:
     - `canonical_well_mapping.csv`
     - `canonical_campaign_mapping.csv`
     - `well_master.csv`
     - `well_alias_lookup.csv`
   - Publish ingestion report: `reports/001_ingestion_task.md`
   - **DO NOT model or estimate yet**

## Data Contracts

### Canonical Columns (Required)
```
wbs_level_1 (string, non-null)
wbs_level_2 (string, non-null)
wbs_level_3 (string, non-null)
wbs_level_4 (string, non-null)
wbs_level_5 (string, non-null)
wbs_code (string, unique, non-null)
activity (string)
cost (numeric, ≥0)
duration (numeric, ≥0)
well (string)
campaign (string)
event_code (string or null)
classification (enum: well_tied|campaign_tied|hybrid)
source_file (string)
source_row (integer)
data_quality_flag (string: null, "high_confidence", "flag_missing_cost", "flag_ambiguous_wbs", etc.)
```

### Well Master
```
well_id (string, primary key)
well_name (string, canonical)
well_aliases (JSON array of alternate names)
field (enum: DARAJAT|SALAK)
status (string)
region (string)
operator (string)
```

### Campaign Master
```
campaign_id (string, primary key)
campaign_name (string, canonical)
campaign_wbs_code (string, L1 WBS code)
field (enum: DARAJAT|SALAK)
start_date (date)
end_date (date)
actual_cost_total (numeric)
```

## Execution Guardrails

### Mandatory
- ✓ Never estimate a Level-5 item without a valid Level-1…5 path
- ✓ Reject rows with ambiguous WBS mapping until remediated
- ✓ Keep well and campaign names canonicalized before any aggregation
- ✓ Maintain an assumption register for all manual overrides

### Quality Thresholds
- Flag records with >20% missing cost/duration data
- Reject null or duplicate WBS codes (L1–L5)
- Document all data imputation decisions in assumption register
- Verify parent-child links (every L2 parent must be in L1, etc.)

### Field Specificity
- Do NOT mix DARAJAT and SALAK records in any single analysis
- Create separate wells masters and campaign masters per field
- Keep field context in all output file names and column headers

## Success Criteria

- [ ] All source workbooks profiled (sheet list, row counts, missingness → `reports/source_inventory.md`)
- [ ] Schema normalized to canonical columns (see Data Contracts above)
- [ ] WBS hierarchy validated: zero orphan L5 entries, all parents linkable to L1
- [ ] Well and campaign names canonicalized with crosswalk tables
- [ ] Unscheduled events mapped to standardized codes
- [ ] All outputs in `data/processed/` with correct column names
- [ ] Ingestion report published to `reports/001_ingestion_task.md`
- [ ] **NO model training or cost estimation performed in this phase**
