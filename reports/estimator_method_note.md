# Estimator Method Note (Phase 5)

## Active branch
- Method branch: **grouped benchmark fallback**.
- Reason: current processed package supports deterministic/quantile benchmarking by field and classification; regression sufficiency evidence is not yet packaged for release.

## Estimation decomposition
Campaign total is decomposed into:
1. well-tied component,
2. hybrid component,
3. campaign-tied component.

Each component is estimated in-field (`DARAJAT` and `SALAK` separated), then allocated to WBS Lv.5 detail rows using in-field support weights.

## Uncertainty
- Uncertainty label: `MAPE_proxy_grouped_benchmark`.
- Interval basis: quantile band (`P10/P90`) from grouped historical baselines.

## Integrity checks
- Detail WBS sum is reconciled to campaign total within strict tolerance.
- Audit package captures runtime toggles, external fallback behavior, source references, and synthetic-row usage.
