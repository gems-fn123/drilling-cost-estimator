# QUICK START CHECKLIST FOR NEW AGENTS

**Purpose:** Onboard new agents to the project in <10 minutes  
**Last Updated:** April 1, 2026

---

## Read First (5 min)

- [ ] [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) — sections 1–3 (Vision + Principles + Corridor)
- [ ] [AGENTS.md](AGENTS.md) — working rules
- [ ] [docs/AGENT.md](docs/AGENT.md) — data assets + agent workflow

**Stop here.** You now understand the project scope, core constraints, and which phase you're entering.

---

## Context Check (2 min)

- [ ] What phase are you entering? (Discover, Define, Design, Develop, Demonstrate, Deploy)
- [ ] What are your inputs? (data files, artifact locations)
- [ ] What are your explicit outputs? (where to save, file names, required columns)
- [ ] What are the success criteria? (checklist of testable conditions)

**If unclear:** Re-read [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) section 3 (Development Corridor) for your phase.

---

## Per-Phase Startup

### Phase 1–4: Ingestion, Classification, Design, Develop

- [ ] Locate source workbooks in `data/raw/`
- [ ] Open [docs/AGENT.md](docs/AGENT.md) section *Agent Workflow*
- [ ] Load and profile workbooks (sheet list, row counts, missingness)
- [ ] Map to canonical schema (see [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) section 5)
- [ ] Run QA checks (null keys, duplicate WBS codes, parent-child links)
- [ ] Generate outputs → `data/processed/` and `reports/`
- [ ] ❌ **DO NOT MODEL.** Ingestion only.

**Success:** All outputs in correct locations, no orphan Level-5 entries, canonical mapping complete.

### Phase 5: Demonstrate (Validation)

- [ ] Load outputs from [Phase 4](MASTER_INSTRUCTIONS.md#phase-4-develop)
- [ ] For DARAJAT: Run correlation → regression → benchmarking
- [ ] For SALAK: Repeat analysis independently
- [ ] Record data sufficiency flags (sample size, variance, missing %)
- [ ] Publish metrics: MAE/MAPE, bias, error spread by WBS level
- [ ] Generate explainability: drill-down L1 → L5, confidence bands

**Success:** Validation report published, uncertainty bands on all estimates.

### Phase 6: Deploy (App)

- [ ] Load validated model outputs from Phase 5
- [ ] Build Streamlit app with hierarchical drill-down
- [ ] Add scenario builder with assumption overrides
- [ ] Package with version, timestamp, confidence bands
- [ ] Test monthly refresh process

**Success:** App demonstrates estimates with full lineage back to source data.

---

## Guardrails (Must-Know)

- ❌ Never estimate without valid L1–L4 WBS path
- ❌ Never pool DARAJAT + SALAK without statistical test
- ❌ Never invent cost drivers—validate first
- ❌ Never model before canonical data exists
- ❌ Never ship estimates without uncertainty bands

---

## Reference Documents (Detailed)

| Task | Reference |
|------|-----------|
| Understand full project intent | [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) section 5 (Data Contracts) |
| Ingestion workflow specifics | [docs/WORKFLOW.md](docs/WORKFLOW.md) Phase 2–4 |
| WBS hierarchy rules | [docs/WBS_TREE.md](docs/WBS_TREE.md) |
| Agent-specific guardrails | [docs/AGENT.md](docs/AGENT.md) section *Guardrails* |
| Working rules summary | [AGENTS.md](AGENTS.md) |
| Strategic context | [docs/PROJECT_INSTRUCTION.md](docs/PROJECT_INSTRUCTION.md) |

---

## Questions During Execution?

1. **"What columns do I need?"** → [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) section 5 (Data Contracts)
2. **"Where do I save outputs?"** → [MASTER_INSTRUCTIONS.md](MASTER_INSTRUCTIONS.md) section 6 (Output Structure)
3. **"When do I model?"** → Phase 5 only (see [docs/WORKFLOW.md](docs/WORKFLOW.md))
4. **"What if data is ambiguous?"** → See [docs/AGENT.md](docs/AGENT.md) *Guardrails* → maintain assumption register

---

## Execution Checklist Template

Use this for each task:

```
Task: [Specific deliverable, e.g., "Ingest WBS Data.xlsx into canonical schema"]

Input:
- [ ] [File/location]
- [ ] [Required columns: list]

Process:
- [ ] [Step 1]
- [ ] [Step 2]
- [ ] [QA check]

Output:
- [ ] [File path: data/processed/...]
- [ ] [Columns: {list}]
- [ ] [Row count expectation]

Success Criteria:
- [ ] [Testable condition 1]
- [ ] [Testable condition 2]
```

---

## That's It!

You have all the context you need. Execute per your phase. When stuck, consult the reference docs above and the assumption register at `docs/assumptions_register.md`.

**Go build.** 🚀
