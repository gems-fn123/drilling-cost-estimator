# Phase 5 Monitoring Skeleton

Date: 2026-04-24

## KPI Feed
- Source artifact: `data/processed/phase5_monitoring_kpis.csv`
- KPI fields: `kpi_ready_share_pct`, `kpi_avg_sample_size`, `kpi_hard_gate_failures`, `kpi_known_limitations`

## Alert Rules (initial)
1. Critical: `kpi_hard_gate_failures > 0`
2. Warning: `kpi_ready_share_pct < 60`
3. Warning: `kpi_known_limitations > 2`

## Current Snapshot
- DARAJAT: ready_share=72.13%, avg_sample=7.05, hard_gate_failures=0, known_limitations=2
- SALAK: ready_share=71.93%, avg_sample=5.16, hard_gate_failures=0, known_limitations=2
