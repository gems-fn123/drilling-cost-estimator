---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
color: #1a1a2e
style: |
  section {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 28px;
  }
  section.title {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: #ffffff;
    text-align: center;
    justify-content: center;
    align-items: center;
  }
  section.title h1 {
    font-size: 52px;
    font-weight: 700;
    margin-bottom: 12px;
    color: #e94560;
  }
  section.title h2 {
    font-size: 26px;
    font-weight: 300;
    color: #a8b2d8;
  }
  section.section-header {
    background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
    color: #ffffff;
    justify-content: center;
    align-items: center;
  }
  section.section-header h1 {
    font-size: 44px;
    color: #e94560;
    text-align: center;
  }
  section.section-header p {
    color: #a8b2d8;
    font-size: 22px;
    text-align: center;
  }
  h1 { color: #0f3460; font-size: 36px; border-bottom: 3px solid #e94560; padding-bottom: 8px; }
  h2 { color: #16213e; font-size: 30px; }
  h3 { color: #0f3460; font-size: 24px; }
  .highlight { color: #e94560; font-weight: bold; }
  table { width: 100%; border-collapse: collapse; font-size: 22px; }
  th { background: #0f3460; color: #ffffff; padding: 10px 14px; text-align: left; }
  td { padding: 8px 14px; border-bottom: 1px solid #dde; }
  tr:nth-child(even) td { background: #f4f6fb; }
  blockquote { border-left: 5px solid #e94560; padding-left: 18px; color: #444; font-style: italic; }
  ul li { margin: 6px 0; }
  .columns { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
---

<!-- _class: title -->

# Drilling Cost Estimator
## C-Suite Final Project Update

**Geothermal Drilling Analytics Initiative**
May 2026

---

<!-- _class: section-header -->

# 01
# Project Overview & Motivation

*Why we built this — and what it solves*

---

# Project Overview

## The Business Problem

> Geothermal drilling costs are **multi-million dollar commitments** made on incomplete information — leading to budget overruns, planning gaps, and reactive decision-making.

### What We Set Out to Solve

- **No standardized estimation method** existed at Level 5 WBS granularity
- Historical cost data was **unstructured and uncategorised**
- Field teams relied on **expert intuition**, not reproducible models
- C-suite lacked **audit-ready cost forecasts**

---

# Motivation & Scope

## Level 5 WBS Cost Estimation

The Work Breakdown Structure (WBS) at **Level 5** is the most granular decomposition of drilling project costs — covering individual service lines, materials, and time-based activities.

| WBS Level | Description | Coverage |
|---|---|---|
| L1 | Project | Portfolio |
| L2 | Phase | Exploration / Development |
| L3 | Well Programme | Per-well |
| L4 | Activity | Drilling, Completion |
| **L5** | **Line Item** | **Service, Material, NPT** |

> **This project targets L5** — enabling bottom-up cost reconstruction and benchmark-to-actual variance tracking.

---

# Project Goals

## Four Pillars of Delivery

1. **📊 Data Foundation** — Clean, classified well-cost history across Darajat & Salak fields
2. **🔬 Statistical Validation** — Pearson correlation to identify true cost drivers
3. **🧮 Estimation Engine** — Formula-based model with field-specific calibration
4. **✅ Integrity Layer** — WBS reconciliation + audit package for governance

### Fields in Scope
- **Darajat** — Deeper wells, higher day-rate sensitivity
- **Salak** — Shallower profile, different cost structure

---

<!-- _class: section-header -->

# 02
# Data Clustering & Classification

*Decomposing the well portfolio into comparable groups*

---

# Well Decomposition Framework

## Three Structural Categories

Before any estimation can begin, every well in the historical dataset must be classified by its **operational and logistical relationship** to other wells and infrastructure.

```
Well Portfolio
├── Well-tied        → Standalone single-well operations
├── Hybrid           → Mixed characteristics (pad + tie-in)
└── Campaign-tied    → Multi-well programmes, shared mobilisation
```

> This decomposition is critical — mixing well types without classification **inflates variance** and destroys estimation accuracy.

---

# Decomposition Types — Detail

| Type | Definition | Cost Implication |
|---|---|---|
| **Well-tied** | Single well, independent mobilisation | Full mob/demob cost; no shared spread |
| **Hybrid** | Shares some infrastructure but not fully campaign | Partial cost allocation; requires splitting |
| **Campaign-tied** | Multi-well campaign, shared rig & crew | Costs amortised across well count |

### Why It Matters for Estimation
- Campaign wells **cannot** be benchmarked against standalone wells
- Hybrid wells require **semantic disambiguation** before assignment
- Misclassification → wrong benchmark peer group → bad estimate

---

# Classification Rulebook: R0–R9

## Logic Flow Overview

| Rule | Trigger Condition | Classification Outcome |
|---|---|---|
| **R0** | No AFE linkage; isolated well record | Well-tied (Standalone) |
| **R1** | Single AFE, single well | Well-tied (Confirmed) |
| **R2** | Shared AFE across ≥2 wells, sequential spud | Campaign-tied |
| **R3** | Shared rig, overlapping dates, different AFEs | Campaign-tied (Inferred) |
| **R4** | Pad location flag + unique AFE | Hybrid (Pad Expansion) |
| **R5** | Surface tie-in noted, no new pad | Hybrid (Tie-in) |
| **R6** | Campaign flag + pad location | Campaign-tied (override) |
| **R7** | Missing location data; cost outlier | Flagged for Manual Review |
| **R8** | Recompletion / sidetrack on existing wellbore | Well-tied (Modified) |
| **R9** | Data conflict between rules | Escalate to Data Steward |

---

# Hybrid Semantics

## Two Distinct Hybrid Sub-Types

### 🔵 Pad Expansion
- New well drilled from an **existing pad location**
- Shares surface casing, conductor, and location preparation costs
- **Cost split**: Surface civil works allocated to the pad; subsurface to the individual well

### 🟠 Tie-ins
- New wellbore **tied into existing gathering system or manifold**
- Surface flowline, valve train, and hookup costs are shared
- **Cost split**: Hookup allocated by metre of flowline; wellbore costs standalone

> Correct hybrid semantics prevents **double-counting** and ensures per-well unit costs are comparable across the portfolio.

---

<!-- _class: section-header -->

# 03
# Pearson's Correlation Results

*What actually drives drilling costs — the data speaks*

---

# Why Pearson's Correlation?

## Validation Before Modelling

Before committing to any cost driver in the estimation formula, we ran **Pearson's r** across all candidate variables against total well cost.

### Variables Tested
- Operational: Days drilled, Total Depth (TVD/MD), Well complexity
- Economic: Brent crude price, CPI index, Steel price index
- Operational context: Rig type, formation difficulty, NPT hours

> **Pearson's r** measures linear correlation: values closer to ±1.0 indicate strong predictive relationships. Threshold for inclusion: **|r| ≥ 0.60**

---

# Primary Drivers: Days vs. Depth

## Headline Findings

| Variable | Darajat r | Salak r | Interpretation |
|---|---|---|---|
| **Days Drilled** | **0.89** | **0.80** | 🔴 Strong — primary driver |
| Total Depth (TVD) | 0.61 | 0.44 | 🟡 Mixed — field-dependent |
| MD/TVD Ratio | 0.38 | 0.52 | 🟢 Moderate in Salak only |
| NPT Hours | 0.71 | 0.68 | 🔴 Consistent — secondary driver |
| Complexity Score | 0.65 | 0.63 | 🟡 Consistent moderate |

### Key Insight
> **Drilling days** is the dominant cost driver in both fields. Depth matters — but only after field type is controlled for. This validates a **service-time-first** estimation approach.

---

# Macro Economic Correlations

## External Factors: Brent, CPI, Steel

| Macro Variable | Portfolio r | Lag (months) | Significance |
|---|---|---|---|
| **Brent Crude (USD/bbl)** | 0.73 | 3–6 months | ✅ Significant |
| **CPI (Indonesia)** | 0.58 | 6–9 months | ✅ Moderate |
| **Steel Price Index** | 0.67 | 0–3 months | ✅ Significant |
| USD/IDR Exchange Rate | 0.41 | 1–3 months | ⚠️ Weak |

### Implications for the Model
- Brent and steel prices should be used as **escalation indices**, not direct inputs
- CPI lag suggests **contract renewal cycles** absorb some macro volatility
- Macro adjustments will be applied as **annual index multipliers** on base estimates

---

# Field-Specific Insights

## Darajat vs. Salak — Divergent Profiles

### Darajat
- Deeper wells (avg. 2,400m MD) → **depth coefficient matters more**
- Days correlation **r = 0.89**: day-rate exposure is the #1 risk
- High-temperature formations drive **NPT** via mud losses and bit wear
- 📌 *Days are expensive because formations are punishing*

### Salak
- Shallower wells (avg. 1,800m MD) → depth less variable
- Days correlation **r = 0.80**: still dominant but less extreme
- More predictable geology → NPT is **more plannable** at Salak
- 📌 *Cost predictability is higher; depth variation matters relatively more*

> The two fields require **separate coefficient sets** — a unified model would introduce systematic bias.

---

<!-- _class: section-header -->

# 04
# Estimation Algorithm

*The model — how we build a defensible cost estimate*

---

# Algorithm Architecture

## Active Branch: Grouped Benchmark Fallback

The estimation engine uses a **three-tier resolution strategy**:

```
Estimate Request
        │
        ▼
 ┌─────────────────────┐
 │ Tier 1: Direct Match │  ← Same field, same well type, same year band
 └────────┬────────────┘
          │ No match?
          ▼
 ┌──────────────────────────┐
 │ Tier 2: Grouped Benchmark │  ← Same field, same type, adjacent years ✅ ACTIVE
 └────────┬─────────────────┘
          │ No match?
          ▼
 ┌──────────────────────────┐
 │ Tier 3: Formula Fallback  │  ← Regression formula, field coefficients
 └──────────────────────────┘
```

> **Tier 2 (Grouped Benchmark Fallback)** is the primary active branch — balancing specificity with data availability.

---

# The Estimation Formula

## Four-Component Cost Model

$$\boxed{C_{total} = C_{service} + C_{material} + C_{NPT} + C_{complexity}}$$

### Component Definitions

| Component | Formula | Description |
|---|---|---|
| **C_service** | `days × rate_day` | Time-based rig & service costs |
| **C_material** | `depth × rate_ft` | Casing, cement, mud per foot |
| **C_NPT** | `npt_hours × rate_npt` | Non-productive time exposure |
| **C_complexity** | `base × complexity_factor` | Well design complexity premium |

> All four components are **independently auditable** and map directly to WBS L5 line items.

---

# Field-Specific Coefficients

## Calibrated from Historical Data (2018–2024)

### Darajat Coefficients

| Coefficient | Value | Basis |
|---|---|---|
| Day Rate (`rate_day`) | **$119,000 / day** | Weighted avg, rig + services |
| Depth Rate (`rate_ft`) | **$190 / ft MD** | Casing + cement + mud benchmark |
| NPT Rate | $42,000 / hr | Historical NPT cost distribution |
| Complexity Factor | 1.0 – 1.35× | Based on well design score |

### Salak Coefficients

| Coefficient | Value | Basis |
|---|---|---|
| Day Rate (`rate_day`) | **$155,000 / day** | Higher service density at surface |
| Depth Rate (`rate_ft`) | **$135 / ft MD** | Shallower = less casing strings |
| NPT Rate | $38,000 / hr | Lower formation-driven NPT |
| Complexity Factor | 1.0 – 1.28× | Shallower wells, less variability |

---

# Coefficient Rationale

## Why Salak Has a Higher Day Rate

> Counter-intuitive: Salak is shallower, yet day rate is **$36k/day higher** than Darajat.

### Explanation
1. **Service density** at Salak surface operations is higher — more simultaneous service lines
2. **Completions complexity** at Salak wellheads involves more valve trains and instrumentation
3. **Rig standby** is more frequent during pad tie-in operations, increasing billable idle time

### Depth Rate Inversion
- Darajat's **$190/ft** reflects deep high-temperature casing programmes (4–5 strings)
- Salak's **$135/ft** reflects fewer casing strings in shallower, more predictable geology

> This field divergence is **exactly why a single unified model fails** — and why we built field-specific calibration.

---

<!-- _class: section-header -->

# 05
# Integrity & Quality

*Making estimates auditable, reconcilable, and defensible*

---

# WBS Reconciliation

## Closing the Loop: Estimate → Actual → Variance

The estimation output is **fully reconciled** against the WBS cost structure at L5 granularity.

### Reconciliation Workflow

```
AFE Estimate (L5)
      │
      ▼
  Actuals Capture (SAP / Cost System)
      │
      ▼
  WBS Reconciliation Engine
      │
      ├─ Line-item match: ✅ Reconciled
      ├─ Variance > 15%: ⚠️ Flagged for review
      └─ Missing line item: 🔴 Escalation required
      │
      ▼
  Variance Report (per well, per phase, portfolio)
```

> **No estimate is considered final** until WBS reconciliation confirms all L5 codes are populated and balanced.

---

# Audit Package Features

## What Ships with Every Estimate

Each estimate generated by the system produces a **self-contained audit package**:

| Feature | Description |
|---|---|
| 📄 **Estimate Trace** | Full calculation trail: inputs → components → total |
| 📊 **Peer Benchmark Report** | Which historical wells were used as comparators |
| 🔢 **Coefficient Snapshot** | Coefficient version and calibration date used |
| 📈 **Sensitivity Analysis** | ±10% / ±20% variation on days and depth |
| 🗂️ **WBS Mapping Table** | Every cost line mapped to L5 WBS code |
| 📋 **Classification Evidence** | R-rule applied, evidence record, override log |
| ✍️ **Reviewer Sign-off** | Digital approval workflow with timestamp |

> The audit package satisfies **SOX-adjacent controls** and supports JV partner review requests without additional manual preparation.

---

# Data Quality Metrics

## Current State of the Historical Dataset

| Metric | Value | Target |
|---|---|---|
| Wells fully classified (R0–R9) | **94%** | 100% |
| L5 WBS completeness | **87%** | 95% |
| Actuals reconciled to estimate | **91%** | 95% |
| Macro index linkage coverage | **100%** | 100% |
| Peer benchmark availability | **96%** | 98% |

### Remaining 6% Unclassified Wells
- Primarily pre-2015 wells with incomplete AFE documentation
- Being resolved via **manual data archaeology** with field records
- Expected completion: **Q3 2026**

---

<!-- _class: section-header -->

# 06
# Roadmap & Next Steps

*From prototype to production — the path forward*

---

# Immediate Next Steps (Q2–Q3 2026)

## 90-Day Action Plan

| Priority | Action | Owner | Target |
|---|---|---|---|
| 🔴 **P1** | Complete classification of pre-2015 wells | Data Engineering | Jul 2026 |
| 🔴 **P1** | L5 WBS completeness to 95% target | Cost Engineering | Jul 2026 |
| 🟡 **P2** | Integrate Brent/Steel live index feed | IT / Analytics | Aug 2026 |
| 🟡 **P2** | Deploy audit package to SharePoint | IT / Cost Eng | Aug 2026 |
| 🟢 **P3** | Field calibration review (annual) | Drilling Eng | Sep 2026 |
| 🟢 **P3** | Expand to Wayang Windu field | Analytics | Oct 2026 |

---

# Medium-Term Roadmap (Q4 2026 – Q2 2027)

## Building Toward Predictive Capability

### Phase 3: Production Deployment
- Full integration with **SAP PM / Cost Management** for live actuals feed
- Automated **AFE pre-population** from estimation engine outputs
- Monthly **coefficient refresh** cycle based on rolling 24-month actuals

### Phase 4: Predictive Extension
- Machine learning layer on top of correlation baseline (Random Forest / XGBoost)
- **Real-time NPT probability scoring** using formation prognosis inputs
- Portfolio-level **Monte Carlo simulation** for AFE contingency setting

### Phase 5: Multi-Field Standardisation
- Extend classification rulebook to all Pertamina Geothermal fields
- Unified cross-field benchmarking with **field adjustment factors**

---

# Business Value Summary

## What This Delivers to the Organisation

| Value Driver | Current State | With Estimator |
|---|---|---|
| **Estimate preparation time** | 3–5 days | < 4 hours |
| **Estimate accuracy (P50)** | ±25–35% | **±12–18%** |
| **Audit readiness** | Manual, weeks | Automated, same day |
| **Benchmark availability** | Ad hoc, inconsistent | Structured, versioned |
| **JV partner confidence** | Low (no audit trail) | High (full trace) |
| **Contingency setting** | Gut-feel % | Data-driven sensitivity |

> **Estimated annual value**: Improved cost predictability on a $150M+ annual drilling programme represents **$8–15M in reduced contingency waste** and planning efficiency gains.

---

# Risk & Mitigation

## Known Risks to Monitor

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Coefficient drift (macro shocks) | Medium | High | Annual recalibration + index linkage |
| New well type not in rulebook | Low | Medium | R9 escalation path + quarterly review |
| Data quality regression | Low | High | Automated completeness monitoring |
| Model over-reliance (black box risk) | Medium | Medium | Full trace audit package + reviewer sign-off |
| Field expansion data gaps | Medium | Medium | Phased rollout with data readiness gate |

---

<!-- _class: title -->

# Summary

## Drilling Cost Estimator — Delivered

- ✅ **Classified** historical well portfolio with R0–R9 rulebook
- ✅ **Validated** cost drivers via Pearson's correlation
- ✅ **Calibrated** field-specific estimation formula (Darajat & Salak)
- ✅ **Built** audit-ready WBS reconciliation package
- 🚀 **Next**: Production integration & predictive layer

---

*Thank you*

**Questions & Discussion**

---
*Drilling Cost Estimator | C-Suite Final Update | May 2026*
*Geothermal Drilling Analytics — Confidential*