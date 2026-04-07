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
WELL_BRIDGE_PATH = PROCESSED_DIR / "wbs_row_to_well_bridge.csv"
WELL_INSTANCE_CONTEXT_PATH = PROCESSED_DIR / "well_instance_context.csv"
WELL_INSTANCE_EVENT_CONTEXT_PATH = PROCESSED_DIR / "well_instance_event_context.csv"
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
PHASE4_COVERAGE_REPORT = REPORTS_DIR / "phase4_plus_coverage_summary.md"

DASHBOARD_SHEET_NAME = "Dashboard_x"
DASHBOARD_SUMMARY_PATH = PROCESSED_DIR / "dashboard_x_summary_metrics.csv"
DASHBOARD_WELL_PATH = PROCESSED_DIR / "dashboard_x_cost_by_well.csv"
DASHBOARD_L3_PATH = PROCESSED_DIR / "dashboard_x_l3_breakdown.csv"
DASHBOARD_REPORT_PATH = REPORTS_DIR / "dashboard_x_snapshot_report.md"

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

SALAK_ORDER_LABEL_MAP = {
    "well_1": "AWI 21-8",
    "well_2": "AWI 21-7",
    "well_3": "AWI 3-9",
    "well_4": "AWI 23-1",
    "well_5": "AWI 23-2",
    "well_6": "AWI 2-7 ML",
    "well_7": "AWI 2-6",
    "well_8": "AWI 9-11",
    "well_9": "AWI 9-10",
}


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


def source_row_id(source_file: str, source_sheet: str, source_row: int, source_section: str, source_key: str) -> str:
    source_row_key = f"{source_file}|{source_sheet}|{source_row}|{source_section}|{source_key}"
    return hashlib.md5(source_row_key.encode("utf-8")).hexdigest()[:16]


def row_value(row: list[str], index: int) -> str:
    return clean_text(row[index]) if index < len(row) else ""


def dashboard_field_from_title(title: str) -> str:
    upper = clean_text(title).upper()
    if "SLK" in upper or "SALAK" in upper:
        return "SALAK"
    if "DRJ" in upper or "DARAJAT" in upper:
        return "DARAJAT"
    return ""


def build_dashboard_summary_rows(rows: list[list[str]]) -> list[dict[str, str]]:
    title = row_value(rows[0], 0) if rows and rows[0] else ""
    field = dashboard_field_from_title(title)
    summary_pairs = [
        (5, 0, "Total Budget (USD)", "executive_summary"),
        (5, 1, "Total Released (USD)", "executive_summary"),
        (5, 2, "Total Actual (USD)", "executive_summary"),
        (5, 3, "Total Committed (USD)", "executive_summary"),
        (8, 0, "Budget Utilization %", "executive_summary"),
        (8, 1, "Release Rate %", "executive_summary"),
        (8, 2, "Variance (Budget-Actual)", "executive_summary"),
        (8, 3, "Remaining Budget", "executive_summary"),
    ]
    output: list[dict[str, str]] = []
    for source_row, source_col, metric_name, metric_group in summary_pairs:
        value = row_value(rows[source_row - 1], source_col) if len(rows) >= source_row else ""
        output.append(
            {
                "field": field,
                "metric_group": metric_group,
                "metric_name": metric_name,
                "metric_value": value,
                "source_file": "20260327_WBS_Data.xlsx",
                "source_sheet": DASHBOARD_SHEET_NAME,
                "source_row": str(source_row),
                "source_row_id": source_row_id("20260327_WBS_Data.xlsx", DASHBOARD_SHEET_NAME, source_row, metric_group, metric_name),
            }
        )
    return output


def build_dashboard_cost_by_well_rows(rows: list[list[str]]) -> list[dict[str, str]]:
    header_idx = -1
    for idx, row in enumerate(rows):
        if row_value(row, 7) == "Well Name" and row_value(row, 8) == "Budget (USD)" and row_value(row, 9) == "Actual (USD)":
            header_idx = idx
            break
    if header_idx < 0:
        return []

    title = row_value(rows[0], 0) if rows and rows[0] else ""
    field = dashboard_field_from_title(title)
    output: list[dict[str, str]] = []
    for excel_row, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
        well_name = row_value(row, 7)
        if not well_name:
            break
        if well_name.startswith("📅") or well_name.startswith("🔍"):
            break
        output.append(
            {
                "field": field,
                "well_name": well_name,
                "budget_usd": row_value(row, 8),
                "actual_usd": row_value(row, 9),
                "pct_spent": row_value(row, 10),
                "status": row_value(row, 11),
                "source_file": "20260327_WBS_Data.xlsx",
                "source_sheet": DASHBOARD_SHEET_NAME,
                "source_row": str(excel_row),
                "source_row_id": source_row_id("20260327_WBS_Data.xlsx", DASHBOARD_SHEET_NAME, excel_row, "cost_by_well", well_name),
            }
        )
    return output


def build_dashboard_l3_rows(rows: list[list[str]]) -> list[dict[str, str]]:
    header_idx = -1
    for idx, row in enumerate(rows):
        if row_value(row, 0) == "L3 Category" and row_value(row, 1) == "Description":
            header_idx = idx
            break
    if header_idx < 0:
        return []

    title = row_value(rows[0], 0) if rows and rows[0] else ""
    field = dashboard_field_from_title(title)
    output: list[dict[str, str]] = []
    for excel_row, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
        l3_category = row_value(row, 0)
        description = row_value(row, 1)
        if not l3_category and not description:
            break
        if l3_category.startswith("📊") or l3_category.startswith("🔍"):
            break
        if not any([l3_category, description, row_value(row, 2), row_value(row, 3), row_value(row, 4), row_value(row, 5)]):
            continue
        output.append(
            {
                "field": field,
                "l3_category": l3_category,
                "description": description,
                "budget_usd": row_value(row, 2),
                "actual_usd": row_value(row, 3),
                "pct_spent": row_value(row, 4),
                "variance_usd": row_value(row, 5),
                "allocation_scope": "well" if description.upper().startswith("WELL COST") else "category",
                "source_file": "20260327_WBS_Data.xlsx",
                "source_sheet": DASHBOARD_SHEET_NAME,
                "source_row": str(excel_row),
                "source_row_id": source_row_id("20260327_WBS_Data.xlsx", DASHBOARD_SHEET_NAME, excel_row, "l3_breakdown", l3_category),
            }
        )
    return output


def write_dashboard_snapshot_report(summary_rows: list[dict[str, str]], well_rows: list[dict[str, str]], l3_rows: list[dict[str, str]]) -> None:
    lines = [
        "# Dashboard_x Snapshot Extract",
        "",
        "## Scope",
        "- Source sheet: `Dashboard_x` from `20260327_WBS_Data.xlsx`.",
        "- This extract preserves dashboard-style historical cost facts as auditable CSV rows.",
        "- The extract is a source snapshot, not a model output.",
        "",
        "## Extracted Sections",
        f"- summary metrics: **{len(summary_rows)}**",
        f"- cost by well rows: **{len(well_rows)}**",
        f"- L3 breakdown rows: **{len(l3_rows)}**",
        "",
        "## Notes",
        "- Field is inferred from the dashboard title (`SLK` -> `SALAK`, `DRJ` -> `DARAJAT`).",
        "- Each extracted row includes a deterministic `source_row_id` for lineage.",
        "- This snapshot is intended to expand the auditable historical pool used by downstream estimator work.",
    ]
    write_text(DASHBOARD_REPORT_PATH, "\n".join(lines) + "\n")


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


def normalize_well_alias(value: str | None) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"[_/]+", " ", text)
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compact_for_match(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]+", "", normalize_well_alias(value))


def compact_for_match_loose(value: str | None) -> str:
    strict = compact_for_match(value)
    return re.sub(r"\d+", lambda m: str(int(m.group(0))), strict) if strict else ""


def base_well_canonical(value: str | None) -> str:
    canonical = normalize_well_alias(value)
    return re.sub(r"\s+(RD|ML)$", "", canonical).strip() if canonical else ""


def build_well_instance_id(campaign_canonical: str, well_base: str) -> str:
    return f"{campaign_canonical}|{well_base}" if clean_text(campaign_canonical) and clean_text(well_base) else ""


def classify_deviation_type(well_text: str, note_text: str = "") -> str:
    combined = f"{clean_text(well_text)} {clean_text(note_text)}".upper()
    if "RD" in combined:
        return "redrill"
    if "SIDETRACK" in combined or "SIDE-TRACK" in combined:
        return "sidetrack"
    if "ML" in combined:
        return "multileg"
    if "LIH" in combined:
        return "LIH_affected"
    if "STUCK" in combined:
        return "stuck_related"
    if clean_text(combined):
        return "standard"
    return "unknown"


def normalize_deviation_type(value: str) -> str:
    text = clean_text(value).lower().replace("-", "").replace("_", "").replace(" ", "")
    if text in {"sidetrack", "sidetracked"}:
        return "sidetrack"
    if text in {"redrill", "re drill", "redrilled"}:
        return "redrill"
    if text in {"multileg", "multilateral"}:
        return "multileg"
    if text in {"lihaffected", "lih"}:
        return "LIH_affected"
    if text in {"stuckrelated", "stuck"}:
        return "stuck_related"
    if text in {"standard", "normal"}:
        return "standard"
    return clean_text(value)


def candidate_aliases_from_text(text: str) -> list[str]:
    candidates: list[str] = []

    generic = re.findall(r"\bwell[\s\-_]*(\d{1,2})\b", text, flags=re.IGNORECASE)
    for n in generic:
        candidates.append(f"well_{int(n)}")

    pattern = re.compile(
        r"\b(?:AWI\s*\d{1,2}\s*-\s*\d{1,2}(?:\s*(?:ML|RD))?|DRJ(?:-STEAM)?\s*-?\s*\d+|SF\s*-?\s*\d+|\d{1,2}\s*-\s*\d{1,2}(?:\s*(?:ML|RD))?)\b",
        flags=re.IGNORECASE,
    )
    candidates.extend(clean_text(m.group(0)) for m in pattern.finditer(text))

    output: list[str] = []
    for candidate in candidates:
        if not clean_text(candidate):
            continue
        if candidate.lower().startswith("well_"):
            output.append(candidate.lower())
        else:
            output.append(normalize_well_alias(candidate))
    return output


def load_well_lookup() -> tuple[dict[tuple[str, str], set[str]], dict[tuple[str, str], set[str]], dict[str, str]]:
    by_campaign: dict[tuple[str, str], set[str]] = defaultdict(set)
    by_field: dict[tuple[str, str], set[str]] = defaultdict(set)
    campaign_to_field: dict[str, str] = {}

    # campaign-specific aliases
    with (PROCESSED_DIR / "canonical_well_mapping.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            alias = normalize_well_alias(row.get("well_alias", ""))
            canonical = normalize_well_alias(row.get("well_canonical", ""))
            campaign_code = clean_text(row.get("campaign_code", ""))
            if not alias or not canonical:
                continue
            if campaign_code:
                by_campaign[(campaign_code, compact_for_match(alias))].add(canonical)
                by_campaign[(campaign_code, compact_for_match_loose(alias))].add(canonical)

    # field fallback aliases
    with (PROCESSED_DIR / "well_master.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            campaign_code = clean_text(row.get("campaign_code", ""))
            field = clean_text(row.get("field", ""))
            canonical = normalize_well_alias(row.get("well_canonical", ""))
            if campaign_code and field:
                campaign_to_field[campaign_code] = field
            if field and canonical:
                by_field[(field, compact_for_match(canonical))].add(canonical)
                by_field[(field, compact_for_match_loose(canonical))].add(canonical)

    with (PROCESSED_DIR / "well_alias_lookup.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            alias = normalize_well_alias(row.get("well_alias", ""))
            canonical = normalize_well_alias(row.get("well_canonical", ""))
            if not alias or not canonical:
                continue
            # assign to all matching campaign fields from well_master fallback
            for field in {"DARAJAT", "SALAK"}:
                by_field[(field, compact_for_match(alias))].add(canonical)
                by_field[(field, compact_for_match_loose(alias))].add(canonical)
    return by_campaign, by_field, campaign_to_field


def append_alias_to_label(label: str, alias: str) -> str:
    base = clean_text(label)
    alias_clean = clean_text(alias)
    if not alias_clean:
        return base
    if compact_for_match(alias_clean) in compact_for_match(base):
        return base
    return clean_text(f"{base} {alias_clean}")


def resolve_well_for_row(
    row: dict[str, str],
    campaign_code: str,
    campaign_canonical: str,
    by_campaign: dict[tuple[str, str], set[str]],
    by_field: dict[tuple[str, str], set[str]],
    campaign_to_field: dict[str, str],
) -> dict[str, str]:
    field = map_field(row.get("Asset", ""))
    source_text = " | ".join([clean_text(row.get("Description", "")), clean_text(row.get("L4", "")), clean_text(row.get("L5", ""))])
    well_name = normalize_well_alias(row.get("Well Name", ""))
    label = clean_text(row.get("Description", ""))

    def resolve_alias(alias: str, prefer_campaign: bool = True) -> tuple[str, str]:
        key_strict = compact_for_match(alias)
        key_loose = compact_for_match_loose(alias)
        if prefer_campaign and campaign_code:
            campaign_hits = by_campaign.get((campaign_code, key_strict), set()) | by_campaign.get((campaign_code, key_loose), set())
            if len(campaign_hits) == 1:
                return next(iter(campaign_hits)), "campaign_unique"
            if len(campaign_hits) > 1:
                return "", "ambiguous"
        field_hits = by_field.get((field, key_strict), set()) | by_field.get((field, key_loose), set())
        if len(field_hits) == 1:
            return next(iter(field_hits)), "field_unique"
        if len(field_hits) > 1:
            return "", "ambiguous"
        return "", "none"

    if well_name:
        # ordered labels for SALAK_2025_2026 are allowed through well-name column as well
        order_token = normalize_well_alias(well_name).lower()
        if campaign_canonical == "SALAK_2025_2026" and order_token in SALAK_ORDER_LABEL_MAP:
            canonical = SALAK_ORDER_LABEL_MAP[order_token]
            return {
                "well_raw": order_token,
                "well_canonical": canonical,
                "mapping_status_well": "mapped_from_order_label",
                "mapping_method": "ordered_label_map",
                "wbs_label_raw": append_alias_to_label(label, order_token),
                "source_text_used": source_text,
                "confidence": "high",
            }
        canonical, mode = resolve_alias(well_name, prefer_campaign=True)
        if mode == "campaign_unique":
            return {
                "well_raw": well_name,
                "well_canonical": canonical,
                "mapping_status_well": "mapped_from_well_name",
                "mapping_method": "campaign_alias_match",
                "wbs_label_raw": append_alias_to_label(label, well_name),
                "source_text_used": source_text,
                "confidence": "high",
            }
        if mode == "field_unique":
            return {
                "well_raw": well_name,
                "well_canonical": canonical,
                "mapping_status_well": "mapped_from_alias_fallback",
                "mapping_method": "field_alias_unique_fallback",
                "wbs_label_raw": append_alias_to_label(label, well_name),
                "source_text_used": source_text,
                "confidence": "medium",
            }
        if mode == "ambiguous":
            return {
                "well_raw": well_name,
                "well_canonical": "",
                "mapping_status_well": "ambiguous_alias_match",
                "mapping_method": "ambiguous_alias_match",
                "wbs_label_raw": append_alias_to_label(label, well_name),
                "source_text_used": source_text,
                "confidence": "low",
            }

    for alias in candidate_aliases_from_text(source_text):
        token = alias.lower()
        if campaign_canonical == "SALAK_2025_2026" and token in SALAK_ORDER_LABEL_MAP:
            canonical = SALAK_ORDER_LABEL_MAP[token]
            return {
                "well_raw": token,
                "well_canonical": canonical,
                "mapping_status_well": "mapped_from_order_label",
                "mapping_method": "ordered_label_map",
                "wbs_label_raw": append_alias_to_label(label, token),
                "source_text_used": source_text,
                "confidence": "high",
            }
        canonical, mode = resolve_alias(alias, prefer_campaign=True)
        if mode == "campaign_unique":
            return {
                "well_raw": alias,
                "well_canonical": canonical,
                "mapping_status_well": "mapped_from_label_alias",
                "mapping_method": "label_alias_campaign_match",
                "wbs_label_raw": append_alias_to_label(label, alias),
                "source_text_used": source_text,
                "confidence": "high",
            }
        if mode == "field_unique":
            return {
                "well_raw": alias,
                "well_canonical": canonical,
                "mapping_status_well": "mapped_from_alias_fallback",
                "mapping_method": "label_alias_field_unique_fallback",
                "wbs_label_raw": append_alias_to_label(label, alias),
                "source_text_used": source_text,
                "confidence": "medium",
            }
        if mode == "ambiguous":
            return {
                "well_raw": alias,
                "well_canonical": "",
                "mapping_status_well": "ambiguous_alias_match",
                "mapping_method": "ambiguous_alias_match",
                "wbs_label_raw": append_alias_to_label(label, alias),
                "source_text_used": source_text,
                "confidence": "low",
            }

    return {
        "well_raw": well_name,
        "well_canonical": "",
        "mapping_status_well": "not_available_at_source_grain",
        "mapping_method": "none",
        "wbs_label_raw": label,
        "source_text_used": source_text,
        "confidence": "low",
    }


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
    well_lookup_by_campaign: dict[tuple[str, str], set[str]],
    well_lookup_by_field: dict[tuple[str, str], set[str]],
    campaign_to_field: dict[str, str],
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
        well_resolution = resolve_well_for_row(
            row,
            campaign_code=campaign_code,
            campaign_canonical=campaign_canonical,
            by_campaign=well_lookup_by_campaign,
            by_field=well_lookup_by_field,
            campaign_to_field=campaign_to_field,
        )
        resolved_well_canonical = clean_text(well_resolution.get("well_canonical", ""))
        well_base = base_well_canonical(resolved_well_canonical)
        well_instance_id = build_well_instance_id(campaign_canonical, well_base)

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
                "well_raw": clean_text(well_resolution.get("well_raw", "")),
                "well_canonical": resolved_well_canonical,
                "well_base_canonical": well_base,
                "well_instance_id": well_instance_id,
                "wbs_code_raw": wbs_code,
                "wbs_lvl1": clean_text(dict_match.get("LVL 1", "")) or clean_text(row.get("L1", "")),
                "wbs_lvl2": clean_text(dict_match.get("LVL 2", "")) or clean_text(row.get("L2", "")),
                "wbs_lvl3": clean_text(dict_match.get("LVL 3", "")) or clean_text(row.get("L3", "")),
                "wbs_lvl4": clean_text(dict_match.get("LVL 4", "")) or clean_text(row.get("L4", "")),
                "wbs_lvl5": clean_text(dict_match.get("LVL 5", "")) or clean_text(row.get("L5", "")),
                "wbs_label_raw": clean_text(well_resolution.get("wbs_label_raw", "")),
                "cost_actual": f"{parse_float(row.get('ACTUAL, USD', '0')):.6f}",
                "currency": "USD",
                "event_code_raw": "",
                "event_code_desc": "",
                "npt_class": "",
                "mapping_status_campaign": "mapped" if campaign_canonical else "unmapped",
                "mapping_status_well": clean_text(well_resolution.get("mapping_status_well", "not_available_at_source_grain")),
                "mapping_method": clean_text(well_resolution.get("mapping_method", "none")),
                "mapping_confidence": clean_text(well_resolution.get("confidence", "low")),
                "source_text_used": clean_text(well_resolution.get("source_text_used", "")),
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


def build_well_bridge_rows(master_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in master_rows:
        rows.append(
            {
                "source_row_id": row["source_row_id"],
                "field": row["field"],
                "campaign_canonical": row["campaign_canonical"],
                "well_raw": row.get("well_raw", ""),
                "well_base_canonical": row.get("well_base_canonical", ""),
                "well_instance_id": row.get("well_instance_id", ""),
                "well_canonical": row.get("well_canonical", ""),
                "mapping_method": row.get("mapping_method", ""),
                "confidence": row.get("mapping_confidence", ""),
                "source_text_used": row.get("source_text_used", ""),
            }
        )
    return rows


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
            "- `wbs_lv5_master.csv` is complete for hierarchy and campaign mapping, with deterministic well-attribution capture where auditable from `Well Name` and label aliases.",
            "- `event_code_raw` and `event_code_desc` remain blank in this Define layer because the unscheduled-event workbook is not row-addressable to `Data.Summary` Lv5 cost rows.",
            "- These limitations do not block Phase 3 design, but they do constrain later well-level driver validation until a richer source grain is introduced.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_salak_2021_scope_investigation(wb_data: dict[str, list[list[str]]], campaign_by_code: dict[str, dict[str, str]]) -> None:
    data_summary_rows = sheet_to_records(
        wb_data["Data.Summary"],
        required=["Asset", "Campaign", "WBS_ID", "Description", "ACTUAL, USD", "L1", "L2", "L3", "L4", "L5"],
    )
    data_summary_rows = [row for row in data_summary_rows if clean_text(row.get("L5", ""))]

    salak_2021_code = "E540-30101-D20001"
    salak_2021_labels = {
        clean_text(v.get("campaign_name_raw", "")).upper()
        for v in campaign_by_code.values()
        if clean_text(v.get("campaign_code", "")) == salak_2021_code
    }
    salak_2021_labels.update({"SALAK CAMPAIGN 2021", "SLK 2021"})

    salak_2021_rows = [r for r in data_summary_rows if clean_text(r.get("Campaign", "")).upper() in salak_2021_labels]
    in_scope_rows = [r for r in data_summary_rows if clean_text(r.get("Campaign", "")).upper() in IN_SCOPE_CAMPAIGN_LABELS]

    reference_sheets: list[str] = []
    for sheet, rows in wb_data.items():
        if sheet == "Data.Summary":
            continue
        joined = " ".join(" ".join(r) for r in rows[:250]).upper()
        if "SALAK" in joined and "2021" in joined:
            reference_sheets.append(sheet)

    lines = [
        "# SALAK_2021 Scope Investigation",
        "",
        "## Objective",
        "Assess whether SALAK_2021 can be moved from `legacy_reference` to `in_scope` for the Phase 4 pipeline.",
        "",
        "## Evidence",
        f"- Data.Summary Lv5 cost rows mapped to SALAK_2021 labels: **{len(salak_2021_rows)}**.",
        f"- Data.Summary Lv5 cost rows for current in-scope labels (`DRJ 2022`, `DRJ 2023`, `SLK 2025`): **{len(in_scope_rows)}**.",
        f"- Non-Data.Summary sheets with SALAK 2021 references: **{', '.join(sorted(reference_sheets)) or 'none_detected'}**.",
        "",
        "## Assessment",
        "- Current Phase 4 ingestion contract requires cost-bearing Lv5 rows in `Data.Summary`.",
        "- SALAK_2021 appears as campaign/well reference context outside the active in-scope cost-bearing Lv5 path.",
        "",
        "## Recommendation",
        "- Keep `SALAK_2021` as **`legacy_reference`** in this phase.",
        "- Do not promote to `in_scope` and do not synthesize SALAK_2021 cost rows unless authoritative Lv5 cost-bearing rows are available.",
    ]
    (REPORTS_DIR / "salak_2021_scope_investigation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_well_instance_context_rows(
    wb_data: dict[str, list[list[str]]],
    campaign_by_name: dict[str, dict[str, str]],
    campaign_by_code: dict[str, dict[str, str]],
    by_campaign: dict[tuple[str, str], set[str]],
    by_field: dict[tuple[str, str], set[str]],
) -> list[dict[str, str]]:
    rows = sheet_to_records(
        wb_data["WellView.Data"],
        required=["Asset", "Drilling Campaign", "Well Name SAP", "Actual Depth (ft MD)", "Actual Days (days)", "NPT (days)"],
        optional=["Well Name Well View"],
    )
    manual_deviation_override: dict[str, str] = {}
    if WELL_INSTANCE_CONTEXT_PATH.exists():
        for existing in read_csv_rows(WELL_INSTANCE_CONTEXT_PATH):
            canonical = normalize_well_alias(existing.get("well_canonical", ""))
            if not canonical:
                continue
            normalized = normalize_deviation_type(existing.get("deviation_type", ""))
            if normalized and normalized != "standard":
                manual_deviation_override[canonical] = existing.get("deviation_type", "")

    out: list[dict[str, str]] = []
    for row in rows:
        field = map_field(row.get("Asset", ""))
        campaign_map, _ = resolve_campaign_mapping(row.get("Drilling Campaign", ""), campaign_by_name, campaign_by_code)
        campaign_code = clean_text(campaign_map.get("campaign_code", ""))
        campaign_canonical = clean_text(campaign_map.get("campaign_id", ""))
        alias = normalize_well_alias(row.get("Well Name SAP", "") or row.get("Well Name Well View", ""))

        campaign_hits = by_campaign.get((campaign_code, compact_for_match(alias)), set()) if campaign_code else set()
        field_hits = by_field.get((field, compact_for_match(alias)), set())
        hits = campaign_hits or field_hits
        canonical = sorted(hits)[0] if len(hits) == 1 else ""
        confidence = "high" if len(campaign_hits) == 1 else ("medium" if len(field_hits) == 1 else "low")
        well_base = base_well_canonical(canonical)
        well_instance_id = build_well_instance_id(campaign_canonical, well_base)
        deviation = classify_deviation_type(alias, row.get("Well Name Well View", ""))
        if canonical in manual_deviation_override:
            deviation = manual_deviation_override[canonical]
        out.append(
            {
                "field": field,
                "campaign_canonical": campaign_canonical,
                "well_base_canonical": well_base,
                "well_instance_id": well_instance_id,
                "well_canonical": canonical,
                "actual_depth": f"{parse_float(row.get('Actual Depth (ft MD)', '0')):.6f}",
                "actual_days": f"{parse_float(row.get('Actual Days (days)', '0')):.6f}",
                "npt_days": f"{parse_float(row.get('NPT (days)', '0')):.6f}",
                "deviation_type": deviation,
                "source_sheet": "WellView.Data",
                "confidence": confidence,
                "notes": clean_text(row.get("Well Name Well View", "")),
            }
        )
    return out


def build_well_instance_event_context_rows(
    wb_data: dict[str, list[list[str]]],
    by_campaign: dict[tuple[str, str], set[str]],
    by_field: dict[tuple[str, str], set[str]],
) -> list[dict[str, str]]:
    rows = sheet_to_records(
        wb_data["3. NPT.Data"],
        required=["Well Name", "Event Reference No.", "Event Type", "Unsch Maj Cat", "Unscheduled Detail", "Dur (Net) (hr)"],
        optional=["Job Cat"],
    )

    # derive campaign candidates from well_master
    well_master_rows = read_csv_rows(PROCESSED_DIR / "well_master.csv")
    campaign_by_well: dict[str, set[str]] = defaultdict(set)
    field_by_campaign: dict[str, str] = {}
    for wm in well_master_rows:
        canonical = normalize_well_alias(wm.get("well_canonical", ""))
        campaign = clean_text(wm.get("campaign_id", ""))
        if canonical and campaign:
            campaign_by_well[canonical].add(campaign)
        if campaign:
            field_by_campaign[campaign] = clean_text(wm.get("field", ""))

    # allow manual context updates to flow into NPT event context mapping
    deviation_by_well: dict[str, str] = {}
    if WELL_INSTANCE_CONTEXT_PATH.exists():
        for context_row in read_csv_rows(WELL_INSTANCE_CONTEXT_PATH):
            canonical = normalize_well_alias(context_row.get("well_canonical", ""))
            if not canonical:
                continue
            normalized = normalize_deviation_type(context_row.get("deviation_type", ""))
            if normalized:
                deviation_by_well[canonical] = normalized

    out: list[dict[str, str]] = []
    for row in rows:
        alias = normalize_well_alias(row.get("Well Name", ""))
        # no explicit campaign in NPT row, so this is context-level bridge
        # map alias by any known canonical candidate
        candidates = set()
        for field in {"DARAJAT", "SALAK"}:
            candidates |= by_field.get((field, compact_for_match(alias)), set())
        canonical = sorted(candidates)[0] if len(candidates) == 1 else ""
        candidate_campaigns = campaign_by_well.get(canonical, set()) if canonical else set()
        campaign_canonical = sorted(candidate_campaigns)[0] if len(candidate_campaigns) == 1 else ""
        field = field_by_campaign.get(campaign_canonical, "")
        well_base = base_well_canonical(canonical)
        well_instance_id = build_well_instance_id(campaign_canonical, well_base)
        detail = clean_text(row.get("Unscheduled Detail", ""))
        deviation = classify_deviation_type(alias, detail)
        well_context_deviation = deviation_by_well.get(canonical, "")
        if well_context_deviation == "sidetrack":
            deviation = "sidetrack"

        confidence = "low"
        if canonical and campaign_canonical and clean_text(row.get("Event Reference No.", "")):
            confidence = "medium"
        if canonical and campaign_canonical and clean_text(row.get("Event Reference No.", "")) and clean_text(row.get("Job Cat", "")):
            confidence = "high"

        out.append(
            {
                "field": field,
                "campaign_canonical": campaign_canonical,
                "well_base_canonical": well_base,
                "well_instance_id": well_instance_id,
                "well_canonical": canonical,
                "event_ref_no": clean_text(row.get("Event Reference No.", "")),
                "event_type": clean_text(row.get("Event Type", "")),
                "event_major_category": clean_text(row.get("Unsch Maj Cat", "")),
                "event_detail": detail,
                "event_duration_days": f"{(parse_float(row.get('Dur (Net) (hr)', '0')) / 24.0):.6f}",
                "deviation_type": deviation,
                "mapping_method": "well_alias_context_bridge",
                "confidence": confidence,
                "source_text_used": clean_text(row.get("Well Name", "")),
            }
        )
    return out


def write_phase4_plus_coverage_summary(
    master_rows: list[dict[str, str]],
    bridge_rows: list[dict[str, str]],
    event_rows: list[dict[str, str]],
    context_rows: list[dict[str, str]],
) -> None:
    total = len(master_rows)
    well_raw_after = sum(1 for r in master_rows if clean_text(r.get("well_raw", "")))
    well_canon_after = sum(1 for r in master_rows if clean_text(r.get("well_canonical", "")))
    direct_well_name = sum(1 for r in master_rows if clean_text(r.get("mapping_status_well", "")) == "mapped_from_well_name")
    confidence_counts = Counter(clean_text(r.get("confidence", "")).lower() or "unknown" for r in event_rows)
    deviation_counts = Counter(normalize_deviation_type(r.get("deviation_type", "")) or "unknown" for r in context_rows)

    lines = [
        "# Phase 4 Plus Coverage Summary",
        "",
        "## Before vs After (current run reference)",
        f"- populated `well_raw` rows before: **0** (historical pre-remediation baseline).",
        f"- populated `well_raw` rows after: **{well_raw_after} / {total}**.",
        f"- populated `well_canonical` rows before: **0** (historical pre-remediation baseline).",
        f"- populated `well_canonical` rows after: **{well_canon_after} / {total}**.",
        f"- rows mapped from direct `Well Name`: **{direct_well_name}**.",
        f"- rows in `wbs_row_to_well_bridge.csv`: **{len(bridge_rows)}**.",
        f"- rows in `well_instance_event_context.csv`: **{len(event_rows)}**.",
        "",
        "## Event mapping confidence tiers",
        f"- high: **{confidence_counts.get('high', 0)}**",
        f"- medium: **{confidence_counts.get('medium', 0)}**",
        f"- low: **{confidence_counts.get('low', 0)}**",
        "",
        "## Deviation type counts (well context)",
    ]
    for key in ["standard", "redrill", "sidetrack", "multileg", "LIH_affected", "stuck_related", "unknown"]:
        lines.append(f"- {key}: **{deviation_counts.get(key, 0)}**")

    lines.extend(
        [
            "",
            "## Notes",
            "- `3. NPT.Data` is bridged as well-instance event context; direct row-level WBS event fill is not asserted.",
            "- `event_code_raw` remains unchanged unless explicit row-level evidence exists.",
        ]
    )
    write_text(PHASE4_COVERAGE_REPORT, "\n".join(lines) + "\n")


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

    if DASHBOARD_SHEET_NAME in wb_data:
        dashboard_rows = wb_data[DASHBOARD_SHEET_NAME]
        dashboard_summary_rows = build_dashboard_summary_rows(dashboard_rows)
        dashboard_well_rows = build_dashboard_cost_by_well_rows(dashboard_rows)
        dashboard_l3_rows = build_dashboard_l3_rows(dashboard_rows)
        write_csv(
            DASHBOARD_SUMMARY_PATH,
            dashboard_summary_rows,
            ["field", "metric_group", "metric_name", "metric_value", "source_file", "source_sheet", "source_row", "source_row_id"],
        )
        write_csv(
            DASHBOARD_WELL_PATH,
            dashboard_well_rows,
            ["field", "well_name", "budget_usd", "actual_usd", "pct_spent", "status", "source_file", "source_sheet", "source_row", "source_row_id"],
        )
        write_csv(
            DASHBOARD_L3_PATH,
            dashboard_l3_rows,
            ["field", "l3_category", "description", "budget_usd", "actual_usd", "pct_spent", "variance_usd", "allocation_scope", "source_file", "source_sheet", "source_row", "source_row_id"],
        )
        write_dashboard_snapshot_report(dashboard_summary_rows, dashboard_well_rows, dashboard_l3_rows)

    data_summary = sheet_to_records(
        wb_data["Data.Summary"],
        required=["Asset", "Campaign", "WBS_ID", "Description", "ACTUAL, USD", "L1", "L2", "L3", "L4", "L5"],
        optional=["Well Name"],
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
    well_lookup_by_campaign, well_lookup_by_field, campaign_to_field = load_well_lookup()
    policy_rows = load_policy_rows()

    master_rows = build_master_rows(
        data_summary,
        lvl5_dict,
        campaign_by_name,
        campaign_by_code,
        well_lookup_by_campaign,
        well_lookup_by_field,
        campaign_to_field,
    )
    class_rows = build_class_rows(master_rows, policy_rows)
    bridge_rows = build_well_bridge_rows(master_rows)
    well_instance_context_rows = build_well_instance_context_rows(
        wb_data,
        campaign_by_name,
        campaign_by_code,
        well_lookup_by_campaign,
        well_lookup_by_field,
    )
    well_instance_event_rows = build_well_instance_event_context_rows(
        wb_data,
        well_lookup_by_campaign,
        well_lookup_by_field,
    )
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
            "well_base_canonical",
            "well_instance_id",
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
            "mapping_method",
            "mapping_confidence",
            "source_text_used",
            "tag_well_or_pad",
            "tag_lvl5",
        ],
    )
    write_csv(
        WELL_BRIDGE_PATH,
        bridge_rows,
        [
            "source_row_id",
            "field",
            "campaign_canonical",
            "well_raw",
            "well_base_canonical",
            "well_instance_id",
            "well_canonical",
            "mapping_method",
            "confidence",
            "source_text_used",
        ],
    )
    write_csv(
        WELL_INSTANCE_CONTEXT_PATH,
        well_instance_context_rows,
        [
            "field",
            "campaign_canonical",
            "well_base_canonical",
            "well_instance_id",
            "well_canonical",
            "actual_depth",
            "actual_days",
            "npt_days",
            "deviation_type",
            "source_sheet",
            "confidence",
            "notes",
        ],
    )
    write_csv(
        WELL_INSTANCE_EVENT_CONTEXT_PATH,
        well_instance_event_rows,
        [
            "field",
            "campaign_canonical",
            "well_base_canonical",
            "well_instance_id",
            "well_canonical",
            "event_ref_no",
            "event_type",
            "event_major_category",
            "event_detail",
            "event_duration_days",
            "deviation_type",
            "mapping_method",
            "confidence",
            "source_text_used",
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
    write_salak_2021_scope_investigation(wb_data, campaign_by_code)
    write_phase4_plus_coverage_summary(master_rows, bridge_rows, well_instance_event_rows, well_instance_context_rows)
    print("Wrote WBS Lv.5 driver alignment artifacts.")


if __name__ == "__main__":
    main()
