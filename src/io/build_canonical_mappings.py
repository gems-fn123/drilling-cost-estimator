from __future__ import annotations

import json
import logging
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

from src.config import CAMPAIGN_LABEL_TO_CODE, PROCESSED, RAW_DIR, REPORTS, ROOT
from src.utils import read_csv, write_csv

log = logging.getLogger(__name__)

PROCESSED_DIR = PROCESSED
REPORTS_DIR = REPORTS
REPORT_PATH = REPORTS / "well_master_build_report.md"
SYNTH_REPORT_PATH = REPORTS / "synthetic_placeholder_method.md"
SCOPE_REPORT_PATH = REPORTS / "unit_price_scope_coverage.md"

CAMPAIGN_MAPPING_FIELDS = [
    "campaign_code",
    "campaign_id",
    "campaign_name",
    "campaign_name_raw",
    "field",
    "campaign_wbs_code",
    "estimator_scope",
    "include_for_estimator",
    "start_date",
    "end_date",
    "actual_cost_total",
    "source_file",
    "source_sheet",
]

WELL_MASTER_FIELDS = [
    "well_id",
    "well_name",
    "well_canonical",
    "well_aliases",
    "field",
    "campaign_code",
    "campaign_id",
    "well_sequence_in_campaign",
    "well_order_label",
    "well_order_basis",
    "well_order_note",
    "status",
    "region",
    "operator",
    "include_for_estimator",
    "include_for_well_training",
    "training_note",
]

LOOKUP_FIELDS = [
    "well_alias",
    "well_canonical",
    "source_sheet",
    "alias_type",
    "resolution_method",
    "is_modeling_master",
]

SALAK_2025_ORDER = [
    ("AWI 21-8", 1, "well_1"),
    ("AWI 21-7", 2, "well_2"),
    ("AWI 3-9", 3, "well_3"),
    ("AWI 23-1", 4, "well_4"),
    ("AWI 23-2", 5, "well_5"),
    ("AWI 2-7 ML", 6, "well_6"),
    ("AWI 2-6", 7, "well_7"),
    ("AWI 9-11", 8, "well_8"),
    ("AWI 9-10", 9, "well_9"),  # alias AWI 9-10RD canonicalized to AWI 9-10
]

NS_MAIN = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_PKG = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}
ZIP_MAGIC = b"PK\x03\x04"
OLE_MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"

DASHBOARD_WORKBOOK = "20260422_Data for Dashboard.xlsx"

CANONICAL_WELL_MAPPING_FIELDS = [
    "well_alias",
    "well_canonical",
    "campaign_code",
    "campaign_id",
    "estimator_scope",
    "include_for_estimator",
    "include_for_well_training",
    "source_sheet",
    "note",
    "well_sequence_in_campaign",
    "well_order_label",
    "well_order_basis",
    "well_order_note",
]

OFFICIAL_CAMPAIGNS = {
    "E530-30101-D225301": {"campaign_id": "DARAJAT_2022", "field": "DARAJAT", "scope": "in_scope"},
    "E530-30101-D235301": {"campaign_id": "DARAJAT_2023_2024", "field": "DARAJAT", "scope": "in_scope"},
    "E540-30101-D245401": {"campaign_id": "SALAK_2025_2026", "field": "SALAK", "scope": "in_scope"},
    "E530-30101-D19001": {"campaign_id": "DARAJAT_2019", "field": "DARAJAT", "scope": "in_scope"},
    "E540-30101-D20001": {"campaign_id": "SALAK_2021", "field": "SALAK", "scope": "in_scope"},
    "E500-2-0-8501-185003": {"campaign_id": "WAYANG_WINDU_2018", "field": "WAYANG_WINDU", "scope": "in_scope"},
    "E500-30101-D205011": {"campaign_id": "WAYANG_WINDU_2021", "field": "WAYANG_WINDU", "scope": "in_scope"},
}

WELL_ALIAS_PAIRS = [
    ("14-1", "DRJ-51"),
    ("14-2", "DRJ-52"),
    ("20-1", "DRJ-50"),
    ("SF-1", "DRJ-49"),
    ("SF-ML", "DRJ-38"),
    ("DRJ-38RD", "DRJ-38"),
    ("DRJ-44OH", "DRJ-44"),
    ("DRJ-45OH", "DRJ-45"),
    ("DRJ-46OH", "DRJ-46"),
    ("DRJ-47OH", "DRJ-47"),
    ("DRJ-49OH", "DRJ-49"),
    ("DRJ-50OH", "DRJ-50"),
    ("DRJ-51OH", "DRJ-51"),
    ("DRJ-52OH", "DRJ-52"),
    ("DRJ-Steam 6", "DRJ-53"),
    ("DRJ-Steam 2", "DRJ-54"),
    ("DRJ-Steam 3", "DRJ-55"),
    ("DRJ-Steam 4", "DRJ-56"),
    ("DRJ-Steam 5", "DRJ-57"),
    ("AWI 9-10RD", "AWI 9-10"),
]


SYNTHETIC_CAMPAIGNS = [
    {"synthetic_campaign_id": "SLK_2020", "field": "SALAK", "target_year": 2020},
    {"synthetic_campaign_id": "DRJ_2019", "field": "DARAJAT", "target_year": 2019},
    {"synthetic_campaign_id": "SLK_2012", "field": "SALAK", "target_year": 2012},
    {"synthetic_campaign_id": "DRJ_2011", "field": "DARAJAT", "target_year": 2011},
    {"synthetic_campaign_id": "SLK_2026", "field": "SALAK", "target_year": 2026},
    {"synthetic_campaign_id": "DRJ_2027", "field": "DARAJAT", "target_year": 2027},
]

# Local macro lookup (replaceable later with external official data source pulls).
CPI_INDEX_BY_YEAR = {
    2011: 224.9,
    2012: 229.6,
    2019: 255.7,
    2020: 258.8,
    2022: 292.7,
    2023: 305.3,
    2025: 318.0,
    2026: 324.0,
    2027: 330.0,
}
BRENT_BY_YEAR = {
    2011: 111.3,
    2012: 111.6,
    2019: 64.3,
    2020: 41.8,
    2022: 100.9,
    2023: 82.2,
    2025: 79.0,
    2026: 80.0,
    2027: 81.0,
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip()


def normalize_well(name: str) -> str:
    return re.sub(r"\s*-\s*", "-", clean_text(name).upper())


def col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def _read_zip_xlsx(path: Path) -> dict[str, list[list[str]]]:
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


def _read_legacy_xls(path: Path) -> dict[str, list[list[str]]]:
    try:
        import xlrd
    except ImportError as exc:  # pragma: no cover - environment-dependent dependency
        raise RuntimeError(
            "Legacy Excel format detected (non-zip workbook). Install 'xlrd' to read this file type."
        ) from exc

    sheets: dict[str, list[list[str]]] = {}
    workbook = xlrd.open_workbook(str(path))
    for sheet in workbook.sheets():
        rows: list[list[str]] = []
        for row_idx in range(sheet.nrows):
            dense: list[str] = []
            for value in sheet.row_values(row_idx):
                if isinstance(value, float) and value.is_integer():
                    dense.append(str(int(value)))
                else:
                    dense.append(clean_text(str(value)) if value is not None else "")

            while dense and not dense[-1]:
                dense.pop()
            rows.append(dense)
        sheets[sheet.name] = rows
    return sheets


def _read_with_excel_com(path: Path) -> dict[str, list[list[str]]]:
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:  # pragma: no cover - windows dependency
        raise RuntimeError(
            "Legacy/encrypted workbook fallback requires pywin32 (win32com)."
        ) from exc

    def _coerce_cell(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return clean_text(str(value))

    resolved_path = path.resolve()
    excel = None
    workbook = None
    com_initialized = False
    try:
        # Streamlit may execute callbacks on worker threads where COM is not initialized.
        pythoncom.CoInitialize()
        com_initialized = True
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        workbook = excel.Workbooks.Open(str(resolved_path), ReadOnly=True, UpdateLinks=0, IgnoreReadOnlyRecommended=True)

        sheets: dict[str, list[list[str]]] = {}
        for worksheet in workbook.Worksheets:
            used_range = worksheet.UsedRange
            row_count = int(used_range.Rows.Count)
            col_count = int(used_range.Columns.Count)
            if row_count <= 0 or col_count <= 0:
                sheets[worksheet.Name] = []
                continue

            raw_values = used_range.Value
            if row_count == 1 and col_count == 1:
                matrix = ((raw_values,),)
            elif row_count == 1:
                matrix = (raw_values,)
            elif col_count == 1:
                matrix = tuple((item,) for item in raw_values)
            else:
                matrix = raw_values

            rows: list[list[str]] = []
            for row in matrix:
                dense = [_coerce_cell(value) for value in row]
                while dense and not dense[-1]:
                    dense.pop()
                rows.append(dense)
            sheets[worksheet.Name] = rows

        return sheets
    finally:
        if workbook is not None:
            try:
                workbook.Close(False)
            except Exception:
                pass
        if excel is not None:
            try:
                excel.Quit()
            except Exception:
                pass
        if com_initialized:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


def read_xlsx(path: Path) -> dict[str, list[list[str]]]:
    with path.open("rb") as handle:
        magic = handle.read(8)

    if magic.startswith(ZIP_MAGIC):
        return _read_zip_xlsx(path)
    if magic == OLE_MAGIC:
        try:
            return _read_legacy_xls(path)
        except Exception:
            # Some enterprise workbooks are wrapped in OLE encryption containers.
            return _read_with_excel_com(path)

    raise ValueError(f"Unsupported Excel format for file: {path}")


def norm_header(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def extract_table(rows: list[list[str]], headers: dict[str, str]) -> list[dict[str, str]]:
    target = {k: norm_header(v) for k, v in headers.items()}
    idx = -1
    cols: dict[str, int] = {}
    for i, row in enumerate(rows[:40]):
        normalized = {norm_header(c): j for j, c in enumerate(row) if norm_header(c)}
        if all(v in normalized for v in target.values()):
            idx = i
            cols = {k: normalized[v] for k, v in target.items()}
            break
    if idx < 0:
        return []

    out: list[dict[str, str]] = []
    for row in rows[idx + 1 :]:
        if not any(clean_text(c) for c in row):
            continue
        item = {k: clean_text(row[c]) if c < len(row) else "" for k, c in cols.items()}
        if any(item.values()):
            out.append(item)
    return out


def extract_full_table(rows: list[list[str]], required_headers: list[str]) -> list[dict[str, str]]:
    normalized_required = [norm_header(h) for h in required_headers]
    header_idx = -1
    headers: list[str] = []
    for i, row in enumerate(rows[:50]):
        norm_row = [norm_header(c) for c in row]
        if all(req in norm_row for req in normalized_required):
            header_idx = i
            headers = [clean_text(c) if clean_text(c) else f"col_{j}" for j, c in enumerate(row)]
            break
    if header_idx < 0:
        return []
    output: list[dict[str, str]] = []
    for row in rows[header_idx + 1 :]:
        if not any(clean_text(c) for c in row):
            continue
        item = {}
        for j, h in enumerate(headers):
            item[h] = clean_text(row[j]) if j < len(row) else ""
        output.append(item)
    return output


def campaign_rows_from_sources() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for row in dashboard_campaign_rows():
        meta = OFFICIAL_CAMPAIGNS.get(row["campaign_code"])
        rows.append(
            {
                "campaign_code": row["campaign_code"],
                "campaign_id": meta["campaign_id"] if meta else "EXCLUDED",
                "campaign_name_raw": row["campaign_name"],
                "estimator_scope": meta["scope"] if meta else "excluded",
                "include_for_estimator": "yes" if meta and meta["scope"] == "in_scope" else "no",
                "source_file": row["source_file"],
                "source_sheet": row["source_sheet"],
            }
        )

    dedup: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["campaign_code"] not in dedup:
            dedup[row["campaign_code"]] = row
    for code, meta in OFFICIAL_CAMPAIGNS.items():
        if code not in dedup:
            dedup[code] = {
                "campaign_code": code,
                "campaign_id": meta["campaign_id"],
                "campaign_name_raw": "",
                "estimator_scope": meta["scope"],
                "include_for_estimator": "yes" if meta["scope"] == "in_scope" else "no",
                "source_file": "",
                "source_sheet": "",
            }

    return [dedup[k] for k in sorted(dedup)]


def enrich_campaign_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    actual_totals = dashboard_actual_costs()
    enriched_rows: list[dict[str, str]] = []
    for row in rows:
        meta = OFFICIAL_CAMPAIGNS.get(row["campaign_code"])
        campaign_name = row["campaign_id"] if row["campaign_id"] != "EXCLUDED" else clean_text(row["campaign_name_raw"])
        enriched_rows.append(
            {
                "campaign_code": row["campaign_code"],
                "campaign_id": row["campaign_id"],
                "campaign_name": campaign_name,
                "campaign_name_raw": row["campaign_name_raw"],
                "field": meta["field"] if meta else "",
                "campaign_wbs_code": row["campaign_code"] if meta else "",
                "estimator_scope": row["estimator_scope"],
                "include_for_estimator": row["include_for_estimator"],
                "start_date": "",
                "end_date": "",
                "actual_cost_total": f"{actual_totals[row['campaign_code']]:.2f}" if row["campaign_code"] in actual_totals else "",
                "source_file": row["source_file"],
                "source_sheet": row["source_sheet"],
            }
        )
    return enriched_rows


def build_alias_index() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for left, right in WELL_ALIAS_PAIRS:
        l_norm, r_norm = normalize_well(left), normalize_well(right)
        mapping[l_norm] = r_norm
        mapping[r_norm] = r_norm
    mapping.update(load_dashboard_alias_index())
    return mapping


def load_dashboard_alias_index() -> dict[str, str]:
    path = RAW_DIR / DASHBOARD_WORKBOOK
    if not path.exists():
        return {}

    wb = read_xlsx(path)
    rows = extract_full_table(
        wb.get("General.Camp.Data", []),
        ["Asset", "Campaign", "WBS CODE", "Well Name Actual", "Well Name SAP", "Well Name Alt 1", "Well Name Alt 2"],
    )

    mapping: dict[str, str] = {}
    for row in rows:
        canonical = normalize_well(row.get("Well Name Actual", ""))
        if not canonical:
            continue
        for key in ["Well Name Actual", "Well Name SAP", "Well Name Alt 1", "Well Name Alt 2"]:
            alias = normalize_well(row.get(key, ""))
            if alias:
                mapping[alias] = canonical
        if canonical.startswith("DRJ-") and canonical not in {"DRJ-53", "DRJ-54", "DRJ-55", "DRJ-56", "DRJ-57"}:
            mapping[f"{canonical}OH"] = canonical
        if canonical == "DRJ-38":
            mapping["DRJ-38RD"] = canonical
    return mapping


def dashboard_campaign_rows() -> list[dict[str, str]]:
    path = RAW_DIR / DASHBOARD_WORKBOOK
    if not path.exists():
        return []

    wb = read_xlsx(path)
    rows = extract_full_table(wb.get("General.Camp.Data", []), ["Asset", "Campaign", "WBS CODE"])
    out: list[dict[str, str]] = []
    for row in rows:
        code = clean_text(row.get("WBS CODE", "")).upper()
        campaign_name = clean_text(row.get("Campaign", ""))
        if code and campaign_name:
            out.append(
                {
                    "campaign_code": code,
                    "campaign_name": campaign_name,
                    "source_file": DASHBOARD_WORKBOOK,
                    "source_sheet": "General.Camp.Data",
                }
            )
    return out


def dashboard_actual_costs() -> dict[str, float]:
    path = RAW_DIR / DASHBOARD_WORKBOOK
    if not path.exists():
        return {}

    wb = read_xlsx(path)
    rows = extract_full_table(wb.get("Check.Total", []), ["Row Labels", "Sum of Actual Cost USD"])
    out: dict[str, float] = {}
    for row in rows:
        label = clean_text(row.get("Row Labels", "")).upper()
        total_text = clean_text(row.get("Sum of Actual Cost USD", ""))
        if not label or not total_text:
            continue
        code = CAMPAIGN_LABEL_TO_CODE.get(label, "")
        if code:
            try:
                out[code] = float(total_text.replace(",", ""))
            except ValueError:
                continue
    return out


def collect_observations() -> list[dict[str, str]]:
    observations: list[dict[str, str]] = []

    dashboard_path = RAW_DIR / DASHBOARD_WORKBOOK
    if dashboard_path.exists():
        dashboard = read_xlsx(dashboard_path)
        context_rows = extract_full_table(
            dashboard.get("General.Camp.Data", []),
            ["Asset", "Campaign", "WBS CODE", "Well Name Actual", "Well Name SAP", "Well Name Alt 1", "Well Name Alt 2"],
        )
        for row in context_rows:
            campaign_raw = row.get("Campaign", "")
            for key in ["Well Name Actual", "Well Name SAP", "Well Name Alt 1", "Well Name Alt 2"]:
                well_alias = normalize_well(row.get(key, ""))
                if well_alias:
                    observations.append(
                        {
                            "source_sheet": "General.Camp.Data",
                            "campaign_raw": campaign_raw,
                            "well_alias": well_alias,
                        }
                    )

        template_rows = extract_full_table(dashboard.get("DashBoard.Tab.Template", []), ["Asset", "Campaign", "Well"])
        for row in template_rows:
            well_alias = normalize_well(row.get("Well", ""))
            if well_alias and well_alias != "GENERAL":
                observations.append(
                    {
                        "source_sheet": "DashBoard.Tab.Template",
                        "campaign_raw": row.get("Campaign", ""),
                        "well_alias": well_alias,
                    }
                )

        structured_rows = extract_full_table(dashboard.get("Structured.Cost", []), ["Asset", "Campaign", "Well"])
        for row in structured_rows:
            well_alias = normalize_well(row.get("Well", ""))
            if well_alias and well_alias != "GENERAL":
                observations.append(
                    {
                        "source_sheet": "Structured.Cost",
                        "campaign_raw": row.get("Campaign", ""),
                        "well_alias": well_alias,
                    }
                )

        phase_rows = extract_full_table(dashboard.get("Phase.Summary", []), ["Well Name"])
        for row in phase_rows:
            well_alias = normalize_well(row.get("Well Name", ""))
            if well_alias and well_alias != "GENERAL":
                observations.append(
                    {
                        "source_sheet": "Phase.Summary",
                        "campaign_raw": "",
                        "well_alias": well_alias,
                    }
                )

        depth_rows = extract_full_table(dashboard.get("Drill.Depth.Days", []), ["Well Name (WellView Version)"])
        for row in depth_rows:
            well_alias = normalize_well(row.get("Well Name (WellView Version)", ""))
            if well_alias and well_alias != "GENERAL":
                observations.append(
                    {
                        "source_sheet": "Drill.Depth.Days",
                        "campaign_raw": "",
                        "well_alias": well_alias,
                    }
                )

    return observations


def build_master_and_lookup() -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, int]]:
    alias_index = build_alias_index()
    observations = collect_observations()

    # Step 1: establish in-scope master roster from non-history operational sheets.
    master_by_key: dict[tuple[str, str], dict[str, str]] = {}
    lookup_rows: list[dict[str, str]] = []

    for obs in observations:
        campaign_label = clean_text(obs["campaign_raw"]).upper()
        campaign_code = CAMPAIGN_LABEL_TO_CODE.get(campaign_label, "")
        canonical = alias_index.get(obs["well_alias"], obs["well_alias"])

        if campaign_label == "DRJ 2023" and canonical == "DRJ-50":
            lookup_rows.append(
                {
                    "well_alias": obs["well_alias"],
                    "well_canonical": canonical,
                    "source_sheet": obs["source_sheet"],
                    "alias_type": "source_observation",
                    "resolution_method": "posting_exception",
                    "is_modeling_master": "no",
                }
            )
            continue

        if obs["source_sheet"] in {"General.Camp.Data", "DashBoard.Tab.Template", "Structured.Cost"} and campaign_code in OFFICIAL_CAMPAIGNS:
            meta = OFFICIAL_CAMPAIGNS[campaign_code]
            if meta["scope"] == "in_scope":
                key = (canonical, campaign_code)
                if key not in master_by_key:
                    training_note = ""
                    include_training = "yes"
                    if canonical == "DRJ-STEAM 1" and campaign_code == "E530-30101-D235301":
                        include_training = "no"
                        training_note = "Keep in scope, exclude from well-level training until confirmed"
                    master_by_key[key] = {
                        "well_canonical": canonical,
                        "field": meta["field"],
                        "campaign_code": campaign_code,
                        "campaign_id": meta["campaign_id"],
                        "include_for_estimator": "yes",
                        "include_for_well_training": include_training,
                        "training_note": training_note,
                    }

    # helper for history reassignment rule
    campaigns_by_well: dict[str, set[str]] = {}
    for well_canonical, campaign_code in master_by_key.keys():
        campaigns_by_well.setdefault(well_canonical, set()).add(campaign_code)

    reassigned_history_rows = 0
    unresolved_rows = 0
    remaining_exclusions = 0

    for obs in observations:
        canonical = alias_index.get(obs["well_alias"], obs["well_alias"])
        campaign_label = clean_text(obs["campaign_raw"]).upper()
        campaign_code = CAMPAIGN_LABEL_TO_CODE.get(campaign_label, "")

        alias_type = "context_observation" if obs["source_sheet"] in {"Phase.Summary", "Drill.Depth.Days"} else "source_observation"
        resolution_method = "direct_match"
        is_modeling_master = "no"

        if campaign_label == "DRJ 2023" and canonical == "DRJ-50":
            resolution_method = "posting_exception"
            remaining_exclusions += 1
        elif obs["source_sheet"] in {"Phase.Summary", "Drill.Depth.Days"}:
            matches = sorted(campaigns_by_well.get(canonical, set()))
            if len(matches) == 1:
                campaign_code = matches[0]
                reassigned_history_rows += 1
                resolution_method = "context_reassigned_unique_master"
                is_modeling_master = "yes"
            elif len(matches) == 0:
                resolution_method = "out_of_scope"
                unresolved_rows += 1
                remaining_exclusions += 1
            else:
                resolution_method = "ambiguous_master_match"
                unresolved_rows += 1
                remaining_exclusions += 1
        else:
            if campaign_code in OFFICIAL_CAMPAIGNS and OFFICIAL_CAMPAIGNS[campaign_code]["scope"] == "in_scope":
                is_modeling_master = "yes"
            elif campaign_code in OFFICIAL_CAMPAIGNS:
                resolution_method = "legacy_reference"
                remaining_exclusions += 1
            else:
                resolution_method = "out_of_scope"
                remaining_exclusions += 1

        lookup_rows.append(
            {
                "well_alias": obs["well_alias"],
                "well_canonical": canonical,
                "source_sheet": obs["source_sheet"],
                "alias_type": alias_type,
                "resolution_method": resolution_method,
                "is_modeling_master": is_modeling_master,
            }
        )

    # Add explicit alias catalog rows.
    for left, right in WELL_ALIAS_PAIRS:
        l_norm, r_norm = normalize_well(left), normalize_well(right)
        for alias in [l_norm, r_norm]:
            lookup_rows.append(
                {
                    "well_alias": alias,
                    "well_canonical": r_norm,
                    "source_sheet": "alias_catalog",
                    "alias_type": "manual_alias",
                    "resolution_method": "manual_alias_map",
                    "is_modeling_master": "yes" if r_norm in campaigns_by_well else "no",
                }
            )

    # De-duplicate lookup rows
    dedup_lookup: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    for row in lookup_rows:
        key = (row["well_alias"], row["well_canonical"], row["source_sheet"], row["alias_type"], row["resolution_method"])
        if key not in dedup_lookup:
            dedup_lookup[key] = row

    stats = {
        "reassigned_history_rows": reassigned_history_rows,
        "unresolved_rows": unresolved_rows,
        "remaining_exclusions": remaining_exclusions,
    }

    master_rows = sorted(master_by_key.values(), key=lambda r: (r["campaign_code"], r["well_canonical"]))
    lookup_final = sorted(dedup_lookup.values(), key=lambda r: (r["well_alias"], r["source_sheet"], r["resolution_method"]))
    return master_rows, lookup_final, stats


def enrich_master_rows(master_rows: list[dict[str, str]], lookup_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    aliases_by_canonical: dict[str, set[str]] = {}
    for row in lookup_rows:
        canonical = clean_text(row.get("well_canonical", ""))
        alias = clean_text(row.get("well_alias", ""))
        if not canonical:
            continue
        aliases_by_canonical.setdefault(canonical, set()).add(canonical)
        if alias:
            aliases_by_canonical[canonical].add(alias)

    order_map = {
        well: {"well_sequence_in_campaign": str(seq), "well_order_label": label}
        for well, seq, label in SALAK_2025_ORDER
    }

    enriched_rows: list[dict[str, str]] = []
    for row in master_rows:
        well_canonical = row["well_canonical"]
        order_meta = {"well_sequence_in_campaign": "", "well_order_label": "", "well_order_basis": "", "well_order_note": ""}
        if row["campaign_id"] == "SALAK_2025_2026" and well_canonical in order_map:
            order_meta = {
                "well_sequence_in_campaign": order_map[well_canonical]["well_sequence_in_campaign"],
                "well_order_label": order_map[well_canonical]["well_order_label"],
                "well_order_basis": "user_confirmed_salak_2025_2026_left_to_right",
                "well_order_note": "AWI 9-10RD aliases to canonical AWI 9-10 for order metadata.",
            }
        enriched_rows.append(
            {
                "well_id": well_canonical,
                "well_name": well_canonical,
                "well_canonical": well_canonical,
                "well_aliases": json.dumps(sorted(aliases_by_canonical.get(well_canonical, {well_canonical}))),
                "field": row["field"],
                "campaign_code": row["campaign_code"],
                "campaign_id": row["campaign_id"],
                "well_sequence_in_campaign": order_meta["well_sequence_in_campaign"],
                "well_order_label": order_meta["well_order_label"],
                "well_order_basis": order_meta["well_order_basis"],
                "well_order_note": order_meta["well_order_note"],
                "status": "in_scope_estimator",
                "region": "",
                "operator": "",
                "include_for_estimator": row["include_for_estimator"],
                "include_for_well_training": row["include_for_well_training"],
                "training_note": row["training_note"],
            }
        )
    return enriched_rows


def build_canonical_well_mapping_rows(master_rows: list[dict[str, str]], lookup_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    aliases_by_canonical: dict[str, set[str]] = {}
    source_sheets_by_pair: dict[tuple[str, str], set[str]] = {}
    for row in lookup_rows:
        canonical = clean_text(row.get("well_canonical", ""))
        alias = clean_text(row.get("well_alias", ""))
        source_sheet = clean_text(row.get("source_sheet", ""))
        if not canonical or not alias:
            continue
        aliases_by_canonical.setdefault(canonical, set()).add(alias)
        source_sheets_by_pair.setdefault((canonical, alias), set()).add(source_sheet or "lookup")
        aliases_by_canonical[canonical].add(canonical)
        source_sheets_by_pair.setdefault((canonical, canonical), set()).add(source_sheet or "lookup")

    rows: list[dict[str, str]] = []

    for left, right in WELL_ALIAS_PAIRS:
        alias = normalize_well(left)
        canonical = normalize_well(right)
        rows.append(
            {
                "well_alias": alias,
                "well_canonical": canonical,
                "campaign_code": "",
                "campaign_id": "",
                "estimator_scope": "reference",
                "include_for_estimator": "no",
                "include_for_well_training": "no",
                "source_sheet": "alias_catalog",
                "note": "Configured alias mapping",
                "well_sequence_in_campaign": "",
                "well_order_label": "",
                "well_order_basis": "",
                "well_order_note": "",
            }
        )

    for master in master_rows:
        canonical = clean_text(master.get("well_canonical", ""))
        if not canonical:
            continue
        aliases = sorted(aliases_by_canonical.get(canonical, {canonical}))
        for alias in aliases:
            sources = sorted(source_sheets_by_pair.get((canonical, alias), {"dashboard"}))
            for source_sheet in sources:
                row = {
                    "well_alias": alias,
                    "well_canonical": canonical,
                    "campaign_code": master.get("campaign_code", ""),
                    "campaign_id": master.get("campaign_id", ""),
                    "estimator_scope": "in_scope",
                    "include_for_estimator": master.get("include_for_estimator", "yes"),
                    "include_for_well_training": master.get("include_for_well_training", "yes"),
                    "source_sheet": source_sheet,
                    "note": "",
                    "well_sequence_in_campaign": "",
                    "well_order_label": "",
                    "well_order_basis": "",
                    "well_order_note": "",
                }
                if master.get("campaign_id") == "SALAK_2025_2026":
                    canonical_norm = normalize_well(canonical)
                    order_meta = {normalize_well(well): (seq, label) for well, seq, label in SALAK_2025_ORDER}
                    if canonical_norm in order_meta:
                        seq, label = order_meta[canonical_norm]
                        row["well_sequence_in_campaign"] = str(seq)
                        row["well_order_label"] = label
                        row["well_order_basis"] = "user_confirmed_salak_2025_2026_left_to_right"
                        row["well_order_note"] = "AWI 9-10RD aliases to canonical AWI 9-10 for order metadata."
                rows.append(row)

    dedup: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = (
            row["well_alias"],
            row["well_canonical"],
            row["campaign_code"],
            row["campaign_id"],
            row["source_sheet"],
            row["include_for_well_training"],
            row["well_order_label"],
        )
        if key not in dedup:
            dedup[key] = row

    return sorted(
        dedup.values(),
        key=lambda r: (
            r["well_alias"],
            r["well_canonical"],
            r["campaign_code"],
            r["source_sheet"],
        ),
    )


def enrich_canonical_well_mapping_order_metadata() -> None:
    path = PROCESSED_DIR / "canonical_well_mapping.csv"
    if not path.exists():
        return

    order_map = {
        well: {"well_sequence_in_campaign": str(seq), "well_order_label": label}
        for well, seq, label in SALAK_2025_ORDER
    }

    rows = read_csv(path)
    fieldnames = list(rows[0].keys()) if rows else []

    for extra in ["well_sequence_in_campaign", "well_order_label", "well_order_basis", "well_order_note"]:
        if extra not in fieldnames:
            fieldnames.append(extra)

    for row in rows:
        row.setdefault("well_sequence_in_campaign", "")
        row.setdefault("well_order_label", "")
        row.setdefault("well_order_basis", "")
        row.setdefault("well_order_note", "")

        if row.get("campaign_id") != "SALAK_2025_2026":
            continue

        canonical = normalize_well(row.get("well_canonical", ""))
        if canonical not in order_map:
            continue
        row["well_sequence_in_campaign"] = order_map[canonical]["well_sequence_in_campaign"]
        row["well_order_label"] = order_map[canonical]["well_order_label"]
        row["well_order_basis"] = "user_confirmed_salak_2025_2026_left_to_right"
        row["well_order_note"] = "AWI 9-10RD aliases to canonical AWI 9-10 for order metadata."

    write_csv(path, rows, fieldnames)




def write_report(stats: dict[str, int], master_rows: list[dict[str, str]], lookup_rows: list[dict[str, str]]) -> None:
    in_scope_master = len(master_rows)
    alias_catalog_rows = sum(1 for r in lookup_rows if r["source_sheet"] == "alias_catalog")
    report = f"""# Well Master Build Report

## Build outcome
- In-scope well master rows: **{in_scope_master}**
- Alias lookup rows: **{len(lookup_rows)}**
- Alias catalog rows: **{alias_catalog_rows}**

## Required counts
- Reassigned history rows: **{stats['reassigned_history_rows']}**
- Unresolved rows: **{stats['unresolved_rows']}**
- Remaining exclusions: **{stats['remaining_exclusions']}**

## Rules enforced
1. Campaign scope widened to all seven dashboard campaigns across DARAJAT, SALAK, and WAYANG_WINDU.
2. `DRJ-Steam 1` kept in scope and excluded from well-level training.
3. `20-1` under DRJ 2023 treated as posting exception only.
4. Context-only well aliases (`Phase.Summary`, `Drill.Depth.Days`) are reassigned to campaign when canonical well maps to exactly one in-scope master well.
5. Dashboard workbook aliases (`OH`, `RD`, SAP/Alt names, WW spacing variants) are normalized into canonical well names before estimator use.

## Exported contract
- `well_master.csv` now carries both estimator roster fields (`campaign_code`, `campaign_id`, training flags) and stable master keys (`well_id`, `well_name`, `well_aliases`).
- `status` is scoped to estimator roster membership (`in_scope_estimator`) rather than real-world well lifecycle.
- `region` and `operator` remain blank in this Define layer because the current source package does not provide a reliable authoritative value for every in-scope well.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def write_scope_coverage_report(campaign_rows: list[dict[str, str]], master_rows: list[dict[str, str]]) -> None:
    wells_by_campaign: dict[str, int] = {}
    for row in master_rows:
        wells_by_campaign[row["campaign_id"]] = wells_by_campaign.get(row["campaign_id"], 0) + 1

    lines = [
        "# Unit Price Scope Coverage",
        "",
        "Ground-up canonical scope for the dashboard-driven unit-price build.",
        "",
        "| field | campaign_id | campaign_code | include_for_estimator | actual_cost_total | canonical_well_count | source_file | source_sheet |",
        "|---|---|---|---|---:|---:|---|---|",
    ]
    for row in sorted(campaign_rows, key=lambda r: (r["field"], r["campaign_id"])):
        if row["include_for_estimator"] != "yes":
            continue
        lines.append(
            f"| {row['field']} | {row['campaign_id']} | {row['campaign_code']} | {row['include_for_estimator']} | "
            f"{row['actual_cost_total'] or '0.00'} | {wells_by_campaign.get(row['campaign_id'], 0)} | "
            f"{row['source_file'] or ''} | {row['source_sheet'] or ''} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "- Campaign scope is workbook-driven and no longer limited to the legacy three-campaign estimator subset.",
            "- Canonical well names come from dashboard workbook observations (`General.Camp.Data`, `DashBoard.Tab.Template`, `Structured.Cost`) and manual alias rules.",
            "- `DRJ-STEAM 1` remains in estimator scope but excluded from well-level training until confirmed.",
        ]
    )
    SCOPE_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _to_float(value: str) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _synthetic_wbs_id(level2: str, level3: str, level4: str, level5: str) -> str:
    parts = [level2, level3, level4, level5]
    tokens = [re.sub(r"[^A-Z0-9]+", "_", clean_text(part).upper()).strip("_") for part in parts]
    return "L5_" + "__".join(token or "NA" for token in tokens)


def build_synthetic_placeholders() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    wb = read_xlsx(RAW_DIR / DASHBOARD_WORKBOOK)
    structured_rows = extract_full_table(
        wb.get("Structured.Cost", []),
        ["Asset", "Campaign", "Level 2", "Level 3", "Level 4", "Level 5", "Well", "Actual Cost USD"],
    )

    template_candidates = {
        "SALAK": [
            {"campaign_label": "SLK - 2025", "campaign_code": "E540-30101-D245401", "campaign_id": "SALAK_2025_2026", "year": 2025}
        ],
        "DARAJAT": [
            {"campaign_label": "DRJ - 2022", "campaign_code": "E530-30101-D225301", "campaign_id": "DARAJAT_2022", "year": 2022},
            {"campaign_label": "DRJ - 2024", "campaign_code": "E530-30101-D235301", "campaign_id": "DARAJAT_2023_2024", "year": 2023},
        ],
    }

    campaign_rows: list[dict[str, str]] = []
    lv5_rows: list[dict[str, str]] = []

    for spec in SYNTHETIC_CAMPAIGNS:
        candidates = template_candidates[spec["field"]]
        template = min(candidates, key=lambda c: abs(c["year"] - spec["target_year"]))
        cpi_ratio = CPI_INDEX_BY_YEAR[spec["target_year"]] / CPI_INDEX_BY_YEAR[template["year"]]
        brent_ratio = BRENT_BY_YEAR[spec["target_year"]] / BRENT_BY_YEAR[template["year"]]
        macro_factor = 0.7 * cpi_ratio + 0.3 * brent_ratio

        campaign_rows.append(
            {
                "synthetic_campaign_id": spec["synthetic_campaign_id"],
                "field": spec["field"],
                "synthetic_target_year": str(spec["target_year"]),
                "synthetic_base_campaign": template["campaign_id"],
                "synthetic_base_campaign_code": template["campaign_code"],
                "synthetic_macro_factor": f"{macro_factor:.6f}",
                "synthetic_cpi_ratio": f"{cpi_ratio:.6f}",
                "synthetic_brent_ratio": f"{brent_ratio:.6f}",
                "is_synthetic": "yes",
                "synthetic_purpose": "placeholder_campaign_integration",
                "placeholder_confidence": "low",
                "include_for_training": "no",
                "include_for_validation": "no",
            }
        )

        template_rows = [
            r for r in structured_rows
            if clean_text(r.get("Campaign", "")).upper() == template["campaign_label"].upper()
            and clean_text(r.get("Level 5", ""))
        ]

        for row in template_rows:
            level2 = clean_text(row.get("Level 2", ""))
            level3 = clean_text(row.get("Level 3", ""))
            level4 = clean_text(row.get("Level 4", ""))
            level5 = clean_text(row.get("Level 5", ""))
            source_cost = _to_float(row.get("Actual Cost USD", "")) or 0.0

            lv5_rows.append(
                {
                    "Asset": spec["field"],
                    "Campaign": spec["synthetic_campaign_id"],
                    "WBS_Level": "05",
                    "WBS_ID": _synthetic_wbs_id(level2, level3, level4, level5),
                    "Description": level5,
                    "L1": spec["synthetic_campaign_id"],
                    "L2": level2,
                    "L3": level3,
                    "L4": level4,
                    "L5": level5,
                    "L5_Group": level5,
                    "Well Name": clean_text(row.get("Well", "")),
                    "ACTUAL, USD": f"{source_cost * macro_factor:.6f}",
                    "Actual Cost USD": f"{source_cost * macro_factor:.6f}",
                    "is_synthetic": "yes",
                    "synthetic_purpose": "placeholder_wbs_lv5_integration",
                    "synthetic_base_campaign": template["campaign_id"],
                    "synthetic_target_year": str(spec["target_year"]),
                    "synthetic_macro_factor": f"{macro_factor:.6f}",
                    "synthetic_cpi_ratio": f"{cpi_ratio:.6f}",
                    "synthetic_brent_ratio": f"{brent_ratio:.6f}",
                    "placeholder_confidence": "low",
                    "include_for_training": "no",
                    "include_for_validation": "no",
                }
            )

    return campaign_rows, lv5_rows


def write_synthetic_report(campaign_rows: list[dict[str, str]], lv5_rows: list[dict[str, str]]) -> None:
    by_campaign = {}
    for row in lv5_rows:
        by_campaign[row["Campaign"]] = by_campaign.get(row["Campaign"], 0) + 1

    lines = [
        "# Synthetic Placeholder Method",
        "",
        "This staging layer is placeholder-only for future old/new campaign integration and is **excluded from training and validation**.",
        "",
        "## Macro factor",
        "`synthetic_cost = base_cost * macro_factor`",
        "`macro_factor = 0.7 * (CPI_target / CPI_base) + 0.3 * (Brent_target / Brent_base)`",
        "",
        "## Generated synthetic campaigns",
        "| synthetic_campaign_id | base_campaign | target_year | macro_factor |",
        "|---|---|---:|---:|",
    ]
    for row in campaign_rows:
        lines.append(
            f"| {row['synthetic_campaign_id']} | {row['synthetic_base_campaign']} | {row['synthetic_target_year']} | {row['synthetic_macro_factor']} |"
        )
    lines.extend(
        [
            "",
            "## Output counts",
            f"- synthetic campaign rows: **{len(campaign_rows)}**",
            f"- synthetic WBS Lv.5 placeholder rows: **{len(lv5_rows)}**",
            "",
            "## Notes",
            "- Non-cost structural fields are copied from nearest same-field real campaign templates.",
            "- Only cost-like numeric fields are scaled by macro factor.",
            "- All synthetic rows set `include_for_training = no` and `include_for_validation = no`.",
        ]
    )
    SYNTH_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_salak_2021_scope_report() -> None:
    wb = read_xlsx(RAW_DIR / DASHBOARD_WORKBOOK)
    structured_rows = extract_full_table(
        wb.get("Structured.Cost", []),
        ["Asset", "Campaign", "Level 2", "Level 3", "Level 4", "Level 5", "Well", "Actual Cost USD"],
    )

    salak_2021_labels = {"SLK - 2021", "SALAK CAMPAIGN 2021", "SLK 2021"}
    salak_2021_lv5 = [r for r in structured_rows if clean_text(r.get("Campaign", "")).upper() in salak_2021_labels]
    in_scope_labels = {"SLK - 2025", "DRJ - 2022", "DRJ - 2024"}
    in_scope_lv5 = [r for r in structured_rows if clean_text(r.get("Campaign", "")).upper() in in_scope_labels]

    reference_only_sheets: list[str] = []
    for sheet_name, rows in wb.items():
        joined = " ".join(" ".join(r) for r in rows[:200]).upper()
        if "2021" in joined and "SALAK" in joined and sheet_name != "Structured.Cost":
            reference_only_sheets.append(sheet_name)

    lines = [
        "# SALAK_2021 Scope Investigation",
        "",
        "## Objective",
        "Record the current scope posture for SALAK_2021 after adding the dashboard workbook to the canonical source package.",
        "",
        "## Findings",
        f"- Structured.Cost Lv5 rows for SALAK_2021 labels (`SLK - 2021` / `SALAK CAMPAIGN 2021`): **{len(salak_2021_lv5)}**.",
        f"- Structured.Cost Lv5 rows for current in-scope campaigns (`SLK - 2025`, `DRJ - 2022`, `DRJ - 2024`): **{len(in_scope_lv5)}**.",
        f"- Sheets with SALAK 2021 references but no direct Lv5 cost-row authority used by this pipeline: **{', '.join(sorted(reference_only_sheets)) or 'none_detected'}**.",
        "",
        "## Interpretation",
        "- Dashboard Structured.Cost provides the active Lv5 cost-bearing source for SALAK_2021.",
        "- The widened unit-price program now treats the dashboard workbook as an authoritative historical source for campaign and well scope, so SALAK_2021 is retained in canonical scope.",
        "",
        "## Recommendation",
        "- Keep SALAK_2021 included for dashboard-driven history, unit-price analysis, and macro trend work.",
        "- Keep estimator refresh fully dashboard-driven and avoid fallback to legacy workbooks.",
    ]
    (ROOT / "reports" / "salak_2021_scope_investigation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    # Keep campaign scope artifact unchanged for audit continuity.
    campaign_rows = enrich_campaign_rows(campaign_rows_from_sources())
    write_csv(PROCESSED_DIR / "canonical_campaign_mapping.csv", campaign_rows, CAMPAIGN_MAPPING_FIELDS)

    master_rows_base, lookup_rows, stats = build_master_and_lookup()
    master_rows = enrich_master_rows(master_rows_base, lookup_rows)
    write_csv(PROCESSED_DIR / "well_master.csv", master_rows, WELL_MASTER_FIELDS)
    write_csv(PROCESSED_DIR / "well_alias_lookup.csv", lookup_rows, LOOKUP_FIELDS)
    canonical_well_rows = build_canonical_well_mapping_rows(master_rows, lookup_rows)
    write_csv(PROCESSED_DIR / "canonical_well_mapping.csv", canonical_well_rows, CANONICAL_WELL_MAPPING_FIELDS)
    enrich_canonical_well_mapping_order_metadata()
    write_report(stats, master_rows, lookup_rows)
    write_scope_coverage_report(campaign_rows, master_rows)
    write_salak_2021_scope_report()

    synth_campaign_rows, synth_lv5_rows = build_synthetic_placeholders()
    write_csv(PROCESSED_DIR / "synthetic_campaign_placeholders.csv", synth_campaign_rows)
    write_csv(PROCESSED_DIR / "synthetic_wbs_lv5_placeholders.csv", synth_lv5_rows)
    write_synthetic_report(synth_campaign_rows, synth_lv5_rows)
    print("Wrote canonical campaign/well mappings, well master, and scope reports.")


if __name__ == "__main__":
    main()
