# Strategic Project Plan — The 6D Development Corridor

## Purpose
Define the strategic approach: Discover → Define → Design → Develop → Demonstrate → Deploy.

## Audience
Project leadership, architects, and phase leads.

## Prerequisites
- See [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) for detailed phase breakdowns

## Objective
Build a **drilling cost estimator that produces statistically valid Level-5 WBS estimates** from historical campaign data, with separate field validation and transparent assumptions.

## Development Corridor (6 Phases)

### Phase 1: Discover
**Goal:** Align data sources and naming conventions  
**Key Activities:**
- Inventory all source workbooks (sheets, row counts, key structures)
- Confirm WBS hierarchy consistency (L1–L5) across sources
- Validate named entity consistency (well names, campaign names, event codes)
- Identify data gaps and quality issues

**Deliverables:**
- Data inventory report (`reports/source_inventory.md`)
- Canonical schema contract (column mapping, naming rules)
- Assumption register seed (`docs/assumptions_register.md`)

---

### Phase 2: Define
**Goal:** Lock canonical data contracts and feature families  
**Key Activities:**
- Define canonical columns: `wbs_level_1..5`, `wbs_code`, `activity`, `cost`, `duration`, `well`, `campaign`, `event_code`, `classification`
- Create well-name crosswalk and campaign-name canonicalization rules
- Define feature families: depth, section, operation type, NPT/unscheduled events, campaign context
- Establish data quality thresholds (null %, duplicate keys, hierarchy violations)

**Deliverables:**
- Well master reference (`data/processed/well_master.csv`)
- Campaign master reference (`data/processed/canonical_campaign_mapping.csv`)
- Feature family specification (`docs/feature_families.md`)
- Quality thresholds document

---

### Phase 3: Design
**Goal:** Architect the statistical pipeline  
**Key Activities:**
- Design pipeline sequence: Ingest → Validate → Normalize → Enrich → Model → Report
- Separate deterministic rollups (hierarchical subtotals) from statistical estimation logic
- Define validation gates (quality thresholds, field-specific checks)
- Plan DARAJAT vs SALAK separation strategy

**Deliverables:**
- Pipeline architecture diagram
- Validation gate specifications
- Separation strategy document (field-specific processing)

---

### Phase 4: Develop
**Goal:** Implement reusable transforms and generate canonical data  
**Key Activities:**
- Implement schema normalization (source → canonical)
- Implement hierarchy validation (parent-child links, orphan detection)
- Implement well/campaign canonicalization
- Run QA checks and publish data quality report
- Generate canonical datasets in `data/processed/`

**Deliverables:**
- Clean, conformed datasets (all canonical CSVs)
- Data quality report with pass/fail thresholds
- Ingestion report (`reports/001_ingestion_task.md`)
- Updated assumption register

**STOP HERE.** No modeling until Phase 5.

---

### Phase 5: Demonstrate
**Goal:** Validate and document statistical models  
**Key Activities:**
- **Separate Analysis by Field:**
  - DARAJAT: Correlation analysis → identify significant drivers
  - DARAJAT: Simple regression → multiple regression → grouped benchmarking
  - SALAK: Repeat DARAJAT analysis independently
- Record data sufficiency flags (sample size, variance, missing %)
- Generate holdout validation metrics (MAE, MAPE, bias, error spread) per WBS level
- Create explainability artifacts: drill-down paths, confidence bands
- Publish confidence intervals and model diagnostics

**Deliverables:**
- Validation report (metrics by field, WBS level)
- Explainability summary (L1 → L5 drill-downs)
- Model version and metadata  
- Confidence band tables
- Updated assumption register

**GATE:** Phase 6 approval only after validation metrics approved.

---

### Phase 6: Deploy
**Goal:** Operationalize and release  
**Key Activities:**
- Build Streamlit app with:
  - Hierarchical drill-down (L1 → L5)
  - Scenario builder with assumption overrides
  - Confidence bands and uncertainty visualization
- Implement monthly/quarterly refresh runbook
- Package release bundle: model, metadata, QA checklist, assumptions, training docs
- Establish production monitoring and audit trail

**Deliverables:**
- Streamlit application (operational)
- Refresh runbook and automation
- Release checklist and deployment guide
- Monitoring dashboard
- Stakeholder training materials

---

## Cross-Phase Principles

| Principle | Implementation |
|-----------|-----------------|
| **Hierarchy First** | Every L5 item must map to valid L1–L4 parents; cost rollups additive upward |
| **Field Specificity** | DARAJAT and SALAK analyzed separately; separate validation metrics per field |
| **Evidence-Based** | Cost drivers require correlation/regression evidence; no assumptions without data |
| **Auditability** | Every output versioned, timestamped, with assumptions register; complete lineage to source rows |
| **Progressive Fidelity** | L1–L3 stable before L4–L5 refinement; model only after canonical data validated |

---

## Success Criteria

### Phase Completion Gates
- [ ] **Phase 1→2:** Canonical schema contract approved, data inventory complete
- [ ] **Phase 2→3:** Well/campaign masters finalized, feature families defined
- [ ] **Phase 3→4:** Architecture approved, validation gates designed
- [ ] **Phase 4→5:** All canonical CSVs generated, QA thresholds met, zero orphan L5 entries
- [ ] **Phase 5→6:** Validation metrics approved by field, confidence bands published
- [ ] **Phase 6:** App operational, refresh automated, assumptions maintained

### Final Delivery
- ✓ Level-5 cost estimates published with confidence intervals
- ✓ Separate validation metrics for DARAJAT and SALAK
- ✓ Traceable lineage from estimates back to source rows
- ✓ Operational refresh process with version control
- ✓ Stakeholder-accessible application and documentation
