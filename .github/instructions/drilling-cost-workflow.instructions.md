---
description: "Use when editing drilling-cost-estimator repo files that affect ingestion, canonical data contracts, validation reports, assumptions, or field-specific outputs."
applyTo: ["data/**", "docs/**", "reports/**", "src/**", "tests/**"]
name: "Drilling Cost Workflow Instructions"
---
# Drilling Cost Workflow Rules

- Keep work aligned to the project phase sequence: Discover, Define, Design, Develop, Demonstrate, Deploy.
- Do not pool DARAJAT and SALAK unless the task explicitly requires a justified combined analysis.
- Do not invent cost drivers, mappings, or assumptions without evidence from repository data or reports.
- Do not introduce statistical modeling during ingestion, classification, or schema-definition work.
- Keep outputs auditable and traceable to source rows, canonical contracts, and the assumptions register.
- Prefer minimal, targeted edits and preserve existing file conventions, canonical column names, and phase-gated artifacts.
- If a task crosses a phase boundary, call out the boundary rather than silently expanding scope.