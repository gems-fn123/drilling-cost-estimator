from __future__ import annotations

import csv
import hashlib
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

POLICY_INPUT_PATH = ROOT / "src" / "cleaning" / "wbs_lv5_family_policy.csv"
CURATED_POLICY_OUTPUT_PATH = PROCESSED_DIR / "wbs_lv5_curated_policy.csv"

MASTER_PATH = PROCESSED_DIR / "wbs_lv5_master.csv"
CLASSIFICATION_PATH = PROCESSED_DIR / "wbs_lv5_classification.csv"
DRIVER_REFERENCE_PATH = PROCESSED_DIR / "wbs_lv5_driver_reference.csv"
REVIEW_QUEUE_PATH = PROCESSED_DIR / "wbs_lv5_review_queue.csv"
COST_SUMMARY_PATH = PROCESSED_DIR / "wbs_lv5_cost_summary_by_classification.csv"
FIELD_SUMMARY_PATH = PROCESSED_DIR / "wbs_lv5_cost_summary_by_field_and_classification.csv"
HYBRID_SCOPE_PATH = PROCESSED_DIR / "wbs_lv5_hybrid_tag_recommendation.csv"
RULE_COVERAGE_PATH = PROCESSED_DIR / "wbs_lv5_rule_coverage.csv"

INVENTORY_REPORT = REPORTS_DIR / "wbs_lv5_source_inventory.md"
RULEBOOK_REPORT = REPORTS_DIR / "wbs_lv5_classification_rulebook.md"
CLASSIFICATION_REPORT = REPORTS_DIR / "wbs_lv5_classification_report.md"
ALIGNMENT_REPORT = REPORTS_DIR / "wbs_lv5_driver_alignment_report.md"
DEFINE_QUALITY_REPORT = REPORTS_DIR / "phase2_define_quality_thresholds.md"

NS_MAIN = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_PKG = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}

MATERIAL_REVIEW_THRESHOLD = 500000.0

CAMPAIGN_LABEL_TO_CODE = {
    "DRJ 2022": "E530-30101-D225301",
    "DRJ 2023": "E530-30101-D235301",
    "SLK 2025": "E540-30101-D245401",
    "DARAJAT CAMPAIGN 2019": "E530-30101-D19001",
    "SALAK CAMPAIGN 2021": "E540-30101-D20001",
}

IN_SCOPE_CAMPAIGN_LABELS = {"DRJ 2022", "DRJ 2023", "SLK 2025"}
ALLOWED_CLASSES = {"well_tied", "campaign_tied", "hybrid"}
CLASS_ORDER = ["well_tied", "campaign_tied", "hybrid", "unresolved"]


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\n", " ")).strip()


def normalize_token(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(value).lower())


def col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def parse_float(value: str | None) -> float:
    text = clean_text(value).replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def read_xlsx(path: Path) -> dict[str, list[list[str]]]:
    sheets: dict[str, list[list[str]]] = {}
    with zipfile.ZipFile(path) as zf:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", NS_MAIN):
                shared_strings.append("".join(node.text or "" for node in item.findall(".//a:t", NS_MAIN)))

        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("p:Relationship", NS_PKG)}

        for sh in wb.findall("a:sheets/a:sheet", NS_MAIN):
            name = sh.attrib["name"]
            rel_id = sh.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = "xl/" + rel_map[rel_id].lstrip("/")
            root = ET.fromstring(zf.read(target))
            rows: list[list[str]] = []
            for row in root.findall("a:sheetData/a:row", NS_MAIN):
                values: dict[int, str] = {}
                for c in row.findall("a:c", NS_MAIN):
                    v = c.find("a:v", NS_MAIN)
                    if v is None:
                        continue
                    txt = v.text or ""
                    if c.attrib.get("t") == "s":
                        txt = shared_strings[int(txt)] if txt else ""
                    values[col_index(c.attrib["r"])] = clean_text(txt)
                if not values:
                    rows.append([])
                    continue
                dense = [""] * (max(values) + 1)
                for i, value in values.items():
                    dense[i] = value
                rows.append(dense)
            sheets[name] = rows
    return sheets


def find_header(rows: list[list[str]], required: list[str], lookahead: int = 40) -> tuple[int, dict[str, int]]:
    required_norm = [normalize_token(v) for v in required]
    for i, row in enumerate(rows[:lookahead]):
        norm = {normalize_token(c): j for j, c in enumerate(row) if normalize_token(c)}
        if all(req in norm for req in required_norm):
            return i, {required[k]: norm[required_norm[k]] for k in range(len(required))}
    raise ValueError(f"Header not found for required columns: {required}")


def sheet_to_records(rows: list[list[str]], required: list[str], optional: list[str] | None = None) -> list[dict[str, str]]:
    optional = optional or []
    header_idx, cols_required = find_header(rows, required)
    norm_to_idx = {normalize_token(v): i for i, v in enumerate(rows[header_idx]) if normalize_token(v)}
    cols_optional: dict[str, int] = {}
    for col in optional:
        key = normalize_token(col)
        if key in norm_to_idx:
            cols_optional[col] = norm_to_idx[key]

    records: list[dict[str, str]] = []
    for offset, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
        if not any(clean_text(c) for c in row):
            continue
        rec = {k: clean_text(row[idx]) if idx < len(row) else "" for k, idx in cols_required.items()}
        for k, idx in cols_optional.items():
            rec[k] = clean_text(row[idx]) if idx < len(row) else ""
        rec["_source_excel_row"] = str(offset)
        records.append(rec)
    return records


def map_field(asset_raw: str) -> str:
    value = clean_text(asset_raw).upper()
    if value in {"DRJ", "DARAJAT"}:
        return "DARAJAT"
    if value in {"SLK", "SALAK"}:
        return "SALAK"
    return value


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def build_inventory_note(workbooks: dict[str, dict[str, list[list[str]]]]) -> None:
    lines = [
        "# WBS Lv.5 Source Inventory",
        "",
        "## Scope",
        "Reviewed workbook structure and headers for the driver-alignment build.",
        "",
        "## Snapshot Freeze",
        "- This alignment run treats the current `data/raw/*.xlsx` workbook set as the frozen source snapshot.",
        "- Driver alignment remains a classification/reference task only; no statistical driver validation is performed in this layer.",
        "",
        "## Workbook / Sheet Inventory",
    ]

    for file_name, sheets in workbooks.items():
        lines.append(f"### `{file_name}`")
        for sheet_name in sorted(sheets):
            lines.append(f"- `{sheet_name}`: {len(sheets[sheet_name])} rows")
        lines.append("")

    lines.extend(
        [
            "## Authoritative Sources Used",
            "- **WBS hierarchy:** `20260318_WBS_Dictionary.xlsx` -> `WBS_Dictionary` (`LEVEL`, `LVL 1..5`, WBS tags).",
            "- **Cost rows:** `20260327_WBS_Data.xlsx` -> `Data.Summary` (`ACTUAL, USD`, WBS path fields).",
            "- **Campaign scope:** `data/processed/canonical_campaign_mapping.csv` plus explicit label aliases for `DRJ 2022`, `DRJ 2023`, and `SLK 2025`.",
            "- **Curated driver policy:** `src/cleaning/wbs_lv5_family_policy.csv`.",
            "",
            "## Data Quality Observations",
            "- `Data.Summary` contains multiple WBS levels; only rows with populated `L5` are used in this build.",
            "- Campaign labels in `Data.Summary` are short labels (`DRJ 2022`, `DRJ 2023`, `SLK 2025`), so driver alignment resolves them through explicit alias mapping before class assignment.",
            "- `hybrid` is reserved for non-well scope that is estimable from structured campaign design/scope drivers. Missing evidence no longer defaults to `hybrid`.",
            "",
            "## Join Candidates",
            "- Cost rows -> WBS dictionary via exact `WBS_ID` (`Data.Summary`) to `WBS CODE` (`WBS_Dictionary`).",
            "- Cost rows -> canonical campaign via label alias to official campaign code.",
            "- Well-level context remains nullable because `Data.Summary` is still campaign/WBS grain rather than row-level well attribution.",
        ]
    )
    write_text(INVENTORY_REPORT, "\n".join(lines) + "\n")


def load_policy_rows() -> list[dict[str, str]]:
    with POLICY_INPUT_PATH.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["policy_priority"] = str(int(clean_text(row.get("policy_priority", "999")) or "999"))
    return sorted(rows, key=lambda r: int(r["policy_priority"]))


def load_campaign_mappings() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    with (PROCESSED_DIR / "canonical_campaign_mapping.csv").open(encoding="utf-8") as fh:
        campaign_rows = list(csv.DictReader(fh))
    campaign_by_name = {normalize_token(r["campaign_name_raw"]): r for r in campaign_rows if clean_text(r.get("campaign_name_raw", ""))}
    campaign_by_code = {clean_text(r["campaign_code"]): r for r in campaign_rows if clean_text(r.get("campaign_code", ""))}
    return campaign_by_name, campaign_by_code


def resolve_campaign_mapping(campaign_raw: str, campaign_by_name: dict[str, dict[str, str]], campaign_by_code: dict[str, dict[str, str]]) -> tuple[dict[str, str], str]:
    raw_clean = clean_text(campaign_raw)
    alias_code = CAMPAIGN_LABEL_TO_CODE.get(raw_clean.upper(), "")
    if alias_code and alias_code in campaign_by_code:
        return campaign_by_code[alias_code], "campaign_label_alias"

    by_name = campaign_by_name.get(normalize_token(raw_clean))
    if by_name:
        return by_name, "campaign_name_raw"

    if raw_clean in campaign_by_code:
        return campaign_by_code[raw_clean], "campaign_code_raw"

    return {}, "unmapped"


def wildcard_match(expected: str, actual: str) -> bool:
    value = clean_text(expected)
    if value in {"", "*"}:
        return True
    return clean_text(actual).lower() == value.lower()


def contains_match(expected: str, actual: str) -> bool:
    value = clean_text(expected)
    if value in {"", "*"}:
        return True
    return value.lower() in clean_text(actual).lower()


def usage_flags_for_class(estimation_class: str) -> tuple[str, str]:
    if estimation_class == "well_tied":
        return "direct", "rollup_from_wells"
    if estimation_class == "campaign_tied":
        return "exclude", "direct_campaign"
    if estimation_class == "hybrid":
        return "exclude", "scope_scaled"
    return "exclude", "exclude"


def policy_match(row: dict[str, str], policy_rows: list[dict[str, str]]) -> dict[str, str] | None:
    for policy in policy_rows:
        if not wildcard_match(policy.get("tag_well_or_pad", "*"), row.get("tag_well_or_pad", "")):
            continue
        if not wildcard_match(policy.get("tag_lvl5", "*"), row.get("tag_lvl5", "")):
            continue
        if not contains_match(policy.get("label_contains", ""), row.get("wbs_label_raw", "")):
            continue
        return policy
    return None


def keyword_fallback(row: dict[str, str]) -> dict[str, str]:
    label_text = clean_text(row.get("wbs_label_raw", "")).lower()
    tag_text = clean_text(row.get("tag_lvl5", "")).lower()
    combined = f"{tag_text} {label_text}"

    if any(token in combined for token in ["skid moving", "rig skid"]):
        well_use, campaign_use = usage_flags_for_class("hybrid")
        return {
            "classification": "hybrid",
            "driver_family": "rig_skid_count",
            "classification_confidence": "medium",
            "classification_rule_id": "R4_KEYWORD_SCOPE_HYBRID",
            "classification_rule_text": "Skid-moving keywords indicate campaign scope that scales with rig skid count.",
            "well_estimation_use": well_use,
            "campaign_estimation_use": campaign_use,
            "review_status": "approved_keyword",
            "review_notes": "Approved via deterministic keyword fallback.",
        }

    if any(token in combined for token in ["interpad moving", "road & pad", "new rig pavement", "tie in", "hookup", "hook up", "pre-comm", "spec req"]):
        driver_family = "interpad_move_count" if "interpad moving" in combined else "pad_expansion_flag"
        if any(token in combined for token in ["tie in", "hookup", "hook up", "pre-comm"]):
            driver_family = "tie_in_flag"
        well_use, campaign_use = usage_flags_for_class("hybrid")
        return {
            "classification": "hybrid",
            "driver_family": driver_family,
            "classification_confidence": "medium",
            "classification_rule_id": "R4_KEYWORD_SCOPE_HYBRID",
            "classification_rule_text": "Structured scope keywords indicate non-well cost estimable from campaign design flags/counts.",
            "well_estimation_use": well_use,
            "campaign_estimation_use": campaign_use,
            "review_status": "approved_keyword",
            "review_notes": "Approved via deterministic keyword fallback.",
        }

    if any(token in combined for token in ["mobilization", "demobilization", "interfield move"]):
        well_use, campaign_use = usage_flags_for_class("campaign_tied")
        return {
            "classification": "campaign_tied",
            "driver_family": "campaign_logistics",
            "classification_confidence": "medium",
            "classification_rule_id": "R5_KEYWORD_CAMPAIGN_SUPPORT",
            "classification_rule_text": "Campaign-logistics keywords indicate shared campaign support scope.",
            "well_estimation_use": well_use,
            "campaign_estimation_use": campaign_use,
            "review_status": "approved_keyword",
            "review_notes": "Approved via deterministic keyword fallback.",
        }

    if any(token in combined for token in ["support", "security", "permit", "environment", "monitor", "hazardous", "drill cutting", "water support", "project management", "pgpa", "andalalin", "ipal", "lih", "contingency"]):
        driver_family = "campaign_compliance" if any(token in combined for token in ["permit", "environment", "monitor", "pgpa", "andalalin", "ipal", "lih"]) else "shared_support"
        if any(token in combined for token in ["hazardous", "drill cutting"]):
            driver_family = "waste_support"
        well_use, campaign_use = usage_flags_for_class("campaign_tied")
        return {
            "classification": "campaign_tied",
            "driver_family": driver_family,
            "classification_confidence": "medium",
            "classification_rule_id": "R5_KEYWORD_CAMPAIGN_SUPPORT",
            "classification_rule_text": "Shared-support/compliance keywords indicate campaign-tied scope.",
            "well_estimation_use": well_use,
            "campaign_estimation_use": campaign_use,
            "review_status": "approved_keyword",
            "review_notes": "Approved via deterministic keyword fallback.",
        }

    well_markers = [r"\bwell\b", r"\bawi\b", r"\bdrj-steam\b", r"\b14-1\b", r"\b14-2\b", r"\b20-1\b", r"\bsf-1\b"]
    well_operations = [
        "contract rig",
        "casing",
        "cement",
        "mud",
        "logging",
        "coring",
        "directional drilling",
        "supervision",
        "transportation",
        "equipment rental",
        "machine shop",
        "inspection",
        "service lines",
        "welding",
        "explosive",
    ]
    if any(re.search(pattern, combined) for pattern in well_markers) or any(token in combined for token in well_operations):
        well_use, campaign_use = usage_flags_for_class("well_tied")
        return {
            "classification": "well_tied",
            "driver_family": "well_scope",
            "classification_confidence": "medium",
            "classification_rule_id": "R6_KEYWORD_WELL_SCOPE",
            "classification_rule_text": "Well markers and well-operation keywords indicate direct well scope.",
            "well_estimation_use": well_use,
            "campaign_estimation_use": campaign_use,
            "review_status": "approved_keyword",
            "review_notes": "Approved via deterministic keyword fallback.",
        }

    well_use, campaign_use = usage_flags_for_class("unresolved")
    return {
        "classification": "unresolved",
        "driver_family": "",
        "classification_confidence": "low",
        "classification_rule_id": "R9_REVIEW_REQUIRED",
        "classification_rule_text": "No deterministic driver-family evidence matched the current policy or keyword rules.",
        "well_estimation_use": well_use,
        "campaign_estimation_use": campaign_use,
        "review_status": "needs_review",
        "review_notes": "Missing deterministic evidence; hold for adjudication rather than defaulting to hybrid.",
    }


def build_proposal(row: dict[str, str], policy_rows: list[dict[str, str]]) -> dict[str, str]:
    tag = clean_text(row.get("tag_well_or_pad", ""))

    if tag == "Well":
        well_use, campaign_use = usage_flags_for_class("well_tied")
        return {
            "classification": "well_tied",
            "driver_family": "well_scope",
            "classification_confidence": "high",
            "classification_rule_id": "R1_DICT_WELL_TAG",
            "classification_rule_text": "Dictionary `Tag_Well_or_Pad=Well` indicates direct well scope.",
            "well_estimation_use": well_use,
            "campaign_estimation_use": campaign_use,
            "review_status": "approved_auto",
            "review_notes": "Approved from explicit dictionary tag.",
        }

    matched_policy = policy_match(row, policy_rows)
    if matched_policy:
        estimation_class = clean_text(matched_policy["estimation_class"])
        well_use, campaign_use = usage_flags_for_class(estimation_class)
        return {
            "classification": estimation_class,
            "driver_family": clean_text(matched_policy["driver_family"]),
            "classification_confidence": "high",
            "classification_rule_id": f"R2_POLICY_{clean_text(matched_policy['policy_id'])}",
            "classification_rule_text": clean_text(matched_policy["approval_notes"]),
            "well_estimation_use": well_use,
            "campaign_estimation_use": campaign_use,
            "review_status": "approved_policy",
            "review_notes": clean_text(matched_policy["approval_basis"]),
        }

    return keyword_fallback(row)


def build_master_rows(
    data_summary: list[dict[str, str]],
    lvl5_dict: dict[str, dict[str, str]],
    campaign_by_name: dict[str, dict[str, str]],
    campaign_by_code: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    master_rows: list[dict[str, str]] = []
    for row in data_summary:
        campaign_raw = clean_text(row.get("Campaign", ""))
        wbs_code = clean_text(row.get("WBS_ID", ""))
        dict_match = lvl5_dict.get(wbs_code, {})
        campaign_map, mapping_basis = resolve_campaign_mapping(campaign_raw, campaign_by_name, campaign_by_code)
        campaign_canonical = clean_text(campaign_map.get("campaign_id", ""))
        campaign_code = clean_text(campaign_map.get("campaign_code", ""))
        campaign_scope = clean_text(campaign_map.get("estimator_scope", ""))

        source_row_key = f"20260327_WBS_Data.xlsx|Data.Summary|{row['_source_excel_row']}|{wbs_code}|{campaign_raw}"
        source_row_id = hashlib.md5(source_row_key.encode("utf-8")).hexdigest()[:16]

        master_rows.append(
            {
                "source_file": "20260327_WBS_Data.xlsx",
                "source_sheet": "Data.Summary",
                "source_row_id": source_row_id,
                "field": map_field(row.get("Asset", "")),
                "campaign_raw": campaign_raw,
                "campaign_code": campaign_code,
                "campaign_canonical": campaign_canonical,
                "campaign_scope": campaign_scope,
                "campaign_mapping_basis": mapping_basis,
                "well_raw": "",
                "well_canonical": "",
                "wbs_code_raw": wbs_code,
                "wbs_lvl1": clean_text(dict_match.get("LVL 1", "")) or clean_text(row.get("L1", "")),
                "wbs_lvl2": clean_text(dict_match.get("LVL 2", "")) or clean_text(row.get("L2", "")),
                "wbs_lvl3": clean_text(dict_match.get("LVL 3", "")) or clean_text(row.get("L3", "")),
                "wbs_lvl4": clean_text(dict_match.get("LVL 4", "")) or clean_text(row.get("L4", "")),
                "wbs_lvl5": clean_text(dict_match.get("LVL 5", "")) or clean_text(row.get("L5", "")),
                "wbs_label_raw": clean_text(row.get("Description", "")),
                "cost_actual": f"{parse_float(row.get('ACTUAL, USD', '0')):.6f}",
                "currency": "USD",
                "event_code_raw": "",
                "event_code_desc": "",
                "npt_class": "",
                "mapping_status_campaign": "mapped" if campaign_canonical else "unmapped",
                "mapping_status_well": "not_available_at_source_grain",
                "tag_well_or_pad": clean_text(dict_match.get("Tag_Well_or_Pad", "")),
                "tag_lvl5": clean_text(dict_match.get("Tag_LVL5", "")),
            }
        )

    unmapped_in_scope = [
        row
        for row in master_rows
        if clean_text(row["campaign_raw"]).upper() in IN_SCOPE_CAMPAIGN_LABELS and row["mapping_status_campaign"] != "mapped"
    ]
    if unmapped_in_scope:
        sample = unmapped_in_scope[0]
        raise ValueError(
            "In-scope campaign mapping hard gate failed; example unmapped row: "
            f"{sample['campaign_raw']} | {sample['wbs_code_raw']} | {sample['wbs_label_raw']}"
        )

    return master_rows


def build_class_rows(master_rows: list[dict[str, str]], policy_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for rec in master_rows:
        cls_key = "|".join([rec["field"], rec["wbs_lvl2"], rec["wbs_lvl3"], rec["wbs_lvl4"], rec["wbs_lvl5"]])
        grouped[cls_key].append(rec)

    class_rows: list[dict[str, str]] = []
    for key, recs in sorted(grouped.items()):
        spend = sum(parse_float(r["cost_actual"]) for r in recs)
        proposal = build_proposal(recs[0], policy_rows)
        class_rows.append(
            {
                "classification_key": key,
                "field": recs[0]["field"],
                "wbs_code_lv5": recs[0]["wbs_code_raw"],
                "wbs_lvl2": recs[0]["wbs_lvl2"],
                "wbs_lvl3": recs[0]["wbs_lvl3"],
                "wbs_lvl4": recs[0]["wbs_lvl4"],
                "wbs_lvl5": recs[0]["wbs_lvl5"],
                "wbs_family_tag": recs[0]["tag_lvl5"],
                "example_wbs_label": recs[0]["wbs_label_raw"],
                "classification": proposal["classification"],
                "driver_family": proposal["driver_family"],
                "classification_confidence": proposal["classification_confidence"],
                "classification_rule_id": proposal["classification_rule_id"],
                "classification_rule_text": proposal["classification_rule_text"],
                "well_estimation_use": proposal["well_estimation_use"],
                "campaign_estimation_use": proposal["campaign_estimation_use"],
                "review_status": proposal["review_status"],
                "review_notes": proposal["review_notes"],
                "material_review_flag": "yes" if spend >= MATERIAL_REVIEW_THRESHOLD else "no",
                "supporting_row_count": str(len(recs)),
                "supporting_cost_total": f"{spend:.6f}",
            }
        )
    return class_rows


def build_driver_reference(class_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    driver_rows: list[dict[str, str]] = []
    for row in class_rows:
        spend = parse_float(row["supporting_cost_total"])
        approval_notes = clean_text(row["review_notes"])
        if spend >= MATERIAL_REVIEW_THRESHOLD:
            approval_notes = f"{approval_notes} Material item above USD 500k; included in the material review queue.".strip()

        estimation_class = row["classification"] if row["classification"] in ALLOWED_CLASSES else ""
        driver_rows.append(
            {
                "classification_key": row["classification_key"],
                "field": row["field"],
                "wbs_code_lv5": row["wbs_code_lv5"],
                "wbs_lvl5": row["wbs_lvl5"],
                "wbs_family_tag": row["wbs_family_tag"],
                "example_wbs_label": row["example_wbs_label"],
                "supporting_cost_total": row["supporting_cost_total"],
                "estimation_class": estimation_class,
                "driver_family": row["driver_family"],
                "well_estimation_use": row["well_estimation_use"],
                "campaign_estimation_use": row["campaign_estimation_use"],
                "approval_status": row["review_status"],
                "approval_basis": row["classification_rule_id"],
                "approval_notes": approval_notes,
            }
        )
    return driver_rows


def build_review_queue(class_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    review_rows: list[dict[str, str]] = []
    for row in class_rows:
        spend = parse_float(row["supporting_cost_total"])
        unresolved = row["classification"] == "unresolved"
        material = spend >= MATERIAL_REVIEW_THRESHOLD
        if not unresolved and not material:
            continue

        if unresolved and material:
            reason = "unresolved_and_material"
        elif unresolved:
            reason = "unresolved_classification"
        else:
            reason = "material_threshold"

        review_rows.append(
            {
                "classification_key": row["classification_key"],
                "field": row["field"],
                "wbs_lvl5": row["wbs_lvl5"],
                "wbs_family_tag": row["wbs_family_tag"],
                "reason_for_review": reason,
                "approval_status": row["review_status"],
                "observed_patterns": row["classification_rule_id"],
                "supporting_row_count": row["supporting_row_count"],
                "supporting_cost_total": row["supporting_cost_total"],
                "proposed_classification": row["classification"],
                "driver_family": row["driver_family"],
            }
        )
    return review_rows


def build_summary_rows(class_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    cost_by_class = defaultdict(float)
    count_by_class = Counter()
    total_cost = 0.0
    approved_rows = [row for row in class_rows if row["classification"] in ALLOWED_CLASSES]
    for row in approved_rows:
        cls = row["classification"]
        spend = parse_float(row["supporting_cost_total"])
        count_by_class[cls] += 1
        cost_by_class[cls] += spend
        total_cost += spend

    global_rows: list[dict[str, str]] = []
    total_keys = sum(count_by_class.values())
    for cls in CLASS_ORDER:
        if cls == "unresolved":
            continue
        global_rows.append(
            {
                "classification": cls,
                "key_count": str(count_by_class[cls]),
                "key_share_pct": f"{(100.0 * count_by_class[cls] / total_keys) if total_keys else 0.0:.4f}",
                "cost_total": f"{cost_by_class[cls]:.6f}",
                "cost_share_pct": f"{(100.0 * cost_by_class[cls] / total_cost) if total_cost else 0.0:.4f}",
            }
        )

    field_rows: list[dict[str, str]] = []
    field_costs: dict[tuple[str, str], float] = defaultdict(float)
    field_counts: Counter[tuple[str, str]] = Counter()
    field_totals: dict[str, float] = defaultdict(float)
    field_key_totals: Counter[str] = Counter()
    for row in approved_rows:
        field = row["field"]
        cls = row["classification"]
        spend = parse_float(row["supporting_cost_total"])
        field_costs[(field, cls)] += spend
        field_counts[(field, cls)] += 1
        field_totals[field] += spend
        field_key_totals[field] += 1

    for field in sorted(field_totals):
        for cls in CLASS_ORDER:
            if cls == "unresolved":
                continue
            key = (field, cls)
            field_rows.append(
                {
                    "field": field,
                    "classification": cls,
                    "key_count": str(field_counts[key]),
                    "key_share_pct": f"{(100.0 * field_counts[key] / field_key_totals[field]) if field_key_totals[field] else 0.0:.4f}",
                    "cost_total": f"{field_costs[key]:.6f}",
                    "cost_share_pct": f"{(100.0 * field_costs[key] / field_totals[field]) if field_totals[field] else 0.0:.4f}",
                }
            )

    return global_rows, field_rows


def build_hybrid_scope_rows(class_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    hybrid_rows = []
    for row in class_rows:
        if row["classification"] != "hybrid":
            continue
        hybrid_rows.append(
            {
                "classification_key": row["classification_key"],
                "field": row["field"],
                "wbs_lvl4": row["wbs_lvl4"],
                "wbs_lvl5": row["wbs_lvl5"],
                "supporting_cost_total": row["supporting_cost_total"],
                "suggested_tag": "campaign",
                "suggestion_basis": f"approved_hybrid_scope:{row['driver_family']}",
            }
        )
    return sorted(hybrid_rows, key=lambda r: parse_float(r["supporting_cost_total"]), reverse=True)


def build_rulebook(policy_rows: list[dict[str, str]]) -> None:
    lines = [
        "# WBS Lv.5 Driver Alignment Rulebook",
        "",
        "## Rule Order",
        "1. `R0_CAMPAIGN_MAPPING_GATE`: resolve `DRJ 2022`, `DRJ 2023`, and `SLK 2025` to official campaign codes before any class assignment.",
        "2. `R1_DICT_WELL_TAG`: explicit dictionary `Tag_Well_or_Pad=Well` -> `well_tied` with `driver_family=well_scope`.",
        "3. `R2_POLICY_*`: curated family policy table splits non-well scope into `campaign_tied` versus `hybrid` using WBS family/subfamily meaning.",
        "4. `R4/R5/R6_KEYWORD_*`: deterministic keyword fallback is allowed only after curated policy lookup.",
        "5. `R9_REVIEW_REQUIRED`: unresolved items remain in review; missing evidence never defaults to `hybrid`.",
        "",
        "## Hybrid Semantics",
        "- `hybrid` means non-well cost that is estimable from structured campaign design/scope drivers such as pad expansion, tie-in scope, interpad moves, or rig skid count.",
        "- `hybrid` is **not** a placeholder for unknown scope.",
        "",
        "## Curated Policy Families",
    ]
    for row in policy_rows:
        lines.append(
            f"- `{row['policy_id']}` priority {row['policy_priority']}: "
            f"`tag={clean_text(row['tag_well_or_pad']) or '*'}` / "
            f"`family={clean_text(row['tag_lvl5']) or '*'}` / "
            f"`label_contains={clean_text(row['label_contains']) or '*'}` -> "
            f"`{row['estimation_class']}` (`{row['driver_family']}`)"
        )
    lines.extend(
        [
            "",
            "## Estimator Composition Freeze",
            "- `campaign estimate = sum(well_tied well estimates) + campaign_tied campaign estimate + hybrid scope-based campaign estimate`.",
            "- Usage flags are fixed as `well_tied -> direct + rollup_from_wells`, `campaign_tied -> exclude + direct_campaign`, `hybrid -> exclude + scope_scaled`.",
        ]
    )
    write_text(RULEBOOK_REPORT, "\n".join(lines) + "\n")


def build_alignment_report(
    master_rows: list[dict[str, str]],
    driver_rows: list[dict[str, str]],
    global_summary_rows: list[dict[str, str]],
    field_summary_rows: list[dict[str, str]],
) -> str:
    total_cost = sum(parse_float(row["cost_actual"]) for row in master_rows)
    mapped_in_scope = sum(
        1
        for row in master_rows
        if clean_text(row["campaign_raw"]).upper() in IN_SCOPE_CAMPAIGN_LABELS and row["mapping_status_campaign"] == "mapped"
    )
    unresolved_count = sum(1 for row in driver_rows if row["approval_status"] == "needs_review")
    material_rows = [
        row for row in driver_rows if parse_float(row["supporting_cost_total"]) >= MATERIAL_REVIEW_THRESHOLD and row["estimation_class"]
    ]
    hybrid_driver_rollup = defaultdict(float)
    hybrid_driver_counts = Counter()
    for row in driver_rows:
        if row["estimation_class"] != "hybrid":
            continue
        hybrid_driver_rollup[row["driver_family"]] += parse_float(row["supporting_cost_total"])
        hybrid_driver_counts[row["driver_family"]] += 1

    lines = [
        "# WBS Lv.5 Driver Alignment Report",
        "",
        "## Snapshot",
        "- This run treats the current `data/raw/*.xlsx` files as the frozen source snapshot for driver alignment.",
        f"- Total Lv.5 source rows processed: **{len(master_rows)}**",
        f"- Total cost processed (USD): **{total_cost:,.2f}**",
        "",
        "## Campaign Mapping Gate",
        f"- In-scope campaign rows mapped: **{mapped_in_scope} / {len(master_rows)}**",
        "- In-scope labels `DRJ 2022`, `DRJ 2023`, and `SLK 2025` are required to resolve before class assignment.",
        "",
        "## Approved Driver Mix",
    ]
    for row in global_summary_rows:
        lines.append(
            f"- `{row['classification']}`: {row['key_count']} keys ({row['key_share_pct']}%), "
            f"USD {parse_float(row['cost_total']):,.2f} ({row['cost_share_pct']}%)"
        )

    lines.extend(["", "## By Field"])
    current_field = ""
    for row in field_summary_rows:
        if row["field"] != current_field:
            current_field = row["field"]
            lines.append(f"- **{current_field}**")
        lines.append(
            f"  `{row['classification']}`: {row['key_count']} keys ({row['key_share_pct']}%), "
            f"USD {parse_float(row['cost_total']):,.2f} ({row['cost_share_pct']}%)"
        )

    lines.extend(
        [
            "",
            "## Review Status",
            f"- Unresolved keys: **{unresolved_count}**",
            f"- Material review keys (>= USD {MATERIAL_REVIEW_THRESHOLD:,.0f}): **{len(material_rows)}**",
            "",
            "## Material Review List",
        ]
    )
    for row in sorted(material_rows, key=lambda item: parse_float(item["supporting_cost_total"]), reverse=True):
        lines.append(
            f"- `{row['classification_key']}` | `{row['estimation_class']}` | "
            f"`{row['driver_family']}` | USD {parse_float(row['supporting_cost_total']):,.2f}"
        )

    lines.extend(["", "## Hybrid Driver Families"])
    for driver_family in sorted(hybrid_driver_rollup, key=lambda key: hybrid_driver_rollup[key], reverse=True):
        lines.append(
            f"- `{driver_family}`: {hybrid_driver_counts[driver_family]} keys, "
            f"USD {hybrid_driver_rollup[driver_family]:,.2f}"
        )

    lines.extend(
        [
            "",
            "## Estimator Composition",
            "- `campaign estimate = sum(well_tied well estimates) + campaign_tied campaign estimate + hybrid scope-based campaign estimate`.",
            "- `well_tied` remains the only class eligible for direct well-level estimation in this layer.",
            "- `campaign_tied` stays campaign-only.",
            "- `hybrid` stays campaign-scope and is carried through design counts/flags rather than per-well allocation.",
        ]
    )
    return "\n".join(lines) + "\n"


def pct_str(part: int, total: int) -> str:
    if total <= 0:
        return "0.00%"
    return f"{(100.0 * part / total):.2f}%"


def build_define_quality_report(master_rows: list[dict[str, str]], class_rows: list[dict[str, str]]) -> str:
    campaign_rows = read_csv_rows(PROCESSED_DIR / "canonical_campaign_mapping.csv")
    well_rows = read_csv_rows(PROCESSED_DIR / "well_master.csv")

    total_rows = len(master_rows)
    hierarchy_blank = sum(
        1
        for row in master_rows
        if any(not clean_text(row.get(col, "")) for col in ["wbs_lvl1", "wbs_lvl2", "wbs_lvl3", "wbs_lvl4", "wbs_lvl5"])
    )
    campaign_blank = sum(
        1 for row in master_rows if not clean_text(row.get("campaign_code", "")) or not clean_text(row.get("campaign_canonical", ""))
    )
    cost_blank = sum(1 for row in master_rows if not clean_text(row.get("cost_actual", "")))
    well_coverage = sum(1 for row in master_rows if clean_text(row.get("well_canonical", "")))
    event_coverage = sum(1 for row in master_rows if clean_text(row.get("event_code_raw", "")))
    in_scope_rows = [row for row in master_rows if clean_text(row.get("campaign_raw", "")).upper() in IN_SCOPE_CAMPAIGN_LABELS]
    in_scope_mapped = sum(
        1 for row in in_scope_rows if clean_text(row.get("mapping_status_campaign", "")) == "mapped" and clean_text(row.get("campaign_code", ""))
    )

    duplicate_classification_keys = len(class_rows) - len({clean_text(row.get("classification_key", "")) for row in class_rows})
    duplicate_campaign_codes = len(campaign_rows) - len({clean_text(row.get("campaign_code", "")) for row in campaign_rows if clean_text(row.get("campaign_code", ""))})
    duplicate_well_master_keys = len(well_rows) - len(
        {
            f"{clean_text(row.get('well_id', ''))}|{clean_text(row.get('campaign_code', ''))}"
            for row in well_rows
            if clean_text(row.get("well_id", "")) and clean_text(row.get("campaign_code", ""))
        }
    )

    gate_failures = [
        hierarchy_blank != 0,
        campaign_blank != 0,
        in_scope_mapped != len(in_scope_rows),
        duplicate_classification_keys != 0,
        duplicate_campaign_codes != 0,
        duplicate_well_master_keys != 0,
    ]
    gate_status = "READY FOR PHASE 3 DESIGN" if not any(gate_failures) else "HOLD PHASE 2 DEFINE"

    threshold_rows = [
        ("Hierarchy completeness", "0 rows with blank `wbs_lvl1..wbs_lvl5`", f"{hierarchy_blank} / {total_rows} blank", "PASS" if hierarchy_blank == 0 else "FAIL", "Required for L1->L5 auditability."),
        ("Campaign mapping completeness", "0 rows with blank campaign mapping fields", f"{campaign_blank} / {total_rows} blank", "PASS" if campaign_blank == 0 else "FAIL", "Requires both `campaign_code` and `campaign_canonical`."),
        ("In-scope campaign alias mapping", "All in-scope labels mapped", f"{in_scope_mapped} / {len(in_scope_rows)} mapped", "PASS" if in_scope_mapped == len(in_scope_rows) else "FAIL", "Checks `DRJ 2022`, `DRJ 2023`, and `SLK 2025`."),
        ("Duplicate classification keys", "0 duplicate `classification_key` values", str(duplicate_classification_keys), "PASS" if duplicate_classification_keys == 0 else "FAIL", "Classification grain is the implemented Lv5 canonical key."),
        ("Duplicate campaign master codes", "0 duplicate `campaign_code` values", str(duplicate_campaign_codes), "PASS" if duplicate_campaign_codes == 0 else "FAIL", "Campaign master must remain one row per canonical campaign code."),
        ("Duplicate well master keys", "0 duplicate (`well_id`, `campaign_code`) pairs", str(duplicate_well_master_keys), "PASS" if duplicate_well_master_keys == 0 else "FAIL", "Well master is one row per canonical well within a campaign."),
        ("Well attribution coverage", "Report coverage; not a Phase 2 blocker at campaign/WBS grain", f"{well_coverage} / {total_rows} ({pct_str(well_coverage, total_rows)})", "KNOWN LIMITATION", "Current `Data.Summary` grain does not carry direct well attribution for Lv5 rows."),
        ("Event-code coverage", "Report coverage; not a Phase 2 blocker at campaign/WBS grain", f"{event_coverage} / {total_rows} ({pct_str(event_coverage, total_rows)})", "KNOWN LIMITATION", "Event-code family is defined, but row-addressable values are not present in the current Lv5 build."),
    ]

    null_snapshot = [
        ("wbs_lvl1", sum(1 for row in master_rows if not clean_text(row.get("wbs_lvl1", "")))),
        ("wbs_lvl2", sum(1 for row in master_rows if not clean_text(row.get("wbs_lvl2", "")))),
        ("wbs_lvl3", sum(1 for row in master_rows if not clean_text(row.get("wbs_lvl3", "")))),
        ("wbs_lvl4", sum(1 for row in master_rows if not clean_text(row.get("wbs_lvl4", "")))),
        ("wbs_lvl5", sum(1 for row in master_rows if not clean_text(row.get("wbs_lvl5", "")))),
        ("campaign_code", sum(1 for row in master_rows if not clean_text(row.get("campaign_code", "")))),
        ("campaign_canonical", sum(1 for row in master_rows if not clean_text(row.get("campaign_canonical", "")))),
        ("cost_actual", cost_blank),
        ("well_canonical", total_rows - well_coverage),
        ("event_code_raw", total_rows - event_coverage),
    ]

    lines = [
        "# Phase 2 Define Quality Thresholds",
        "",
        "## Gate Authority",
        "- `docs/PROJECT_INSTRUCTION.md` is the authoritative Phase 2 gate reference.",
        f"- Gate recommendation: **{gate_status}**.",
        "- Material review flags are informational only when unresolved keys remain at zero.",
        "",
        "## Threshold Results",
        "| check | threshold | observed | status | notes |",
        "|---|---|---|---|---|",
    ]

    for check, threshold, observed, status, notes in threshold_rows:
        lines.append(f"| {check} | {threshold} | {observed} | {status} | {notes} |")

    lines.extend(
        [
            "",
            "## Null Coverage Snapshot",
            "| field | blank_rows | blank_pct |",
            "|---|---:|---:|",
        ]
    )
    for field_name, blank_count in null_snapshot:
        lines.append(f"| {field_name} | {blank_count} | {pct_str(blank_count, total_rows)} |")

    lines.extend(
        [
            "",
            "## Current Grain Limitation",
            "- `wbs_lv5_master.csv` is complete for hierarchy and campaign mapping, but the current source grain does not populate direct well attribution for Lv5 rows.",
            "- `event_code_raw` and `event_code_desc` remain blank in this Define layer because the unscheduled-event workbook is not row-addressable to `Data.Summary` Lv5 cost rows.",
            "- These limitations do not block Phase 3 design, but they do constrain later well-level driver validation until a richer source grain is introduced.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    wb_data = read_xlsx(RAW_DIR / "20260327_WBS_Data.xlsx")
    wb_dict = read_xlsx(RAW_DIR / "20260318_WBS_Dictionary.xlsx")
    wb_event = read_xlsx(RAW_DIR / "UNSCHEDULED EVENT CODE.xlsx")
    wb_ref = read_xlsx(RAW_DIR / "WBS Reference for Drilling Campaign (Drilling Cost).xlsx")

    build_inventory_note(
        {
            "20260327_WBS_Data.xlsx": wb_data,
            "20260318_WBS_Dictionary.xlsx": wb_dict,
            "UNSCHEDULED EVENT CODE.xlsx": wb_event,
            "WBS Reference for Drilling Campaign (Drilling Cost).xlsx": wb_ref,
        }
    )

    data_summary = sheet_to_records(
        wb_data["Data.Summary"],
        required=["Asset", "Campaign", "WBS_ID", "Description", "ACTUAL, USD", "L1", "L2", "L3", "L4", "L5"],
    )
    data_summary = [row for row in data_summary if clean_text(row.get("L5", ""))]

    dict_rows = sheet_to_records(
        wb_dict["WBS_Dictionary"],
        required=["LEVEL", "WBS CODE", "LVL 1", "LVL 2", "LVL 3", "LVL 4", "LVL 5", "Tag_Well_or_Pad", "Tag_LVL5"],
    )
    lvl5_dict = {
        clean_text(r["WBS CODE"]): r
        for r in dict_rows
        if clean_text(r.get("LEVEL", "")) == "05" and clean_text(r.get("WBS CODE", ""))
    }

    campaign_by_name, campaign_by_code = load_campaign_mappings()
    policy_rows = load_policy_rows()

    master_rows = build_master_rows(data_summary, lvl5_dict, campaign_by_name, campaign_by_code)
    class_rows = build_class_rows(master_rows, policy_rows)
    driver_rows = build_driver_reference(class_rows)
    review_rows = build_review_queue(class_rows)
    global_summary_rows, field_summary_rows = build_summary_rows(class_rows)
    hybrid_scope_rows = build_hybrid_scope_rows(class_rows)
    rule_coverage_rows = [
        {"classification_rule_id": rule_id, "key_count": str(count)}
        for rule_id, count in sorted(Counter(row["classification_rule_id"] for row in class_rows).items())
    ]

    write_csv(
        MASTER_PATH,
        master_rows,
        [
            "source_file",
            "source_sheet",
            "source_row_id",
            "field",
            "campaign_raw",
            "campaign_code",
            "campaign_canonical",
            "campaign_scope",
            "campaign_mapping_basis",
            "well_raw",
            "well_canonical",
            "wbs_code_raw",
            "wbs_lvl1",
            "wbs_lvl2",
            "wbs_lvl3",
            "wbs_lvl4",
            "wbs_lvl5",
            "wbs_label_raw",
            "cost_actual",
            "currency",
            "event_code_raw",
            "event_code_desc",
            "npt_class",
            "mapping_status_campaign",
            "mapping_status_well",
            "tag_well_or_pad",
            "tag_lvl5",
        ],
    )
    write_csv(
        CLASSIFICATION_PATH,
        class_rows,
        [
            "classification_key",
            "field",
            "wbs_code_lv5",
            "wbs_lvl2",
            "wbs_lvl3",
            "wbs_lvl4",
            "wbs_lvl5",
            "wbs_family_tag",
            "example_wbs_label",
            "classification",
            "driver_family",
            "classification_confidence",
            "classification_rule_id",
            "classification_rule_text",
            "well_estimation_use",
            "campaign_estimation_use",
            "review_status",
            "review_notes",
            "material_review_flag",
            "supporting_row_count",
            "supporting_cost_total",
        ],
    )
    write_csv(
        DRIVER_REFERENCE_PATH,
        driver_rows,
        [
            "classification_key",
            "field",
            "wbs_code_lv5",
            "wbs_lvl5",
            "wbs_family_tag",
            "example_wbs_label",
            "supporting_cost_total",
            "estimation_class",
            "driver_family",
            "well_estimation_use",
            "campaign_estimation_use",
            "approval_status",
            "approval_basis",
            "approval_notes",
        ],
    )
    write_csv(
        REVIEW_QUEUE_PATH,
        review_rows,
        [
            "classification_key",
            "field",
            "wbs_lvl5",
            "wbs_family_tag",
            "reason_for_review",
            "approval_status",
            "observed_patterns",
            "supporting_row_count",
            "supporting_cost_total",
            "proposed_classification",
            "driver_family",
        ],
    )
    write_csv(COST_SUMMARY_PATH, global_summary_rows, ["classification", "key_count", "key_share_pct", "cost_total", "cost_share_pct"])
    write_csv(FIELD_SUMMARY_PATH, field_summary_rows, ["field", "classification", "key_count", "key_share_pct", "cost_total", "cost_share_pct"])
    write_csv(HYBRID_SCOPE_PATH, hybrid_scope_rows, ["classification_key", "field", "wbs_lvl4", "wbs_lvl5", "supporting_cost_total", "suggested_tag", "suggestion_basis"])
    write_csv(RULE_COVERAGE_PATH, rule_coverage_rows, ["classification_rule_id", "key_count"])
    write_csv(
        CURATED_POLICY_OUTPUT_PATH,
        policy_rows,
        ["policy_id", "policy_priority", "tag_well_or_pad", "tag_lvl5", "label_contains", "estimation_class", "driver_family", "approval_basis", "approval_notes"],
    )

    build_rulebook(policy_rows)
    alignment_report = build_alignment_report(master_rows, driver_rows, global_summary_rows, field_summary_rows)
    write_text(ALIGNMENT_REPORT, alignment_report)
    write_text(CLASSIFICATION_REPORT, alignment_report)
    write_text(DEFINE_QUALITY_REPORT, build_define_quality_report(master_rows, class_rows))
    print("Wrote WBS Lv.5 driver alignment artifacts.")


if __name__ == "__main__":
    main()
