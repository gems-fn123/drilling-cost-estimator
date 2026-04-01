# WBS Lv.5 Classification Rulebook

## Rule Table
- `R1_TAG_WELL`: if `Tag_Well_or_Pad == Well` → `well_tied`, high confidence.
- `R2_TAG_PAD`: if `Tag_Well_or_Pad == Pad` → `campaign_tied`, high confidence.
- `R3_KEYWORD_CAMPAIGN`: campaign/shared keywords in Lv4/Lv5 labels → `campaign_tied`, medium confidence, review required.
- `R4_KEYWORD_WELL`: well-operation keywords in Lv4/Lv5 labels → `well_tied`, medium confidence, review required.
- `R5_FALLBACK_HYBRID`: default when deterministic evidence is absent → `hybrid`, low confidence, review required.

## Exceptions / Known Limitations
- Data.Summary provides campaign/WBS grain with limited explicit well linkage per cost row.
- Event code and NPT class are preserved as explicit nullable fields in this phase.
- All non-tag-based rules are automatically routed to the review queue.
