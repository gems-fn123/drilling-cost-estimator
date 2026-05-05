# Phase 4 Plus Coverage Summary

## Before vs After (current run reference)
- populated `well_raw` rows before: **0** (historical pre-remediation baseline).
- populated `well_raw` rows after: **848 / 848**.
- populated `well_canonical` rows before: **0** (historical pre-remediation baseline).
- populated `well_canonical` rows after: **681 / 848**.
- rows mapped from direct `Well Name`: **681**.
- rows in `wbs_row_to_well_bridge.csv`: **848**.
- rows in `well_instance_event_context.csv`: **401**.

## Event mapping confidence tiers
- high: **270**
- medium: **0**
- low: **131**

## Deviation type counts (well context)
- standard: **33**
- redrill: **2**
- sidetrack: **2**
- multileg: **2**
- LIH_affected: **0**
- stuck_related: **0**
- unknown: **0**

## Notes
- `NPT.Data` (or legacy `3. NPT.Data` when present) is bridged as well-instance event context; direct row-level WBS event fill is not asserted.
- `event_code_raw` remains unchanged unless explicit row-level evidence exists.
