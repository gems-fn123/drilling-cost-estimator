# MASTER INSTRUCTIONS: Drilling Cost Estimator Project

**Last Updated:** April 1, 2026  
**Status:** Active | **Audience:** All project contributors and AI agents

---

## Quick Start
1. Read this document (sections 1–3)
2. Refer to specialized guides: [AGENTS.md](AGENTS.md) (quick rules), [docs/AGENT.md](docs/AGENT.md) (agent workflow)
3. Execute per phase in [docs/WORKFLOW.md](docs/WORKFLOW.md)

---

## 1. PROJECT VISION

### Objective
Build a **statistically valid drilling campaign cost estimator** that produces defensible **Level-5 WBS estimates** from historical campaign data (DARAJAT and SALAK fields).

### Success Definition
- ✓ Every cost record maps to WBS levels 1–5 hierarchy
- ✓ Level-5 estimates explainable from source rows
- ✓ Separate validation metrics by field (DARAJAT, SALAK)
- ✓ Operationalized monthly/quarterly refresh with auditable outputs

---

## 2. CORE PRINCIPLES (Non-Negotiable)

1. **Hierarchy First**
   - Every Level-5 item must have a valid Level-1 → Level-4 parent chain
   - Cost rollups must be additive upward (L5 → L1)
   - Reject ambiguous WBS mappings until remediated

2. **Field Specificity**
   - Analyze DARAJAT and SALAK separately where required
   - Do not pool fields without statistical justification
   - Maintain field context in all outputs and reports

3. **No Premature Modeling**
   - Ingestion → Classification → Driver Validation → App
   - Do not build statistical models before canonical data exists
   - Keep methods interpretable (correlation → regression → grouped benchmarking)

4. **Auditability**
   - Every estimate must be traceable to source rows
   - Persist assumptions, model version, data timestamp, QA outputs
   - Maintain assumption register for manual overrides

5. **Evidence-Based**
   - Do not invent cost drivers without data validation
   - Record rationale, exclusions, uncertainty, and data sufficiency flags
   - Provide bias and error diagnostics by WBS level

---

## 3. DEVELOPMENT CORRIDOR (6 Phases)

### Phase 1: Discover
**Goal:** Align data sources, naming conventions, hierarchy consistency  
**Inputs:** Source workbooks in `data/raw/`  
**Outputs:** Data inventory report, canonical schema contract  
**Guardrail:** Confirm WBS hierarchy (L1–L5) and dictionary integrity  

**Key Assets:**
- `20260327_WBS_Data.xlsx` (primary: WBS.Tree, Data.Summary, Cost & Technical Data)
- `20260318_WBS_Dictionary.xlsx` (WBS_Dictionary, WBS.structure)
- `UNSCHEDULED EVENT CODE.xlsx` (controlled vocabulary)
- `WBS Reference for Drilling Campaign.xlsx` (supplemental)

### Phase 2: Define
**Goal:** Lock canonical data contracts  
**Deliverables:**
- Canonical columns: `wbs_level_1..5`, `wbs_code`, `activity`, `cost`, `duration`, `well`, `campaign`, `event_code`
- Well-name crosswalk table
- Feature families: depth, section, operation type, NPT/unscheduled events, campaign context

**Output Location:** `data/processed/`

### Phase 3: Design
**Goal:** Architect pipeline with guardrails  
**Pipeline:** Ingest → Validate → Normalize → Enrich → Model → Report  
**Separation:** Deterministic rollups ≠ Statistical estimation  

### Phase 4: Develop
**Goal:** Implement reusable transforms  
**Outputs:**
- Clean conformed datasets in `data/processed/`
- Per-WBS-level metrics and confidence bands
- Data quality report (pass/fail thresholds)

**Stable Deliverables:**
- `canonical_well_mapping.csv`
- `canonical_campaign_mapping.csv`
- `well_master.csv`
- `well_alias_lookup.csv`

### Phase 5: Demonstrate
**Goal:** Validate and explain  
**Metrics:**
- MAE/MAPE, bias, error spread by WBS level
- Comparison against holdout historical records
- Drill-down path: L1 total → L5 leaf drivers

**Output:** `reports/` (validation report, explainability summary)

### Phase 6: Deploy
**Goal:** Operationalize  
**Outputs:**
- Runbook for monthly/quarterly refresh
- Release checklist
- Production-ready output bundle
- Streamlit app (only after Phase 5 validation)

---

## 4. EXECUTION CHECKLIST

### Ingestion Task (Phase 2–4)
- [ ] Profile all source workbooks (sheet list, row counts, missingness, duplicate keys)
- [ ] Normalize schema to canonical columns
- [ ] Validate WBS hierarchy (no orphans, parent-child consistency L1 → L5)
- [ ] Map unscheduled events to standardized codes
- [ ] Generate outputs in `data/processed/`
- [ ] Publish ingestion report in `reports/`
- [ ] **DO NOT build model yet during ingestion**

### Classification Task
- [ ] Mark Level-5 items as `well_tied`, `campaign_tied`, or `hybrid`
- [ ] Validate classification logic against business domain
- [ ] Create lookup table in `data/processed/`

### Driver Validation (Separate by Field)
- [ ] DARAJAT: Run correlation analysis, identify significant drivers
- [ ] DARAJAT: Validate with simple/multiple regression, grouped benchmarking
- [ ] SALAK: Repeat DARAJAT analysis independently
- [ ] Record data sufficiency flags (sample size, variance, missing %)
- [ ] Publish validation report with uncertainty bands

### App Development (Phase 5 completion gate)
- [ ] Build Streamlit interface only after validated driver outputs exist
- [ ] Implement hierarchical drill-down (L1 → L5)
- [ ] Add scenario builder with assumption override capability
- [ ] Deploy with model version, data timestamp, confidence bands

---

## 5. DATA CONTRACTS

### Required Columns (Canonical)
```
wbs_level_1, wbs_level_2, wbs_level_3, wbs_level_4, wbs_level_5,
wbs_code, activity, 
cost, duration, 
well, campaign, 
event_code, classification (well_tied|campaign_tied|hybrid),
source_file, source_row, data_quality_flag
```

### WBS Hierarchy Rules
1. Every Level-5 node must have exactly one Level-4 parent
2. Every Level-4 node must have exactly one Level-3 parent (chain to L1)
3. `wbs_code` must be unique and immutable (canonicalized before aggregation)
4. `is_leaf = True` only for Level-5 nodes
5. Cost rollups must be additive upward

### Well Master Schema
```
well_id (primary key),
well_name (canonical),
well_aliases (JSON list),
field (DARAJAT|SALAK),
status, region, operator
```

### Campaign Master Schema
```
campaign_id (primary key),
campaign_name (canonical),
campaign_wbs_code,
field (DARAJAT|SALAK),
start_date, end_date, actual_cost_total
```

---

## 6. OUTPUT STRUCTURE

```
data/
  processed/
    ├── canonical_campaign_mapping.csv      # Campaign ID ↔ L1 WBS mapping
    ├── canonical_well_mapping.csv          # Well ID ↔ L5 WBS mapping
    ├── well_master.csv                     # Well reference table
    ├── well_alias_lookup.csv               # Well name variants
    ├── synthetic_campaign_placeholders.csv # Test data
    └── synthetic_wbs_lv5_placeholders.csv  # Test data

reports/
  ├── campaign_well_mapping_report.md       # Phase 2 findings
  ├── well_master_build_report.md           # Phase 4 findings
  ├── salak_2021_scope_investigation.md     # Field-specific insight
  ├── synthetic_placeholder_method.md       # Test data rationale
  └── tasks/
      └── 001_ingestion_task.md             # Ingestion phase deliverable
```

---

## 7. GUARDRAILS & CONSTRAINTS

### Strict Rules
- ❌ Never estimate a Level-5 item without valid L1–L4 path
- ❌ Do not build statistical models before canonical data exists
- ❌ Do not pool DARAJAT and SALAK without statistical test
- ❌ Do not invent cost drivers—validate against data first
- ❌ Do not publish estimates without uncertainty bands

### Quality Thresholds
- Reject rows with null or ambiguous WBS codes
- Flag records with >20% missing cost/duration fields
- Require >30 samples per Level-4 category for regression
- Confidence interval width must be <50% of estimate for L5

### Assumption Register
- Maintain `docs/assumptions_register.md`
- Document every manual override, data imputation, outlier removal
- Record business justification and date

---

## 8. AGENT WORKFLOW

### Before Starting
1. Read this file (sections 1–3)
2. Read [AGENTS.md](AGENTS.md)
3. Read [docs/AGENT.md](docs/AGENT.md)

### During Execution
1. Load and profile workbooks (see Phase 1 in section 3)
2. Map source → canonical schema
3. Validate WBS hierarchy and event codes
4. Generate outputs in `data/processed/` and `reports/`
5. **Stop after Phase 4.** Do not model until driver validation phase begins.

### Success Indicators
- ✓ All outputs in correct locations with expected column names
- ✓ Example: `data/processed/canonical_well_mapping.csv` has columns `{well_id, well_name, wbs_code_lv5, field, ...}`
- ✓ No orphan Level-5 entries
- ✓ Well-name and campaign-name canonicalization complete
- ✓ Event code mapping validated against UNSCHEDULED EVENT CODE.xlsx

---

## 9. FILE DEPENDENCY TREE

```
MASTER_INSTRUCTIONS.md (YOU ARE HERE)
├─ AGENTS.md (quick rules + working principles)
├─ GPT_PROJECT_INSTRUCTIONS.md (exec summary)
├─ docs/AGENT.md (agent operational guide)
├─ docs/PROJECT_INSTRUCTION.md (6D corridor detail)
├─ docs/WORKFLOW.md (5-phase pipeline)
├─ docs/WBS_TREE.md (hierarchy & schema reference)
└─ docs/QUICK_START_CHECKLIST.md (new agent onboarding)
```

---

## 10. REVISION HISTORY

| Date | Author | Change |
|------|--------|--------|
| 2026-04-01 | Copilot | Consolidated all instructions into single master; added execution checklist |

---

## Questions?
- **Setup & data assets?** → See [docs/AGENT.md](docs/AGENT.md)
- **Phases & deliverables?** → See [docs/WORKFLOW.md](docs/WORKFLOW.md)
- **WBS hierarchy rules?** → See [docs/WBS_TREE.md](docs/WBS_TREE.md)
- **Working rules & quick facts?** → See [AGENTS.md](AGENTS.md)
