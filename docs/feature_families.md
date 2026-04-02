# Feature Families

## Purpose
This document is the Phase 2 Define reference for feature families used by the current Level-5 alignment layer. It records intended estimator features, source-sheet lineage, and whether each family is already populated in the current repository outputs.

## Authority
- Gate authority remains [docs/PROJECT_INSTRUCTION.md](PROJECT_INSTRUCTION.md).
- Implemented row-grain contract: `data/processed/wbs_lv5_master.csv`
- Implemented classification contract: `data/processed/wbs_lv5_classification.csv`

## Feature Families
| family | intended use | source workbook / sheet | source columns or logic | current status |
|---|---|---|---|---|
| `depth` | Future well-level drilling cost intensity and section-length drivers | `20260327_WBS_Data.xlsx` / `4. Depth.vs.Days.History`, `5. Well.Size.Data`, `Cost & Technical Data` | Depth and section attributes are expected to be sourced from well-history / well-size sheets, then joined through canonical well mapping | Defined for later enrichment; not populated in `wbs_lv5_master.csv` |
| `section` | Surface / intermediate / production section segmentation | `20260327_WBS_Data.xlsx` / `Cost & Technical Data`, `5. Well.Size.Data` | Derived from section-related technical fields after well-level canonicalization | Defined for later enrichment; not populated in `wbs_lv5_master.csv` |
| `operation_type` | Distinguish direct well operations from campaign support and structured scope | `20260318_WBS_Dictionary.xlsx` / `WBS_Dictionary`, `20260327_WBS_Data.xlsx` / `Data.Summary` | Uses `Tag_Well_or_Pad`, `Tag_LVL5`, WBS path fields, and curated policy logic | Implemented through `classification`, `driver_family`, `tag_well_or_pad`, and `tag_lvl5` |
| `npt_unscheduled_event` | Future unscheduled-event / NPT driver enrichment | `UNSCHEDULED EVENT CODE.xlsx` / `Sheet1` and `20260327_WBS_Data.xlsx` / `3. NPT.Data` | Controlled vocabulary exists, but current Lv5 cost rows do not have a row-addressable join back to event records | Defined, but `event_code_raw`, `event_code_desc`, and `npt_class` remain blank in the current Lv5 master |
| `campaign_context` | Campaign identity, field separation, scope eligibility, and structured campaign flags | `20260327_WBS_Data.xlsx` / `Data.Summary`, `Drilled.Well`; `data/processed/canonical_campaign_mapping.csv` | Uses campaign-label alias mapping, official campaign codes, field-specific scope rules, and estimator inclusion flags | Implemented through `campaign_code`, `campaign_canonical`, `campaign_scope`, `field`, and classification usage flags |

## Notes
- `hybrid` is reserved for non-well scope that can be estimated from structured campaign design counts or flags such as `pad_expansion_flag`, `tie_in_flag`, `interpad_move_count`, and `rig_skid_count`.
- `well_tied`, `campaign_tied`, and `hybrid` are implemented in `data/processed/wbs_lv5_classification.csv`.
- The current Define layer is audit-ready for hierarchy and campaign mapping, but not yet enriched enough for event-coded or direct well-attributed Lv5 modeling.
