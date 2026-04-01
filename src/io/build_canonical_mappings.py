from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_PATH = ROOT / "reports" / "campaign_well_mapping_report.md"

NS_MAIN = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_PKG = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}

OFFICIAL_CAMPAIGNS = {
    "E530-30101-D225301": {"campaign_id": "DARAJAT_2022", "estimator_scope": "in_scope", "scope_note": "Estimator scope"},
    "E530-30101-D235301": {"campaign_id": "DARAJAT_2023_2024", "estimator_scope": "in_scope", "scope_note": "Estimator scope"},
    "E540-30101-D245401": {"campaign_id": "SALAK_2025_2026", "estimator_scope": "in_scope", "scope_note": "Estimator scope"},
    "E530-30101-D19001": {"campaign_id": "DARAJAT_2019", "estimator_scope": "legacy_reference", "scope_note": "Legacy reference only"},
    "E540-30101-D20001": {"campaign_id": "SALAK_2021", "estimator_scope": "legacy_reference", "scope_note": "Legacy reference only"},
}

WELL_ALIAS_PAIRS = [
    ("14-1", "DRJ-51"),
    ("14-2", "DRJ-52"),
    ("20-1", "DRJ-50"),
    ("SF-1", "DRJ-49"),
    ("SF-ML", "DRJ-38"),
    ("DRJ-STEAM 6", "DRJ-53"),
    ("DRJ-STEAM 2", "DRJ-54"),
    ("DRJ-STEAM 3", "DRJ-55"),
    ("DRJ-STEAM 4", "DRJ-56"),
    ("DRJ-STEAM 5", "DRJ-57"),
    ("AWI 9-10RD", "AWI 9-10"),
]


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip()


def normalize_well(name: str) -> str:
    text = clean_text(name).upper()
    return re.sub(r"\s*-\s*", "-", text)


def col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


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


def norm_header(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def extract_table(rows: list[list[str]], headers: dict[str, str]) -> list[dict[str, str]]:
    target = {k: norm_header(v) for k, v in headers.items()}
    idx = -1
    cols: dict[str, int] = {}
    for i, row in enumerate(rows[:40]):
        norm = {norm_header(c): j for j, c in enumerate(row) if norm_header(c)}
        if all(v in norm for v in target.values()):
            idx = i
            cols = {k: norm[v] for k, v in target.items()}
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


def campaign_rows_from_sources() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for workbook in sorted(RAW_DIR.glob("*.xlsx")):
        sheets = read_xlsx(workbook)
        for sheet, data in sheets.items():
            for rec in extract_table(data, {"campaign_code": "WBS Drilling Campaign", "campaign_name": "Campaign"}):
                code = rec["campaign_code"].upper()
                if not code:
                    continue
                scope = OFFICIAL_CAMPAIGNS.get(code)
                if scope:
                    rows.append(
                        {
                            "campaign_code": code,
                            "campaign_id": scope["campaign_id"],
                            "campaign_name_raw": rec["campaign_name"],
                            "estimator_scope": scope["estimator_scope"],
                            "include_for_estimator": "yes" if scope["estimator_scope"] == "in_scope" else "no",
                            "source_file": workbook.name,
                            "source_sheet": sheet,
                            "scope_note": scope["scope_note"],
                        }
                    )
                else:
                    rows.append(
                        {
                            "campaign_code": code,
                            "campaign_id": "EXCLUDED",
                            "campaign_name_raw": rec["campaign_name"],
                            "estimator_scope": "excluded",
                            "include_for_estimator": "no",
                            "source_file": workbook.name,
                            "source_sheet": sheet,
                            "scope_note": "Excluded from estimator (Wayang Windu / Hamiding / unknown category)",
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
                "estimator_scope": meta["estimator_scope"],
                "include_for_estimator": "yes" if meta["estimator_scope"] == "in_scope" else "no",
                "source_file": "",
                "source_sheet": "",
                "scope_note": meta["scope_note"],
            }

    return [dedup[k] for k in sorted(dedup)]


def build_alias_index() -> dict[str, str]:
    alias_to_canonical: dict[str, str] = {}
    for a, b in WELL_ALIAS_PAIRS:
        a_n, b_n = normalize_well(a), normalize_well(b)
        alias_to_canonical[a_n] = b_n
        alias_to_canonical[b_n] = b_n
    return alias_to_canonical


def collect_observed_wells() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    workbook = RAW_DIR / "20260327_WBS_Data.xlsx"
    sheets = read_xlsx(workbook)
    for sheet in ["Data.Summary", "Cost & Technical Data", "WellView.Data", "2. Drilling.Data.History"]:
        data = sheets.get(sheet, [])
        if sheet == "WellView.Data":
            table = extract_table(data, {"campaign": "Drilling Campaign", "well": "Well Name SAP"})
            for row in table:
                if row["well"]:
                    records.append({"source_sheet": sheet, "campaign_raw": row["campaign"], "well_raw": row["well"]})
        elif sheet == "2. Drilling.Data.History":
            table = extract_table(data, {"campaign": "Drilling Campaign", "well": "Well Name (WellView Version)"})
            for row in table:
                if row["well"]:
                    records.append({"source_sheet": sheet, "campaign_raw": row["campaign"], "well_raw": row["well"]})
        else:
            table = extract_table(data, {"campaign": "Campaign", "well": "Well Name"})
            for row in table:
                if row["well"]:
                    records.append({"source_sheet": sheet, "campaign_raw": row["campaign"], "well_raw": row["well"]})
    return records


def build_well_mapping() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    alias_index = build_alias_index()
    observed = collect_observed_wells()

    well_rows: list[dict[str, str]] = []
    anomalies: list[dict[str, str]] = []
    anomaly_seen: set[tuple[str, str, str, str]] = set()
    seen: set[tuple[str, str, str]] = set()

    campaign_map = {
        "DRJ 2022": "E530-30101-D225301",
        "DRJ 2023": "E530-30101-D235301",
        "SLK 2025": "E540-30101-D245401",
        "DARAJAT CAMPAIGN 2019": "E530-30101-D19001",
        "SALAK CAMPAIGN 2021": "E540-30101-D20001",
    }

    for rec in observed:
        well_norm = normalize_well(rec["well_raw"])
        campaign_norm = clean_text(rec["campaign_raw"]).upper()
        code = campaign_map.get(campaign_norm, "")

        if campaign_norm in {"DRJ 2023", "DARAJAT 2023", "DARAJAT_2023_2024"} and well_norm == "20-1":
            a_key = ("posting_exception", rec["campaign_raw"], rec["well_raw"], rec["source_sheet"])
            if a_key not in anomaly_seen:
                anomaly_seen.add(a_key)
                anomalies.append(
                    {
                        "anomaly_type": "posting_exception",
                        "campaign_raw": rec["campaign_raw"],
                        "well_raw": rec["well_raw"],
                        "source_sheet": rec["source_sheet"],
                        "note": "20-1 under DRJ 2023 treated as posting exception; not remapped to DARAJAT_2023_2024 well roster.",
                    }
                )
            continue

        canonical_well = alias_index.get(well_norm, well_norm)
        include_training = "no" if well_norm == normalize_well("DRJ-Steam 1") else "yes"
        note = ""
        if well_norm == normalize_well("DRJ-Steam 1"):
            note = "Keep in DARAJAT_2023_2024 campaign, exclude from well-level training until confirmed."

        campaign_scope = OFFICIAL_CAMPAIGNS.get(code, {}).get("estimator_scope", "excluded")
        include_estimator = "yes" if campaign_scope == "in_scope" else "no"

        key = (well_norm, code, rec["source_sheet"])
        if key in seen:
            continue
        seen.add(key)

        well_rows.append(
            {
                "well_alias": well_norm,
                "well_canonical": canonical_well,
                "campaign_code": code,
                "campaign_id": OFFICIAL_CAMPAIGNS.get(code, {}).get("campaign_id", "EXCLUDED"),
                "estimator_scope": campaign_scope,
                "include_for_estimator": include_estimator,
                "include_for_well_training": include_training if include_estimator == "yes" else "no",
                "source_sheet": rec["source_sheet"],
                "note": note,
            }
        )

    # Ensure explicit alias catalog is always present for auditable mapping.
    for left, right in WELL_ALIAS_PAIRS:
        l_norm, r_norm = normalize_well(left), normalize_well(right)
        for alias in [l_norm, r_norm]:
            key = (alias, "", "alias_catalog")
            if key in seen:
                continue
            seen.add(key)
            well_rows.append(
                {
                    "well_alias": alias,
                    "well_canonical": r_norm,
                    "campaign_code": "",
                    "campaign_id": "",
                    "estimator_scope": "reference",
                    "include_for_estimator": "no",
                    "include_for_well_training": "no",
                    "source_sheet": "alias_catalog",
                    "note": "Configured alias mapping",
                }
            )

    return sorted(well_rows, key=lambda x: (x["well_alias"], x["campaign_code"], x["source_sheet"])), anomalies


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_report(campaign_rows: list[dict[str, str]], well_rows: list[dict[str, str]], anomalies: list[dict[str, str]]) -> None:
    excluded_campaigns = [r for r in campaign_rows if r["estimator_scope"] == "excluded"]
    legacy_campaigns = [r for r in campaign_rows if r["estimator_scope"] == "legacy_reference"]
    in_scope_wells = [r for r in well_rows if r["include_for_estimator"] == "yes"]
    excluded_wells = [r for r in well_rows if r["include_for_estimator"] == "no" and r["source_sheet"] != "alias_catalog"]

    lines = [
        "# Canonical Campaign and Well Mapping Report",
        "",
        "## Simplified mapping rules applied",
        "1. Campaign source of truth uses official campaign codes.",
        "2. Estimator scope is strictly limited to:",
        "   - DARAJAT_2022 (`E530-30101-D225301`)",
        "   - DARAJAT_2023_2024 (`E530-30101-D235301`)",
        "   - SALAK_2025_2026 (`E540-30101-D245401`)",
        "3. Legacy reference only: DARAJAT_2019 and SALAK_2021.",
        "4. Wayang Windu, Hamiding, and unknown categories are excluded from estimator modeling.",
        "5. Explicit well alias crosswalk is enforced from the provided canonical pairs.",
        "",
        "## Excluded records and unresolved anomalies",
        f"- Excluded campaign codes: **{len(excluded_campaigns)}**.",
        f"- Legacy-only campaign codes: **{len(legacy_campaigns)}**.",
        f"- In-scope well mapping rows: **{len(in_scope_wells)}**.",
        f"- Well rows excluded from estimator: **{len(excluded_wells)}**.",
        f"- Detected posting exceptions / anomalies: **{len(anomalies)}**.",
        "",
        "### Anomaly detail",
        "| anomaly_type | campaign_raw | well_raw | source_sheet | note |",
        "|---|---|---|---|---|",
    ]
    if anomalies:
        for a in anomalies[:20]:
            lines.append(f"| {a['anomaly_type']} | {a['campaign_raw']} | {a['well_raw']} | {a['source_sheet']} | {a['note']} |")
    else:
        lines.append("| - | - | - | - | - |")

    lines.extend(
        [
            "",
            "### Training holdout rule",
            "- `DRJ-Steam 1` is kept under `DARAJAT_2023_2024` campaign context but excluded from well-level training until confirmed.",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    campaign_rows = campaign_rows_from_sources()
    well_rows, anomalies = build_well_mapping()

    write_csv(PROCESSED_DIR / "canonical_campaign_mapping.csv", campaign_rows)
    write_csv(PROCESSED_DIR / "canonical_well_mapping.csv", well_rows)
    write_report(campaign_rows, well_rows, anomalies)
    print("Simplified canonical campaign/well mapping generated.")


if __name__ == "__main__":
    main()
