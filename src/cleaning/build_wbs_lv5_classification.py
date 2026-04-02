from __future__ import annotations

import sys
from pathlib import Path as _BootstrapPath

_ROOT = _BootstrapPath(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.cleaning.wbs_lv5_driver_alignment import main as _driver_alignment_main

if __name__ == "__main__":
    _driver_alignment_main()
    raise SystemExit(0)

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

MASTER_PATH = PROCESSED_DIR / "wbs_lv5_master.csv"
CLASSIFICATION_PATH = PROCESSED_DIR / "wbs_lv5_classification.csv"
REVIEW_QUEUE_PATH = PROCESSED_DIR / "wbs_lv5_review_queue.csv"
COST_SUMMARY_PATH = PROCESSED_DIR / "wbs_lv5_cost_summary_by_classification.csv"
RULE_COVERAGE_PATH = PROCESSED_DIR / "wbs_lv5_rule_coverage.csv"
HYBRID_TAG_REVIEW_PATH = PROCESSED_DIR / "wbs_lv5_hybrid_tag_recommendation.csv"

INVENTORY_REPORT = REPORTS_DIR / "wbs_lv5_source_inventory.md"
RULEBOOK_REPORT = REPORTS_DIR / "wbs_lv5_classification_rulebook.md"
CLASSIFICATION_REPORT = REPORTS_DIR / "wbs_lv5_classification_report.md"

NS_MAIN = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_PKG = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\n", " ")).strip()


def normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(value).lower())


def normalize_name(value: str) -> str:
    return re.sub(r"\s*[-_/]+\s*", "-", clean_text(value).upper())


def col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def parse_float(value: str) -> float:
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
    normalized_header = {normalize_token(v): v for v in rows[header_idx] if clean_text(v)}
    cols_optional: dict[str, int] = {}
    norm_to_idx = {normalize_token(v): i for i, v in enumerate(rows[header_idx]) if normalize_token(v)}
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


def build_inventory_note(workbooks: dict[str, dict[str, list[list[str]]]]) -> None:
    lines = [
        "# WBS Lv.5 Source Inventory",
        "",
        "## Scope",
        "Reviewed workbook structure and headers for classification-layer build.",
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
            "- **WBS hierarchy:** `20260318_WBS_Dictionary.xlsx` → `WBS_Dictionary` (LEVEL/LVL 1..5, WBS CODE, tags).",
            "- **Cost rows:** `20260327_WBS_Data.xlsx` → `Data.Summary` (`ACTUAL, USD`, WBS path fields).",
            "- **Campaign mapping:** `data/processed/canonical_campaign_mapping.csv` + `Campaign` in `Data.Summary`.",
            "- **Well naming context:** `data/processed/canonical_well_mapping.csv` + `1. WellName.Dictionary` for coverage checks.",
            "- **Unscheduled/NPT reference:** `UNSCHEDULED EVENT CODE.xlsx` `Sheet1`; NPT classes are not row-addressable from `Data.Summary`, so left explicit-null in master table.",
            "",
            "## Data Quality Observations",
            "- `Data.Summary` has hierarchy rows across multiple WBS levels; only rows with populated `L5` are used for Lv.5 classification.",
            "- Several workbook sheets contain explanatory header rows before tabular headers; parser identifies header row dynamically.",
            "- `WBS_Dictionary` contains mixed sections; only rows where `LEVEL == 05` and `WBS CODE` is present are used as Lv.5 dictionary records.",
            "- `Campaign` in cost rows is a label (e.g., `DRJ 2022`), requiring canonical mapping lookup by campaign label.",
            "",
            "## Join Candidates",
            "- Cost rows ↔ WBS dictionary via exact `WBS_ID` (`Data.Summary`) to `WBS CODE` (`WBS_Dictionary`).",
            "- Cost rows ↔ canonical campaign via normalized `Campaign` label.",
            "- Well-level context retained as nullable fields because `Data.Summary` is mostly campaign/WBS-grain, not explicit well-grain.",
        ]
    )
    INVENTORY_REPORT.write_text("\n".join(lines) + "\n")


def classify_row(rec: dict[str, str], signal: dict[str, float | int | str]) -> dict[str, str]:
    tag = clean_text(rec.get("tag_well_or_pad", "")).lower()
    lvl5 = clean_text(rec.get("wbs_lvl5", "")).lower()
    lvl4 = clean_text(rec.get("wbs_lvl4", "")).lower()
    combined = f"{lvl4} {lvl5}"

    if tag == "well":
        return {
            "classification": "well_tied",
            "classification_confidence": "high",
            "classification_rule_id": "R1_TAG_WELL",
            "classification_rule_text": "Tag_Well_or_Pad=Well indicates direct well attribution.",
            "recommended_allocation_basis": "direct_to_well",
            "review_status": "approved_auto",
            "review_notes": "",
        }

    if tag == "pad":
        return {
            "classification": "campaign_tied",
            "classification_confidence": "high",
            "classification_rule_id": "R2_TAG_PAD",
            "classification_rule_text": "Tag_Well_or_Pad=Pad indicates shared campaign/pad scope.",
            "recommended_allocation_basis": "allocate_later_by_campaign",
            "review_status": "approved_auto",
            "review_notes": "",
        }

    campaign_words = ["mobil", "demobil", "contingency", "campaign", "support", "shared", "camp", "interfield", "move"]
    well_words = ["drill", "sidetrack", "completion", "logging", "evaluation", "cement", "mud", "bit", "well service"]

    if any(word in combined for word in campaign_words):
        return {
            "classification": "campaign_tied",
            "classification_confidence": "medium",
            "classification_rule_id": "R3_KEYWORD_CAMPAIGN",
            "classification_rule_text": "Campaign/shared-scope keyword match in Lv.4/Lv.5 labels.",
            "recommended_allocation_basis": "allocate_later_by_campaign",
            "review_status": "needs_review",
            "review_notes": "Keyword-only evidence (no explicit tag).",
        }

    if any(word in combined for word in well_words):
        return {
            "classification": "well_tied",
            "classification_confidence": "medium",
            "classification_rule_id": "R4_KEYWORD_WELL",
            "classification_rule_text": "Well-operation keyword match in Lv.4/Lv.5 labels.",
            "recommended_allocation_basis": "direct_to_well_when_available",
            "review_status": "needs_review",
            "review_notes": "Keyword-only evidence (no explicit tag).",
        }

    return {
        "classification": "hybrid",
        "classification_confidence": "low",
        "classification_rule_id": "R5_FALLBACK_HYBRID",
        "classification_rule_text": "No deterministic well/pad tag or stable behavioral indicator; held as hybrid.",
        "recommended_allocation_basis": "defer_driver_based_split",
        "review_status": "needs_review",
        "review_notes": "Ambiguous usage; reviewer confirmation required.",
    }


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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

    with (PROCESSED_DIR / "canonical_campaign_mapping.csv").open() as fh:
        campaign_rows = list(csv.DictReader(fh))
    campaign_by_name = {normalize_token(r["campaign_name_raw"]): r for r in campaign_rows if clean_text(r.get("campaign_name_raw", ""))}
    campaign_by_code = {clean_text(r["campaign_code"]): r for r in campaign_rows if clean_text(r.get("campaign_code", ""))}

    with (PROCESSED_DIR / "canonical_well_mapping.csv").open() as fh:
        well_rows = list(csv.DictReader(fh))
    well_by_alias_campaign = {
        (normalize_token(r.get("campaign_id", "")), normalize_name(r.get("well_alias", ""))): r for r in well_rows if clean_text(r.get("well_alias", ""))
    }

    unscheduled_records = sheet_to_records(wb_event["Sheet1"], required=["Main Code", "Detail Code", "Descriptions"])
    unsched_desc = {
        clean_text(r.get("Detail Code", "")): clean_text(r.get("Descriptions", ""))
        for r in unscheduled_records
        if clean_text(r.get("Detail Code", ""))
    }

    master_rows: list[dict[str, str]] = []
    for row in data_summary:
        campaign_raw = clean_text(row.get("Campaign", ""))
        wbs_code = clean_text(row.get("WBS_ID", ""))
        dict_match = lvl5_dict.get(wbs_code, {})
        lvl2_code = clean_text(dict_match.get("LVL 2", "")) or clean_text(row.get("L2", ""))

        campaign_map = campaign_by_name.get(normalize_token(campaign_raw), {})
        if not campaign_map and lvl2_code:
            campaign_map = campaign_by_code.get(lvl2_code, {})

        field = map_field(row.get("Asset", ""))
        campaign_canonical = clean_text(campaign_map.get("campaign_id", ""))

        source_row_key = f"20260327_WBS_Data.xlsx|Data.Summary|{row['_source_excel_row']}|{wbs_code}|{campaign_raw}"
        source_row_id = hashlib.md5(source_row_key.encode("utf-8")).hexdigest()[:16]

        master_rows.append(
            {
                "source_file": "20260327_WBS_Data.xlsx",
                "source_sheet": "Data.Summary",
                "source_row_id": source_row_id,
                "field": field,
                "campaign_raw": campaign_raw,
                "campaign_canonical": campaign_canonical,
                "well_raw": "",
                "well_canonical": "",
                "wbs_code_raw": wbs_code,
                "wbs_lvl1": clean_text(dict_match.get("LVL 1", "")) or clean_text(row.get("L1", "")),
                "wbs_lvl2": lvl2_code,
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

    master_fields = [
        "source_file",
        "source_sheet",
        "source_row_id",
        "field",
        "campaign_raw",
        "campaign_canonical",
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
    ]
    write_csv(MASTER_PATH, master_rows, master_fields)

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for rec in master_rows:
        cls_key = "|".join([rec["field"], rec["wbs_lvl2"], rec["wbs_lvl3"], rec["wbs_lvl4"], rec["wbs_lvl5"]])
        grouped[cls_key].append(rec)

    lvl4_tag_votes: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for rec in master_rows:
        tag = clean_text(rec.get("tag_well_or_pad", ""))
        if tag in {"Well", "Pad"}:
            lvl4_tag_votes[(rec["field"], rec["wbs_lvl4"])][tag] += 1

    class_rows: list[dict[str, str]] = []
    for key, recs in sorted(grouped.items()):
        spend = sum(parse_float(r["cost_actual"]) for r in recs)
        rule_out = classify_row(recs[0], {})
        include_flag = "yes" if rule_out["classification"] == "well_tied" else "no"
        class_rows.append(
            {
                "classification_key": key,
                "field": recs[0]["field"],
                "wbs_code_lv5": recs[0]["wbs_code_raw"],
                "wbs_lvl2": recs[0]["wbs_lvl2"],
                "wbs_lvl3": recs[0]["wbs_lvl3"],
                "wbs_lvl4": recs[0]["wbs_lvl4"],
                "wbs_lvl5": recs[0]["wbs_lvl5"],
                "classification": rule_out["classification"],
                "classification_confidence": rule_out["classification_confidence"],
                "classification_rule_id": rule_out["classification_rule_id"],
                "classification_rule_text": rule_out["classification_rule_text"],
                "recommended_allocation_basis": rule_out["recommended_allocation_basis"],
                "include_for_modeling_initial": include_flag,
                "review_status": rule_out["review_status"],
                "review_notes": rule_out["review_notes"],
                "supporting_row_count": str(len(recs)),
                "supporting_cost_total": f"{spend:.6f}",
            }
        )

    class_fields = [
        "classification_key",
        "field",
        "wbs_code_lv5",
        "wbs_lvl2",
        "wbs_lvl3",
        "wbs_lvl4",
        "wbs_lvl5",
        "classification",
        "classification_confidence",
        "classification_rule_id",
        "classification_rule_text",
        "recommended_allocation_basis",
        "include_for_modeling_initial",
        "review_status",
        "review_notes",
        "supporting_row_count",
        "supporting_cost_total",
    ]
    write_csv(CLASSIFICATION_PATH, class_rows, class_fields)

    review_rows = []
    for row in class_rows:
        if row["review_status"] != "approved_auto":
            review_rows.append(
                {
                    "classification_key": row["classification_key"],
                    "field": row["field"],
                    "wbs_lvl5": row["wbs_lvl5"],
                    "reason_for_review": row["review_status"],
                    "observed_patterns": row["classification_rule_id"],
                    "supporting_row_count": row["supporting_row_count"],
                    "supporting_cost_total": row["supporting_cost_total"],
                    "suggested_default_classification": row["classification"],
                }
            )

    review_fields = [
        "classification_key",
        "field",
        "wbs_lvl5",
        "reason_for_review",
        "observed_patterns",
        "supporting_row_count",
        "supporting_cost_total",
        "suggested_default_classification",
    ]
    write_csv(REVIEW_QUEUE_PATH, review_rows, review_fields)

    # helper summary tables
    cost_by_class = defaultdict(float)
    count_by_class = Counter()
    cost_total = 0.0
    for row in class_rows:
        cls = row["classification"]
        spend = parse_float(row["supporting_cost_total"])
        count_by_class[cls] += 1
        cost_by_class[cls] += spend
        cost_total += spend

    summary_rows = []
    total_keys = sum(count_by_class.values())
    for cls in ["well_tied", "campaign_tied", "hybrid"]:
        key_count = count_by_class[cls]
        spend = cost_by_class[cls]
        summary_rows.append(
            {
                "classification": cls,
                "key_count": str(key_count),
                "key_share_pct": f"{(100.0 * key_count / total_keys) if total_keys else 0.0:.4f}",
                "cost_total": f"{spend:.6f}",
                "cost_share_pct": f"{(100.0 * spend / cost_total) if cost_total else 0.0:.4f}",
            }
        )
    write_csv(COST_SUMMARY_PATH, summary_rows, ["classification", "key_count", "key_share_pct", "cost_total", "cost_share_pct"])

    rule_coverage = Counter(row["classification_rule_id"] for row in class_rows)
    rule_rows = [{"classification_rule_id": k, "key_count": str(v)} for k, v in sorted(rule_coverage.items())]
    write_csv(RULE_COVERAGE_PATH, rule_rows, ["classification_rule_id", "key_count"])

    hybrid_tag_rows: list[dict[str, str]] = []
    for row in class_rows:
        if row["classification"] != "hybrid":
            continue
        lvl4_counter = lvl4_tag_votes.get((row["field"], row["wbs_lvl4"]), Counter())
        suggestion = "campaign"
        basis = "default_for_shared_or_unknown_scope"
        if lvl4_counter:
            top_tag, votes = lvl4_counter.most_common(1)[0]
            suggestion = "well" if top_tag == "Well" else "pad"
            basis = f"inferred_from_lvl4_siblings:{top_tag}({votes})"

        label_text = clean_text(row["wbs_lvl5"]).lower()
        if any(word in label_text for word in ["mobil", "demobil", "contingency", "camp", "support"]):
            suggestion = "campaign"
            basis = "keyword_campaign_shared_scope"
        elif any(word in label_text for word in ["drilling", "sidetrack", "service", "completion"]):
            suggestion = "well"
            basis = "keyword_well_operation_scope"

        hybrid_tag_rows.append(
            {
                "classification_key": row["classification_key"],
                "field": row["field"],
                "wbs_lvl4": row["wbs_lvl4"],
                "wbs_lvl5": row["wbs_lvl5"],
                "supporting_cost_total": row["supporting_cost_total"],
                "suggested_tag": suggestion,
                "suggestion_basis": basis,
            }
        )

    write_csv(
        HYBRID_TAG_REVIEW_PATH,
        sorted(hybrid_tag_rows, key=lambda r: parse_float(r["supporting_cost_total"]), reverse=True),
        ["classification_key", "field", "wbs_lvl4", "wbs_lvl5", "supporting_cost_total", "suggested_tag", "suggestion_basis"],
    )

    unmapped_campaigns = sum(1 for row in master_rows if row["mapping_status_campaign"] != "mapped")

    rulebook_lines = [
        "# WBS Lv.5 Classification Rulebook",
        "",
        "## Rule Table",
        "- `R1_TAG_WELL`: if `Tag_Well_or_Pad == Well` → `well_tied`, high confidence.",
        "- `R2_TAG_PAD`: if `Tag_Well_or_Pad == Pad` → `campaign_tied`, high confidence.",
        "- `R3_KEYWORD_CAMPAIGN`: campaign/shared keywords in Lv4/Lv5 labels → `campaign_tied`, medium confidence, review required.",
        "- `R4_KEYWORD_WELL`: well-operation keywords in Lv4/Lv5 labels → `well_tied`, medium confidence, review required.",
        "- `R5_FALLBACK_HYBRID`: default when deterministic evidence is absent → `hybrid`, low confidence, review required.",
        "",
        "## Exceptions / Known Limitations",
        "- Data.Summary provides campaign/WBS grain with limited explicit well linkage per cost row.",
        "- Event code and NPT class are preserved as explicit nullable fields in this phase.",
        "- All non-tag-based rules are automatically routed to the review queue.",
    ]
    RULEBOOK_REPORT.write_text("\n".join(rulebook_lines) + "\n")

    top_review = sorted(review_rows, key=lambda r: parse_float(r["supporting_cost_total"]), reverse=True)[:10]
    top_hybrid_tag = sorted(hybrid_tag_rows, key=lambda r: parse_float(r["supporting_cost_total"]), reverse=True)[:10]
    report_lines = [
        "# WBS Lv.5 Classification QA Report",
        "",
        "## Processing Coverage",
        f"- Total source rows processed (Lv.5-only from Data.Summary): **{len(master_rows)}**",
        f"- Total cost processed (USD): **{cost_total:,.2f}**",
        f"- Total unique Lv.5 classification keys: **{len(class_rows)}**",
        f"- Unmapped campaign rows: **{unmapped_campaigns}**",
        f"- Unmapped well rows: **{len(master_rows)}** (not available at source grain)",
        "",
        "## Classification Mix (Count + Spend)",
    ]
    for row in summary_rows:
        report_lines.append(
            f"- `{row['classification']}`: {row['key_count']} keys ({row['key_share_pct']}%), "
            f"USD {parse_float(row['cost_total']):,.2f} ({row['cost_share_pct']}%)"
        )

    low_conf = sum(1 for r in class_rows if r["classification_confidence"] == "low")
    review_count = sum(1 for r in class_rows if r["review_status"] != "approved_auto")
    report_lines.extend(
        [
            "",
            "## Uncertainty / Review",
            f"- Low-confidence keys: **{low_conf}**",
            f"- Keys requiring review: **{review_count}**",
            "",
            "## Top Ambiguous Items by Spend",
        ]
    )
    for item in top_review:
        report_lines.append(
            f"- `{item['classification_key']}` | suggested `{item['suggested_default_classification']}` | "
            f"USD {parse_float(item['supporting_cost_total']):,.2f}"
        )

    report_lines.extend(
        [
            "",
            "## Notes on Inconsistent Behavior",
            "- In this phase, inconsistency is proxied by absence of deterministic tag evidence, routed to `needs_review`.",
            "- No hidden allocations were applied for campaign/hybrid classes.",
            "",
            "## Top Hybrid Spend with Potential Tag Recommendation",
        ]
    )
    for item in top_hybrid_tag:
        report_lines.append(
            f"- `{item['classification_key']}` | potential `{item['suggested_tag']}` | "
            f"basis `{item['suggestion_basis']}` | USD {parse_float(item['supporting_cost_total']):,.2f}"
        )
    CLASSIFICATION_REPORT.write_text("\n".join(report_lines) + "\n")


if __name__ == "__main__":
    main()
