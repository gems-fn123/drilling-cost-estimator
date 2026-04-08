---
name: drilling-cost-workflow
description: "Use for drilling-cost-estimator repo tasks involving ingestion, canonicalization, hierarchy validation, field-specific analysis, auditable reports, or phase-gated workflow decisions."
argument-hint: "Task or files to inspect"
user-invocable: true
disable-model-invocation: false
---

# Drilling Cost Workflow

## What This Skill Does
- Keeps work aligned to the repository phase sequence and data contracts.
- Applies the field-specific rule: DARAJAT and SALAK stay separate unless there is explicit justification to combine them.
- Prevents premature modeling during ingestion, classification, or schema-definition work.
- Preserves auditability by tying outputs back to source rows, canonical contracts, and the assumptions register.

## When to Use
- Ingestion and profiling tasks
- Canonical schema, well mapping, or campaign mapping work
- WBS hierarchy validation and data quality checks
- Report updates, assumptions register updates, and phase-gate decisions
- Any task that needs separate DARAJAT and SALAK handling

## Procedure
1. Read the repository instructions first: [AGENTS.md](../../../AGENTS.md), [MASTER_INSTRUCTIONS.md](../../../MASTER_INSTRUCTIONS.md), and [docs/AGENT.md](../../../docs/AGENT.md).
2. Identify the current phase and confirm whether the task belongs in Discover, Define, Design, Develop, Demonstrate, or Deploy.
3. Check whether the work is field-specific and keep DARAJAT and SALAK separate unless the task explicitly justifies pooling.
4. Inspect the smallest set of files needed and prefer targeted changes over broad refactors.
5. If the task crosses a phase boundary or lacks evidence, stop and report the gap instead of guessing.

## Output Expectations
- State what changed.
- State which files or artifacts were touched.
- State what validation was performed.
- State any blockers, assumptions, or follow-up work.