# WBS Lv.5 Driver Alignment Report

## Snapshot
- This run treats `20260422_Data for Dashboard.xlsx` as the frozen source snapshot for driver alignment.
- Total Lv.5 source rows processed: **848**
- Total cost processed (USD): **176,613,592.01**

## Structured Cost Level Profile (pre-filter)
- Level `05`: **848** rows
- Lv.5 ingestion filter: keep only `WBS_Level=05` rows (dashboard normalized).

## Campaign Mapping Gate
- In-scope campaign rows mapped: **646 / 848**
- In-scope labels are required to resolve before class assignment.

## Approved Driver Mix
- `well_tied`: 72 keys (50.0000%), USD 124,045,169.25 (70.2353%)
- `campaign_tied`: 42 keys (29.1667%), USD 23,017,907.87 (13.0329%)
- `hybrid`: 30 keys (20.8333%), USD 29,550,514.89 (16.7317%)

## By Field
- **DARAJAT**
  `well_tied`: 35 keys (49.2958%), USD 76,544,423.66 (69.5605%)
  `campaign_tied`: 21 keys (29.5775%), USD 14,264,220.43 (12.9628%)
  `hybrid`: 15 keys (21.1268%), USD 19,231,374.61 (17.4767%)
- **SALAK**
  `well_tied`: 37 keys (50.6849%), USD 47,500,745.59 (71.3508%)
  `campaign_tied`: 21 keys (28.7671%), USD 8,753,687.44 (13.1489%)
  `hybrid`: 15 keys (20.5479%), USD 10,319,140.28 (15.5004%)

## Review Status
- Unresolved keys: **7**
- Material review keys (>= USD 500,000): **59**

## Material Review List
- `DARAJAT|Drilling Cost|Well Cost|Services|Contract Rig` | `well_tied` | `well_scope` | USD 15,297,336.06
- `DARAJAT|Drilling Cost|Rig Mobilization|Rig Mobilization|Rig Mobilization` | `campaign_tied` | `campaign_logistics` | USD 9,280,285.77
- `DARAJAT|Drilling Cost|Well Cost|Services|Cement, Cementing & Pump Fees` | `well_tied` | `well_scope` | USD 8,564,060.02
- `DARAJAT|Drilling Cost|Well Cost|Services|Mud, Chemical and Engineering Service` | `well_tied` | `well_scope` | USD 7,513,359.76
- `DARAJAT|Drilling Cost|Well Cost|Material - LL|Casing` | `well_tied` | `well_scope` | USD 7,271,791.03
- `SALAK|Drilling Cost|Well Cost|Material - LL|Casing` | `well_tied` | `well_scope` | USD 6,982,930.33
- `DARAJAT|Drilling Cost|Well Cost|Services|Directional Drilling & Surveys` | `well_tied` | `well_scope` | USD 6,532,895.17
- `DARAJAT|Drilling Cost|Well Cost|Material - LL|Fuel & Lubricants` | `well_tied` | `well_scope` | USD 5,990,691.93
- `SALAK|Drilling Cost|Well Cost|Services|Cement, Cementing & Pump Fees` | `well_tied` | `well_scope` | USD 5,875,073.33
- `SALAK|Drilling Cost|Well Cost|Services|Contract Rig` | `well_tied` | `well_scope` | USD 5,771,257.57
- `DARAJAT|Drilling Cost|Well Cost|Services|Equipment Rental` | `well_tied` | `well_scope` | USD 5,622,229.63
- `SALAK|Drilling Cost|Rig Mobilization|Rig Mobilization|Rig Mobilization` | `campaign_tied` | `campaign_logistics` | USD 4,562,375.13
- `DARAJAT|Drilling Cost|Rig Move|Interpad Move|Rig Move` | `hybrid` | `interpad_move_count` | USD 4,511,425.44
- `DARAJAT|Surface Facilities Cost|Tie-in|Construction|Installation, Hook Up & Pre-Commisioning` | `hybrid` | `tie_in_flag` | USD 4,298,881.38
- `SALAK|Drilling Cost|Well Cost|Services|Mud, Chemical and Engineering Service` | `well_tied` | `well_scope` | USD 3,773,120.96
- `SALAK|Drilling Cost|Well Cost|Services|Directional Drilling & Surveys` | `well_tied` | `well_scope` | USD 3,690,678.63
- `SALAK|Drilling Cost|Well Cost|Services|Equipment Rental` | `well_tied` | `well_scope` | USD 3,617,368.42
- `DARAJAT|Surface Facilities Cost|Tie-in|Procurement|Material - LL` | `hybrid` | `pad_expansion_flag` | USD 3,580,812.67
- `SALAK|Drilling Cost|Well Cost|Services|Drilling Rig O&M` | `well_tied` | `well_scope` | USD 3,415,573.27
- `DARAJAT|Drilling Cost|Well Cost|Material - LL|Equipment Rental` | `well_tied` | `well_scope` | USD 2,882,722.15
- `SALAK|Drilling Cost|Rig Move|Interpad Move|Rig Move` | `hybrid` | `interpad_move_count` | USD 2,707,345.06
- `DARAJAT|Drilling Cost|Well Cost|Services|Bits, Reamer and Core heads` | `well_tied` | `well_scope` | USD 2,687,536.76
- `SALAK|Drilling Cost|Well Cost|Material - LL|Fuel & Lubricants` | `well_tied` | `well_scope` | USD 2,623,304.29
- `DARAJAT|Surface Facilities Cost|Road & Pad|Construction|Construction` | `hybrid` | `pad_expansion_flag` | USD 2,298,677.05
- `SALAK|Surface Facilities Cost|Tie-in|Procurement|Material - LL` | `hybrid` | `pad_expansion_flag` | USD 2,114,871.90
- `DARAJAT|Surface Facilities Cost|Tie-in|Procurement|Material - Non LL` | `hybrid` | `pad_expansion_flag` | USD 1,717,743.15
- `SALAK|Drilling Cost|Well Cost|Services|Bits, Reamer and Core heads` | `well_tied` | `well_scope` | USD 1,716,541.00
- `SALAK|Drilling Cost|LIH|LIH|LIH` | `campaign_tied` | `campaign_compliance` | USD 1,531,986.77
- `DARAJAT|Support Cost|Drilling Operation Water Support|Drilling Operation Water Support|Drilling Operation Water Support` | `campaign_tied` | `shared_support` | USD 1,525,283.68
- `DARAJAT|Surface Facilities Cost|Special Requirement Existing Pad|Construction|Construction` | `hybrid` | `pad_expansion_flag` | USD 1,524,802.26
- `DARAJAT|Drilling Cost|Well Cost|Services|Supervision` | `well_tied` | `well_scope` | USD 1,492,890.61
- `DARAJAT|Drilling Cost|Well Cost|Services|Land Transportation` | `well_tied` | `well_scope` | USD 1,477,042.52
- `SALAK|Surface Facilities Cost|Road & Pad|Construction|Construction` | `hybrid` | `pad_expansion_flag` | USD 1,441,148.15
- `SALAK|Drilling Cost|Well Cost|Services|Others` | `well_tied` | `well_scope` | USD 1,353,239.20
- `SALAK|Surface Facilities Cost|Tie-in|Construction|Installation, Hook Up & Pre-Commisioning` | `hybrid` | `tie_in_flag` | USD 1,271,679.00
- `DARAJAT|Support Cost|Well Testing|Well Testing|Well Testing` | `well_tied` | `well_scope` | USD 1,225,274.80
- `DARAJAT|Surface Facilities Cost|Conductor Casing Installation & Material|Services|Service` | `well_tied` | `well_scope` | USD 1,180,603.34
- `SALAK|Surface Facilities Cost|Conductor Casing Installation & Material|Conductor Casing Installation & Material|Service` | `well_tied` | `well_scope` | USD 1,165,594.54
- `DARAJAT|Drilling Cost|Well Cost|Services|Open Hole Electrical Logging Service` | `well_tied` | `well_scope` | USD 1,159,405.15
- `SALAK|Drilling Cost|Well Cost|Services|Land Transportation` | `well_tied` | `well_scope` | USD 1,072,971.95
- `DARAJAT|Drilling Cost|Well Cost|Services|Others` | `well_tied` | `well_scope` | USD 1,037,617.94
- `DARAJAT|Drilling Cost|Well Cost|Services|Casing Installation` | `well_tied` | `well_scope` | USD 980,527.67
- `SALAK|Drilling Cost|Well Cost|Material - LL|Well Equipment Surface` | `well_tied` | `well_scope` | USD 908,990.86
- `DARAJAT|Support Cost|SHE|Drill Cutting|Drill Cutting - Transport & Process` | `campaign_tied` | `waste_support` | USD 874,481.83
- `SALAK|Surface Facilities Cost|Conductor Casing Installation & Material|Service|Service` | `well_tied` | `well_scope` | USD 844,257.09
- `SALAK|Drilling Cost|Rig Move|Skid Moving|Rig Move` | `hybrid` | `interpad_move_count` | USD 830,091.90
- `DARAJAT|Surface Facilities Cost|Conductor Casing Installation & Material|Conductor Casing Installation & Material|Service` | `well_tied` | `well_scope` | USD 810,634.08
- `DARAJAT|Drilling Cost|Well Cost|Services|Mud Logging Service` | `well_tied` | `well_scope` | USD 780,452.75
- `SALAK|Support Cost|Well Testing|Well Testing|Well Testing` | `well_tied` | `well_scope` | USD 757,000.07
- `SALAK|Drilling Cost|Well Cost|Services|Casing Installation` | `well_tied` | `well_scope` | USD 749,329.10
- `DARAJAT|Support Cost|Well Insurance|Well Insurance|Insurance` | `campaign_tied` | `shared_support` | USD 727,056.04
- `DARAJAT|Support Cost|PGPA & Security|PGPA|PGPA` | `campaign_tied` | `campaign_compliance` | USD 718,108.13
- `SALAK|Drilling Cost|Rig Move|Services|Rig Move` | `hybrid` | `interpad_move_count` | USD 709,217.51
- `SALAK|Drilling Cost|Well Cost|Services|Supervision` | `well_tied` | `well_scope` | USD 705,895.95
- `SALAK|Surface Facilities Cost|Conductor Casing Installation & Material|Conductor Casing Installation & Material|Material` | `well_tied` | `well_scope` | USD 677,988.38
- `SALAK|Support Cost|SHE|Drill Cutting|Drill Cutting - Transport & Process` | `campaign_tied` | `waste_support` | USD 669,465.12
- `DARAJAT|Surface Facilities Cost|Conductor Casing Installation & Material|Conductor Casing Installation & Material|Material` | `well_tied` | `well_scope` | USD 579,209.10
- `DARAJAT|Drilling Cost|Well Cost|Services|API non API Machine Shop Service` | `well_tied` | `well_scope` | USD 574,372.14
- `DARAJAT|Surface Facilities Cost|Special Requirement Existing Pad|Procurement|Material - LL` | `hybrid` | `pad_expansion_flag` | USD 525,317.39

## Hybrid Driver Families
- `pad_expansion_flag`: 20 keys, USD 14,433,295.59
- `interpad_move_count`: 4 keys, USD 8,758,079.91
- `tie_in_flag`: 2 keys, USD 5,570,560.38
- `rig_skid_count`: 4 keys, USD 788,579.01

## Estimator Composition
- `campaign estimate = sum(well_tied well estimates) + campaign_tied campaign estimate + hybrid scope-based campaign estimate`.
- `well_tied` remains the only class eligible for direct well-level estimation in this layer.
- `campaign_tied` stays campaign-only.
- `hybrid` stays campaign-scope and is carried through design counts/flags rather than per-well allocation.
