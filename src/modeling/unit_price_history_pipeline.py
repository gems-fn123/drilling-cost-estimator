#!/usr/bin/env python3
"""Build dashboard-driven unit-price history artifacts."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

from src.config import CAMPAIGN_LABEL_TO_CODE, DASHBOARD_WORKBOOK, PROCESSED, RAW_DIR
from src.io.build_canonical_mappings import (
    clean_text,
    extract_full_table,
    normalize_well,
    read_xlsx,
)
from src.utils import parse_float, read_csv, write_csv

log = logging.getLogger(__name__)

CAMPAIGN_MAP = PROCESSED / "canonical_campaign_mapping.csv"
WELL_MASTER = PROCESSED / "well_master.csv"
WELL_ALIAS = PROCESSED / "well_alias_lookup.csv"

UNIT_PRICE_HISTORY_MART = PROCESSED / "unit_price_history_mart.csv"
UNIT_PRICE_HISTORY_CONTEXT = PROCESSED / "unit_price_history_context.csv"


def normalize_field(asset: str) -> str:
    value = clean_text(asset).upper()
    if value in {"DRJ", "DARAJAT"}:
        return "DARAJAT"
    if value in {"SLK", "SALAK"}:
        return "SALAK"
    if value in {"WAYANG WINDU", "WW", "WAYANG_WINDU"}:
        return "WAYANG_WINDU"
    return value


def campaign_year_from_text(text: str) -> str:
    match = re.search(r"(20\d{2})", clean_text(text))
    return match.group(1) if match else ""


def load_campaign_lookup() -> Dict[str, dict]:
    rows = read_csv(CAMPAIGN_MAP)
    lookup: Dict[str, dict] = {}
    for row in rows:
        if row.get("include_for_estimator") != "yes":
            continue
        lookup[row["campaign_code"]] = row
    return lookup


def load_well_lookup() -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    alias_rows = read_csv(WELL_ALIAS)
    for row in alias_rows:
        if row.get("alias_type") == "manual_alias":
            continue
        alias = normalize_well(row.get("well_alias", ""))
        canonical = normalize_well(row.get("well_canonical", ""))
        if alias and canonical:
            lookup[alias] = canonical
    for row in alias_rows:
        if row.get("alias_type") != "manual_alias":
            continue
        alias = normalize_well(row.get("well_alias", ""))
        canonical = normalize_well(row.get("well_canonical", ""))
        if alias and canonical:
            lookup[alias] = canonical
    for row in read_csv(WELL_MASTER):
        canonical = normalize_well(row.get("well_canonical", ""))
        if canonical and canonical not in lookup:
            lookup[canonical] = canonical
    return lookup


def load_dashboard_tables() -> Tuple[List[dict], List[dict]]:
    workbook = read_xlsx(RAW_DIR / DASHBOARD_WORKBOOK)
    structured_rows = extract_full_table(
        workbook.get("Structured.Cost", []),
        ["Asset", "Campaign", "Level 2", "Level 3", "Level 4", "Level 5", "Well", "Actual Cost USD"],
    )
    general_rows = extract_full_table(
        workbook.get("General.Camp.Data", []),
        [
            "Asset",
            "Campaign",
            "WBS CODE",
            "Well Name Actual",
            "Well Name SAP",
            "Well Name Alt 1",
            "Well Name Alt 2",
            "Actual depth, ft MD",
            "Drilling Duration, days equivalent",
            "NPT hours",
        ],
    )
    return structured_rows, general_rows


def build_context_lookup(general_rows: List[dict], campaign_lookup: Dict[str, dict], well_lookup: Dict[str, str]) -> Tuple[Dict[Tuple[str, str], dict], List[dict]]:
    context_lookup: Dict[Tuple[str, str], dict] = {}
    context_rows: List[dict] = []

    for row in general_rows:
        campaign_code = CAMPAIGN_LABEL_TO_CODE.get(clean_text(row.get("Campaign", "")).upper(), clean_text(row.get("WBS CODE", "")).upper())
        if campaign_code not in campaign_lookup:
            continue

        meta = campaign_lookup[campaign_code]
        actual_depth = parse_float(row.get("Actual depth, ft MD", ""))
        actual_days = parse_float(row.get("Drilling Duration, days equivalent", ""))
        npt_days = parse_float(row.get("NPT hours", "")) / 24.0
        active_days = max(actual_days - npt_days, 0.0)
        canonical_actual = normalize_well(row.get("Well Name Actual", ""))
        well_canonical = well_lookup.get(canonical_actual, canonical_actual)

        context_row = {
            "field": meta["field"],
            "campaign_code": campaign_code,
            "campaign_canonical": meta["campaign_id"],
            "campaign_year": campaign_year_from_text(row.get("Campaign", "")) or campaign_year_from_text(meta["campaign_id"]),
            "well_canonical": well_canonical,
            "well_name_actual": clean_text(row.get("Well Name Actual", "")),
            "actual_depth_ft": f"{actual_depth:.6f}",
            "actual_days": f"{actual_days:.6f}",
            "npt_days": f"{npt_days:.6f}",
            "active_operational_days": f"{active_days:.6f}",
            "source_workbook": DASHBOARD_WORKBOOK,
            "source_sheet": "General.Camp.Data",
        }
        context_rows.append(context_row)

        for key in ["Well Name Actual", "Well Name SAP", "Well Name Alt 1", "Well Name Alt 2"]:
            alias = normalize_well(row.get(key, ""))
            if alias:
                context_lookup[(campaign_code, alias)] = context_row
                context_lookup[(campaign_code, well_lookup.get(alias, alias))] = context_row

    return context_lookup, context_rows


def infer_pricing_basis(level3: str, level4: str, well_raw: str) -> str:
    l3 = clean_text(level3).lower()
    l4 = clean_text(level4).lower()
    well = normalize_well(well_raw)
    if l3 == "well cost" and l4 == "services":
        return "active_day_rate"
    if l3 == "well cost" and "material" in l4:
        return "depth_rate"
    if l3 in {"tie-in", "rig mobilization", "rig move", "road & pad", "special requirement existing pad"}:
        return "campaign_scope_benchmark"
    if well and well != "GENERAL":
        return "per_well_job"
    return "campaign_scope_benchmark"


def infer_quantity(pricing_basis: str, context_row: dict | None, well_raw: str) -> Tuple[str, float]:
    if pricing_basis == "active_day_rate" and context_row:
        return "active_operational_day", parse_float(context_row.get("active_operational_days", "0"))
    if pricing_basis == "depth_rate" and context_row:
        return "ft_md", parse_float(context_row.get("actual_depth_ft", "0"))
    if pricing_basis == "per_well_job" and normalize_well(well_raw) != "GENERAL":
        return "well", 1.0
    return "campaign", 1.0


def build_unit_price_history_mart() -> Tuple[List[dict], List[dict]]:
    campaign_lookup = load_campaign_lookup()
    well_lookup = load_well_lookup()
    structured_rows, general_rows = load_dashboard_tables()
    context_lookup, context_rows = build_context_lookup(general_rows, campaign_lookup, well_lookup)

    mart_rows: List[dict] = []
    for idx, row in enumerate(structured_rows, start=1):
        campaign_label = clean_text(row.get("Campaign", ""))
        campaign_code = CAMPAIGN_LABEL_TO_CODE.get(campaign_label.upper(), "")
        if campaign_code not in campaign_lookup:
            continue

        meta = campaign_lookup[campaign_code]
        well_raw = clean_text(row.get("Well", ""))
        well_alias = normalize_well(well_raw)
        well_canonical = well_lookup.get(well_alias, well_alias if well_alias != "GENERAL" else "")
        context_row = context_lookup.get((campaign_code, well_alias)) or context_lookup.get((campaign_code, well_canonical))
        pricing_basis = infer_pricing_basis(row.get("Level 3", ""), row.get("Level 4", ""), well_raw)
        quantity_basis, quantity_value = infer_quantity(pricing_basis, context_row, well_raw)
        actual_cost = parse_float(row.get("Actual Cost USD", ""))
        unit_price = actual_cost / quantity_value if quantity_value else 0.0
        data_quality_flag = "ok"
        if pricing_basis in {"active_day_rate", "depth_rate"} and quantity_value <= 0:
            data_quality_flag = "missing_quantity"

        mart_rows.append(
            {
                "field": meta["field"],
                "campaign_canonical": meta["campaign_id"],
                "campaign_code": campaign_code,
                "campaign_raw": campaign_label,
                "campaign_year": campaign_year_from_text(campaign_label) or campaign_year_from_text(meta["campaign_id"]),
                "well_raw": well_raw,
                "well_canonical": well_canonical if well_canonical != "GENERAL" else "",
                "level_2": clean_text(row.get("Level 2", "")),
                "level_3": clean_text(row.get("Level 3", "")),
                "level_4": clean_text(row.get("Level 4", "")),
                "level_5": clean_text(row.get("Level 5", "")),
                "pricing_basis": pricing_basis,
                "unit_price_basis": quantity_basis,
                "quantity_value": f"{quantity_value:.6f}",
                "unit_price_usd": f"{unit_price:.6f}",
                "actual_cost_usd": f"{actual_cost:.6f}",
                "actual_depth_ft": context_row.get("actual_depth_ft", "") if context_row else "",
                "actual_days": context_row.get("actual_days", "") if context_row else "",
                "npt_days": context_row.get("npt_days", "") if context_row else "",
                "active_operational_days": context_row.get("active_operational_days", "") if context_row else "",
                "data_quality_flag": data_quality_flag,
                "source_workbook": DASHBOARD_WORKBOOK,
                "source_sheet": "Structured.Cost",
                "source_row_key": str(idx),
            }
        )

    mart_rows.sort(key=lambda r: (r["field"], r["campaign_year"], r["level_3"], r["level_4"], r["level_5"], r["well_canonical"], r["source_row_key"]))
    context_rows.sort(key=lambda r: (r["field"], r["campaign_year"], r["well_canonical"]))
    return mart_rows, context_rows


def main() -> None:
    mart_rows, context_rows = build_unit_price_history_mart()
    write_csv(UNIT_PRICE_HISTORY_MART, mart_rows, list(mart_rows[0].keys()))
    write_csv(UNIT_PRICE_HISTORY_CONTEXT, context_rows, list(context_rows[0].keys()))
    print("Wrote unit_price_history_mart and unit_price_history_context.")


if __name__ == "__main__":
    main()
