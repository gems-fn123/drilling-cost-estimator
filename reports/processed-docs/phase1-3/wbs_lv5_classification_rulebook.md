# WBS Lv.5 Driver Alignment Rulebook

## Rule Order
1. `R0_CAMPAIGN_MAPPING_GATE`: resolve `DRJ 2022`, `DRJ 2023`, and `SLK 2025` to official campaign codes before any class assignment.
2. `R1_DICT_WELL_TAG`: explicit dictionary `Tag_Well_or_Pad=Well` -> `well_tied` with `driver_family=well_scope`.
3. `R2_POLICY_*`: curated family policy table splits non-well scope into `campaign_tied` versus `hybrid` using WBS family/subfamily meaning.
4. `R4/R5/R6_KEYWORD_*`: deterministic keyword fallback is allowed only after curated policy lookup.
5. `R9_REVIEW_REQUIRED`: unresolved items remain in review; missing evidence never defaults to `hybrid`.

## Hybrid Semantics
- `hybrid` means non-well cost that is estimable from structured campaign design/scope drivers such as pad expansion, tie-in scope, interpad moves, or rig skid count.
- `hybrid` is **not** a placeholder for unknown scope.

## Curated Policy Families
- `P001` priority 10: `tag=Pad` / `family=Engineering` / `label_contains=Tie In` -> `hybrid` (`tie_in_flag`)
- `P002` priority 11: `tag=Pad` / `family=Material - LL` / `label_contains=Tie In` -> `hybrid` (`tie_in_flag`)
- `P003` priority 12: `tag=Pad` / `family=Material - Non LL` / `label_contains=Tie In` -> `hybrid` (`tie_in_flag`)
- `P004` priority 13: `tag=Pad` / `family=Installation, Hook Up & Pre-Commisioning` / `label_contains=*` -> `hybrid` (`tie_in_flag`)
- `P005` priority 20: `tag=Pad` / `family=Construction` / `label_contains=*` -> `hybrid` (`pad_expansion_flag`)
- `P006` priority 21: `tag=Pad` / `family=Engineering` / `label_contains=*` -> `hybrid` (`pad_expansion_flag`)
- `P007` priority 22: `tag=Pad` / `family=Material - LL` / `label_contains=*` -> `hybrid` (`pad_expansion_flag`)
- `P008` priority 23: `tag=Pad` / `family=Material - Non LL` / `label_contains=*` -> `hybrid` (`pad_expansion_flag`)
- `P009` priority 24: `tag=*` / `family=New Rig Pavement` / `label_contains=*` -> `hybrid` (`pad_expansion_flag`)
- `P010` priority 30: `tag=*` / `family=Rig Move` / `label_contains=*` -> `hybrid` (`interpad_move_count`)
- `P011` priority 31: `tag=*` / `family=Rig Skid` / `label_contains=*` -> `hybrid` (`rig_skid_count`)
- `P012` priority 40: `tag=*` / `family=Rig Mobilization` / `label_contains=*` -> `campaign_tied` (`campaign_logistics`)
- `P013` priority 50: `tag=*` / `family=Andalalin` / `label_contains=*` -> `campaign_tied` (`campaign_compliance`)
- `P014` priority 51: `tag=*` / `family=Contingency` / `label_contains=*` -> `campaign_tied` (`shared_support`)
- `P015` priority 52: `tag=*` / `family=Drill Cutting - Transport & Process` / `label_contains=*` -> `campaign_tied` (`waste_support`)
- `P016` priority 53: `tag=*` / `family=Drilling Facilities Support` / `label_contains=*` -> `campaign_tied` (`shared_support`)
- `P017` priority 54: `tag=*` / `family=Drilling Operation Water Support` / `label_contains=*` -> `campaign_tied` (`shared_support`)
- `P018` priority 55: `tag=*` / `family=Environment Permit` / `label_contains=*` -> `campaign_tied` (`campaign_compliance`)
- `P019` priority 56: `tag=*` / `family=Environmental Monitoring` / `label_contains=*` -> `campaign_tied` (`campaign_compliance`)
- `P020` priority 57: `tag=*` / `family=Hardware Supply` / `label_contains=*` -> `campaign_tied` (`shared_support`)
- `P021` priority 58: `tag=*` / `family=Hazardous Waste` / `label_contains=*` -> `campaign_tied` (`waste_support`)
- `P022` priority 59: `tag=*` / `family=Heavy Equipment for Drill Cutting` / `label_contains=*` -> `campaign_tied` (`waste_support`)
- `P023` priority 60: `tag=*` / `family=Internet and IT Support Service` / `label_contains=*` -> `campaign_tied` (`shared_support`)
- `P024` priority 61: `tag=*` / `family=IPAL` / `label_contains=*` -> `campaign_tied` (`campaign_compliance`)
- `P025` priority 62: `tag=*` / `family=LIH` / `label_contains=*` -> `campaign_tied` (`campaign_compliance`)
- `P026` priority 63: `tag=*` / `family=Permitting` / `label_contains=*` -> `campaign_tied` (`campaign_compliance`)
- `P027` priority 64: `tag=*` / `family=PGPA` / `label_contains=*` -> `campaign_tied` (`campaign_compliance`)
- `P028` priority 65: `tag=*` / `family=Project Management Cost` / `label_contains=*` -> `campaign_tied` (`shared_support`)
- `P029` priority 66: `tag=*` / `family=Sampling and Lab Analysis` / `label_contains=*` -> `campaign_tied` (`campaign_compliance`)
- `P030` priority 67: `tag=*` / `family=Security` / `label_contains=*` -> `campaign_tied` (`shared_support`)
- `P031` priority 80: `tag=*` / `family=API non API Machine Shop Service` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P032` priority 81: `tag=*` / `family=Bits, Reamer and Core heads` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P033` priority 82: `tag=*` / `family=Casing Installation` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P034` priority 83: `tag=*` / `family=Cement, Cementing & Pump Fees` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P035` priority 84: `tag=*` / `family=Contract Rig` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P036` priority 85: `tag=*` / `family=Coring` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P037` priority 86: `tag=*` / `family=Directional Drilling & Surveys` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P038` priority 87: `tag=*` / `family=Drilling Safety, Health & Environment` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P039` priority 88: `tag=*` / `family=Equipment Rental` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P040` priority 89: `tag=*` / `family=Explosive` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P041` priority 90: `tag=*` / `family=Explosive Handling & Permitting` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P042` priority 91: `tag=*` / `family=Land Transportation` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P043` priority 92: `tag=*` / `family=Logging Cost` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P044` priority 93: `tag=*` / `family=Material` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P045` priority 94: `tag=*` / `family=Mud Logging Service` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P046` priority 95: `tag=*` / `family=Mud, Chemical and Engineering Service` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P047` priority 96: `tag=*` / `family=NDT Inspection` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P048` priority 97: `tag=*` / `family=Open Hole Electrical Logging Service` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P049` priority 98: `tag=*` / `family=Other Transportation` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P050` priority 99: `tag=*` / `family=Rig Inspection` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P051` priority 100: `tag=*` / `family=Service` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P052` priority 101: `tag=*` / `family=Service Lines & Communication` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P053` priority 102: `tag=*` / `family=Supervision` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P054` priority 103: `tag=*` / `family=Vehicle Inspection` / `label_contains=*` -> `well_tied` (`well_scope`)
- `P055` priority 104: `tag=*` / `family=Welding Service` / `label_contains=*` -> `well_tied` (`well_scope`)

## Estimator Composition Freeze
- `campaign estimate = sum(well_tied well estimates) + campaign_tied campaign estimate + hybrid scope-based campaign estimate`.
- Usage flags are fixed as `well_tied -> direct + rollup_from_wells`, `campaign_tied -> exclude + direct_campaign`, `hybrid -> exclude + scope_scaled`.
