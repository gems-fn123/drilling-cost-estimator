from __future__ import annotations

import csv
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_PATH = ROOT / "reports" / "campaign_well_mapping_report.md"

NS_MAIN = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_PKG = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}


@dataclass(frozen=True)
class CampaignRecord:
    source_file: str
    source_sheet: str
    asset_raw: str
    campaign_raw: str
    campaign_code_raw: str


def _col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip()


def normalize_asset(asset: str) -> str:
    text = _clean_text(asset).upper()
    mapping = {
        "DARAJAT": "DARAJAT",
        "DRJ": "DARAJAT",
        "SALAK": "SALAK",
        "SLK": "SALAK",
        "WAYANG WINDU": "WAYANG WINDU",
    }
    return mapping.get(text, text)


def normalize_campaign(name: str) -> str:
    text = _clean_text(name).upper()
    text = text.replace("DRJ", "DARAJAT").replace("SLK", "SALAK")
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_well(name: str) -> str:
    text = _clean_text(name).upper()
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text


def read_xlsx(path: Path) -> dict[str, list[list[str]]]:
    sheets: dict[str, list[list[str]]] = {}
    with zipfile.ZipFile(path) as zf:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", NS_MAIN):
                text = "".join(node.text or "" for node in item.findall(".//a:t", NS_MAIN))
                shared_strings.append(text)

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_by_id = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("p:Relationship", NS_PKG)
        }

        for sheet in workbook.findall("a:sheets/a:sheet", NS_MAIN):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = "xl/" + rel_by_id[rel_id].lstrip("/")
            sheet_xml = ET.fromstring(zf.read(target))
            rows: list[list[str]] = []
            for row in sheet_xml.findall("a:sheetData/a:row", NS_MAIN):
                values: dict[int, str] = {}
                for cell in row.findall("a:c", NS_MAIN):
                    value_node = cell.find("a:v", NS_MAIN)
                    if value_node is None:
                        continue
                    value = value_node.text or ""
                    if cell.attrib.get("t") == "s":
                        value = shared_strings[int(value)] if value else ""
                    values[_col_index(cell.attrib["r"])] = _clean_text(value)
                if not values:
                    rows.append([])
                    continue
                max_col = max(values)
                dense = [""] * (max_col + 1)
                for idx, value in values.items():
                    dense[idx] = value
                rows.append(dense)
            sheets[name] = rows
    return sheets


def _norm_header(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def extract_table(rows: list[list[str]], required_headers: dict[str, str]) -> list[dict[str, str]]:
    required_norm = {key: _norm_header(value) for key, value in required_headers.items()}
    header_idx = None
    header_map: dict[str, int] = {}

    for i, row in enumerate(rows[:40]):
        norm_to_col = {_norm_header(cell): idx for idx, cell in enumerate(row) if _norm_header(cell)}
        if all(val in norm_to_col for val in required_norm.values()):
            header_idx = i
            header_map = {key: norm_to_col[val] for key, val in required_norm.items()}
            break

    if header_idx is None:
        return []

    extracted: list[dict[str, str]] = []
    for row in rows[header_idx + 1 :]:
        if not any(_clean_text(cell) for cell in row):
            continue
        record: dict[str, str] = {}
        for key, col in header_map.items():
            record[key] = _clean_text(row[col]) if col < len(row) else ""
        if any(record.values()):
            extracted.append(record)
    return extracted


def build_mappings() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    campaign_records: list[CampaignRecord] = []
    well_records: list[dict[str, str]] = []

    for xlsx in sorted(RAW_DIR.glob("*.xlsx")):
        sheets = read_xlsx(xlsx)

        for sheet_name, rows in sheets.items():
            # Campaign + well dictionary table
            for rec in extract_table(
                rows,
                {
                    "asset": "Asset",
                    "campaign": "Campaign",
                    "campaign_code": "WBS CODE",
                    "well_sap": "Well Name SAP",
                    "well_wv": "Well Name WellView",
                    "well_other": "Well Name Others",
                },
            ):
                campaign_records.append(
                    CampaignRecord(xlsx.name, sheet_name, rec["asset"], rec["campaign"], rec["campaign_code"])
                )
                for col in ["well_sap", "well_wv", "well_other"]:
                    if rec[col] and rec[col].upper() != "XXXX":
                        well_records.append(
                            {
                                "source_file": xlsx.name,
                                "source_sheet": sheet_name,
                                "asset_raw": rec["asset"],
                                "campaign_raw": rec["campaign"],
                                "campaign_code_raw": rec["campaign_code"],
                                "well_raw": rec[col],
                                "well_source_column": col,
                            }
                        )

            # Campaign reference table
            for rec in extract_table(
                rows,
                {
                    "campaign_code": "WBS Drilling Campaign",
                    "campaign": "Campaign",
                },
            ):
                campaign_records.append(CampaignRecord(xlsx.name, sheet_name, "", rec["campaign"], rec["campaign_code"]))

            # Cost technical table
            for rec in extract_table(
                rows,
                {
                    "asset": "Asset",
                    "campaign": "Campaign",
                    "well": "Well Name",
                },
            ):
                campaign_records.append(CampaignRecord(xlsx.name, sheet_name, rec["asset"], rec["campaign"], ""))
                if rec["well"]:
                    well_records.append(
                        {
                            "source_file": xlsx.name,
                            "source_sheet": sheet_name,
                            "asset_raw": rec["asset"],
                            "campaign_raw": rec["campaign"],
                            "campaign_code_raw": "",
                            "well_raw": rec["well"],
                            "well_source_column": "well",
                        }
                    )

            # WellView adjusted table
            for rec in extract_table(
                rows,
                {
                    "asset": "Asset",
                    "campaign": "Drilling Campaign",
                    "well_sap": "Well Name SAP",
                    "well_wv": "Well Name Well View",
                },
            ):
                campaign_records.append(CampaignRecord(xlsx.name, sheet_name, rec["asset"], rec["campaign"], ""))
                for col in ["well_sap", "well_wv"]:
                    if rec[col]:
                        well_records.append(
                            {
                                "source_file": xlsx.name,
                                "source_sheet": sheet_name,
                                "asset_raw": rec["asset"],
                                "campaign_raw": rec["campaign"],
                                "campaign_code_raw": "",
                                "well_raw": rec[col],
                                "well_source_column": col,
                            }
                        )

            # Historical drilling table
            for rec in extract_table(
                rows,
                {
                    "asset": "Asset",
                    "campaign": "Drilling Campaign",
                    "well": "Well Name (WellView Version)",
                },
            ):
                if rec["campaign"]:
                    campaign_records.append(CampaignRecord(xlsx.name, sheet_name, rec["asset"], rec["campaign"], ""))
                if rec["well"]:
                    well_records.append(
                        {
                            "source_file": xlsx.name,
                            "source_sheet": sheet_name,
                            "asset_raw": rec["asset"],
                            "campaign_raw": rec["campaign"],
                            "campaign_code_raw": "",
                            "well_raw": rec["well"],
                            "well_source_column": "well",
                        }
                    )

    # Explode multiline wells from drilled well reference entries
    exploded_well_records: list[dict[str, str]] = []
    for record in well_records:
        chunks = [chunk.strip() for chunk in record["well_raw"].split("\n") if chunk.strip()]
        if not chunks:
            chunks = [record["well_raw"]]
        for chunk in chunks:
            cloned = dict(record)
            cloned["well_raw"] = chunk
            exploded_well_records.append(cloned)

    # Campaign mapping
    campaign_seen: set[tuple[str, str, str]] = set()
    campaign_rows: list[dict[str, str]] = []
    for rec in campaign_records:
        if not rec.campaign_raw and not rec.campaign_code_raw:
            continue
        campaign_canonical = normalize_campaign(rec.campaign_raw)
        if campaign_canonical in {"", "X"} and not rec.campaign_code_raw:
            continue
        asset_canonical = normalize_asset(rec.asset_raw)
        code_canonical = _clean_text(rec.campaign_code_raw).upper()
        dedupe_key = (campaign_canonical, code_canonical, asset_canonical)
        if dedupe_key in campaign_seen:
            continue
        campaign_seen.add(dedupe_key)
        campaign_rows.append(
            {
                "campaign_canonical": campaign_canonical,
                "campaign_raw": rec.campaign_raw,
                "campaign_code_canonical": code_canonical,
                "campaign_code_raw": rec.campaign_code_raw,
                "asset_canonical": asset_canonical,
                "asset_raw": rec.asset_raw,
                "source_file": rec.source_file,
                "source_sheet": rec.source_sheet,
            }
        )

    campaigns_by_name: dict[str, set[str]] = defaultdict(set)
    for row in campaign_rows:
        if row["campaign_canonical"]:
            if row["campaign_code_canonical"]:
                campaigns_by_name[row["campaign_canonical"]].add(row["campaign_code_canonical"])

    for row in campaign_rows:
        codes = campaigns_by_name.get(row["campaign_canonical"], set())
        row["ambiguity_flag"] = "yes" if len(codes) > 1 else "no"
        row["ambiguity_note"] = (
            f"Multiple campaign codes for canonical name: {', '.join(sorted(codes))}" if len(codes) > 1 else ""
        )

    # Well mapping
    well_rows_raw: list[dict[str, str]] = []
    for rec in exploded_well_records:
        campaign_canonical = normalize_campaign(rec["campaign_raw"])
        matching_codes = sorted(campaigns_by_name.get(campaign_canonical, set()))
        well_rows_raw.append(
            {
                "well_canonical": normalize_well(rec["well_raw"]),
                "well_raw": rec["well_raw"],
                "campaign_canonical": campaign_canonical,
                "campaign_raw": rec["campaign_raw"],
                "campaign_code_inferred": matching_codes[0] if len(matching_codes) == 1 else "",
                "asset_canonical": normalize_asset(rec["asset_raw"]),
                "asset_raw": rec["asset_raw"],
                "source_file": rec["source_file"],
                "source_sheet": rec["source_sheet"],
                "well_source_column": rec["well_source_column"],
                "ambiguity_flag": "yes" if len(matching_codes) > 1 else "no",
                "ambiguity_note": (
                    f"Campaign name maps to multiple codes: {', '.join(matching_codes)}" if len(matching_codes) > 1 else ""
                ),
            }
        )

    # Keep unique provenance-aware rows only.
    seen_well_keys: set[tuple[str, str, str, str, str, str]] = set()
    well_rows: list[dict[str, str]] = []
    for row in well_rows_raw:
        key = (
            row["well_canonical"],
            row["campaign_canonical"],
            row["campaign_code_inferred"],
            row["asset_canonical"],
            row["source_sheet"],
            row["well_source_column"],
        )
        if key in seen_well_keys:
            continue
        seen_well_keys.add(key)
        well_rows.append(row)

    campaign_out = PROCESSED_DIR / "canonical_campaign_mapping.csv"
    with campaign_out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(campaign_rows[0].keys()))
        writer.writeheader()
        writer.writerows(campaign_rows)

    well_out = PROCESSED_DIR / "canonical_well_mapping.csv"
    with well_out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(well_rows[0].keys()))
        writer.writeheader()
        writer.writerows(well_rows)

    unresolved_campaigns = [r for r in campaign_rows if r["ambiguity_flag"] == "yes"]
    unresolved_wells = [r for r in well_rows if r["ambiguity_flag"] == "yes" or not r["campaign_code_inferred"]]
    unresolved_samples = unresolved_wells[:10]

    unresolved_table = "\n".join(
        [
            f"| {r['well_canonical']} | {r['campaign_canonical']} | {r['source_sheet']} | {r['ambiguity_note'] or 'No campaign code could be inferred'} |"
            for r in unresolved_samples
        ]
    )
    if not unresolved_table:
        unresolved_table = "| - | - | - | - |"

    report = f"""# Canonical Campaign and Well Mapping Report

## Scope
This milestone only builds canonical campaign + well mapping from raw Excel files. No modeling or app work is included.

## Join Rules
1. **Campaign canonicalization**
   - `campaign_canonical` is uppercase, whitespace-normalized, with aliases normalized (`DRJ -> DARAJAT`, `SLK -> SALAK`).
   - `asset_canonical` is normalized to `DARAJAT`, `SALAK`, or `WAYANG WINDU` where applicable.
2. **Campaign key precedence**
   - Primary key candidate: `campaign_code_canonical` from `WBS CODE` or `WBS Drilling Campaign`.
   - Fallback key candidate: `(campaign_canonical, asset_canonical)` when code is absent.
3. **Well canonicalization**
   - `well_canonical` is uppercase, whitespace-normalized, and dash-spacing normalized.
   - Multi-line cells (e.g., Drilled.Well) are split into one row per well.
4. **Well-to-campaign assignment**
   - If a canonical campaign name maps to exactly one campaign code, that code is assigned as `campaign_code_inferred`.
   - If the campaign maps to multiple codes, mapping is marked ambiguous.

## Unresolved ambiguities
- Campaign rows with multiple campaign codes for a single `campaign_canonical`: **{len(unresolved_campaigns)}**.
- Well rows unresolved (missing inferred code or ambiguous campaign mapping): **{len(unresolved_wells)}**.

### Notes
- Empty campaign in source rows remains unresolved by design at this milestone.
- `canonical_well_mapping.csv` preserves source provenance (`source_file`, `source_sheet`, and source well column).

### Unresolved sample (first 10 rows)
| well_canonical | campaign_canonical | source_sheet | note |
|---|---|---|---|
{unresolved_table}
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    build_mappings()
    print("Wrote canonical mapping outputs to data/processed and report to reports/.")
