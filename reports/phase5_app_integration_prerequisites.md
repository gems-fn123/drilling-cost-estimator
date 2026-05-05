# Phase 5 App Integration Prerequisites

Date: 2026-05-05

## Output Contract
- Source artifact: `data/processed/phase5_app_dataset.csv`
- Required columns: `field, group_key, classification, driver_family, sample_size, cost_median, cost_p10, cost_p90, confidence_tier, estimator_readiness`
- Field-specific behavior: app filters are hard-partitioned by `field` so DARAJAT and SALAK are never pooled.

## UI Prerequisites
1. Field selector defaults to a single field per session.
2. Group table sorts by `group_key` and shows P10/P50/P90 cost bands.
3. Confidence indicator maps `confidence_tier` to badge colors.
4. Records with `estimator_readiness != ready` remain visible but marked as watchlist.

## Snapshot
- Fields in current dataset: DARAJAT, SALAK
- Total app rows: 119
