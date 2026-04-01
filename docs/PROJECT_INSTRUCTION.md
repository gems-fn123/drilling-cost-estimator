# Project Instruction (Obra App Development Corridor)

## Objective
Build a drilling cost estimator that produces statistically valid **Level-5 WBS estimates** from historical campaign data.

## Development Corridor
1. **Discover**
   - Align data sources and naming conventions.
   - Confirm WBS hierarchy consistency (L1-L5) and dictionary integrity.
2. **Define**
   - Lock canonical data contracts for WBS tree, WBS dictionary, and unscheduled event mapping.
   - Define feature families: depth, section, operation type, NPT/unscheduled events, and campaign context.
3. **Design**
   - Architect pipeline: ingest -> validate -> normalize -> enrich -> model -> report.
   - Separate deterministic rollups from statistical estimation logic.
4. **Develop**
   - Implement reusable transforms and guardrails for quality checks.
   - Produce per-WBS-level metrics and confidence bands.
5. **Demonstrate**
   - Compare estimates against holdout historical records.
   - Publish variance and error diagnostics by WBS level.
6. **Deploy**
   - Operationalize repeatable monthly/quarterly refresh with auditable outputs.

## Delivery Principles
- **Hierarchy first:** every cost record must map to WBS levels 1-5.
- **Traceability:** each estimate must be explainable from source rows.
- **Auditability:** every run should persist assumptions, version, and validation results.
- **Progressive fidelity:** stable L1-L3 baselines before L4-L5 refinement.
