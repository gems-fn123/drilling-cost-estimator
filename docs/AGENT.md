# Agent Workflow Guide

## Purpose
Define the **operating purpose and workflow** for agents in this repository so execution stays aligned with `AGENTS.md`, `GPT_PROJECT_INSTRUCTIONS.md`, and project docs.

Primary purpose:
1. Reconstruct and maintain auditable historical drilling cost structure first.
2. Estimate only through evidence-backed, field-separated logic.
3. Keep every estimate traceable to source-row lineage and reproducible outputs.

## Audience
AI agents, automation contributors, and maintainers running work in this repository.

## Required Startup Sequence (Every Task)
1. Read `AGENTS.md`.
2. Read `GPT_PROJECT_INSTRUCTIONS.md`.
3. Read `MASTER_INSTRUCTIONS.md` sections 1–3.
4. Read this file (`docs/AGENT.md`) and `docs/WORKFLOW.md`.
5. Confirm scope and current phase before editing code.

## Agent Operating Contract

### Non-Negotiables
- Keep **DARAJAT** and **SALAK** separate unless explicit statistical justification is documented.
- Do not invent drivers or claim predictive validity without supporting analysis.
- Preserve exact WBS lineage (L1→L5) and source-row traceability.
- Keep unmapped/missing attribution rows visible in artifacts and audit outputs.
- Persist run artifacts in `data/processed/` and reports in `reports/`.

### Data-First Rule
The estimator and UI must consume one canonical history base (historical mart + bridges), not parallel ad hoc summary logic.

### Honest Uncertainty Rule
Uncertainty labels must reflect actual method used (empirical spread, bootstrap, holdout-derived metrics, etc.).

## Workflow by Phase (Execution Corridor)

### Phase 1–4 (Data Engineering & Validation Setup)
- Ingest, normalize, canonicalize, classify, and validate hierarchy.
- Publish canonical tables and QA reports.
- No unsupported model claims.

### Phase 5 (Demonstrate)
- Build field-specific validation artifacts.
- Publish MAE/MAPE/bias only from actual backtest/holdout logic.
- Produce confidence/uncertainty artifacts with explicit method labels.

### Phase 6 (Deploy)
- Build/operate Streamlit app that:
  - shows campaign totals,
  - shows per-well attribution,
  - shows WBS drill-down,
  - reconciles detail totals exactly,
  - exports audit package per run.

## Required Deliverable Patterns

### Processed Artifacts (`data/processed/`)
- Canonical mart/bridge and coverage outputs.
- Dashboard rebuild outputs.
- Backtest outputs by well and campaign.
- App run audit/summary/manifest outputs.

### Reports (`reports/`)
- Dashboard rebuild check.
- Field-specific validation reports.
- Handoff notes capturing assumptions, limitations, and open gaps.

## Agent Checklist Before Commit
- [ ] Field separation preserved in logic and outputs.
- [ ] Reconciliation checks pass (detail = total).
- [ ] Audit outputs include source rows/method/uncertainty flags.
- [ ] Unmapped attribution impact surfaced.
- [ ] Docs updated when workflow/behavior changes.

## Skills / Tooling Notes
- If superpowers skills are used in local Codex, install via native skill discovery (`~/.agents/skills/superpowers` symlink to `~/.codex/superpowers/skills`) and restart Codex.
- Do not rely on skills that bypass repository guardrails; AGENTS and project docs remain authoritative.
