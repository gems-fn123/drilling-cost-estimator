# WBS Lv.5 Classification QA Report

## Processing Coverage
- Total source rows processed (Lv.5-only from Data.Summary): **822**
- Total cost processed (USD): **106,558,960.11**
- Total unique Lv.5 classification keys: **822**
- Unmapped campaign rows: **241**
- Unmapped well rows: **822** (not available at source grain)

## Classification Mix (Count + Spend)
- `well_tied`: 524 keys (63.7470%), USD 61,040,913.16 (57.2837%)
- `campaign_tied`: 99 keys (12.0438%), USD 8,914,609.06 (8.3659%)
- `hybrid`: 199 keys (24.2092%), USD 36,603,437.89 (34.3504%)

## Uncertainty / Review
- Low-confidence keys: **199**
- Keys requiring review: **199**

## Top Ambiguous Items by Spend
- `SALAK|E540-30101-D245401|E540-3010169-D245401|E540-301016903-D245401|E540-30101690306-D245401` | suggested `hybrid` | USD 2,472,778.98
- `DARAJAT|E530-30101-D235301|E530-3010169-D235301|E530-301016903-D235301|E530-30101690306-D235301` | suggested `hybrid` | USD 2,443,898.79
- `DARAJAT|E530-30101-D225301|E530-3010169-D225301|E530-301016966-D225301|E530-30101696623-D225301` | suggested `hybrid` | USD 2,200,569.61
- `DARAJAT|E530-30101-D235301|E530-3010169-D235301|E530-301016967-D235301|E530-30101696706-D235301` | suggested `hybrid` | USD 1,041,966.78
- `DARAJAT|E530-30101-D225301|E530-3010104-D225301|E530-301010402-D225301|E530-30101040205-D225301` | suggested `hybrid` | USD 1,033,044.74
- `DARAJAT|E530-30101-D225301|E530-3010105-D225301|E530-301010502-D225301|E530-30101050205-D225301` | suggested `hybrid` | USD 867,517.38
- `DARAJAT|E530-30101-D225301|E530-3010103-D225301|E530-301010302-D225301|E530-30101030205-D225301` | suggested `hybrid` | USD 838,855.14
- `SALAK|E540-30101-D245401|E540-3010156-D245401|E540-301015601-D245401|E540-30101560123-D245401` | suggested `hybrid` | USD 830,091.90
- `DARAJAT|E530-30101-D225301|E530-3010101-D225301|E530-301010102-D225301|E530-30101010205-D225301` | suggested `hybrid` | USD 821,879.00
- `DARAJAT|E530-30101-D225301|E530-3010105-D225301|E530-301010502-D225301|E530-30101050209-D225301` | suggested `hybrid` | USD 798,979.46

## Notes on Inconsistent Behavior
- In this phase, inconsistency is proxied by absence of deterministic tag evidence, routed to `needs_review`.
- No hidden allocations were applied for campaign/hybrid classes.
