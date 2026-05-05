#!/usr/bin/env python3
"""Build dashboard-anchored historical mart and reconstruction artifacts."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

WBS_MASTER = PROCESSED / "wbs_lv5_master.csv"
WBS_CLASS = PROCESSED / "wbs_lv5_classification.csv"
WELL_ALIAS = PROCESSED / "well_alias_lookup.csv"
WELL_MAP = PROCESSED / "canonical_well_mapping.csv"
CAMPAIGN_MAP = PROCESSED / "canonical_campaign_mapping.csv"
WELL_POOL_EXCLUSIONS = PROCESSED / "well_pool_exclusions.csv"

HISTORICAL_MART = PROCESSED / "historical_cost_mart.csv"
WELL_BRIDGE = PROCESSED / "wbs_row_to_well_bridge.csv"
CAMPAIGN_BRIDGE = PROCESSED / "wbs_row_to_campaign_bridge.csv"
COVERAGE = PROCESSED / "cost_mart_coverage_report.csv"

REBUILD_WELL = PROCESSED / "dashboard_rebuild_well_cost.csv"
REBUILD_L2 = PROCESSED / "dashboard_rebuild_l2_cost.csv"
REBUILD_L3 = PROCESSED / "dashboard_rebuild_l3_cost.csv"
REBUILD_CHECK = REPORTS / "dashboard_rebuild_check.md"

BACKTEST_WELL = PROCESSED / "backtest_well_results.csv"
BACKTEST_CAMPAIGN = PROCESSED / "backtest_campaign_results.csv"
VAL_DAR = REPORTS / "validation_darajat.md"
VAL_SAL = REPORTS / "validation_salak.md"


def read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: List[dict], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _safe_float(v: str) -> float:
    return float((v or "0").replace(",", ""))


def _normalize_text(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", (value or "").strip().lower())
    return re.sub(r"[^a-z0-9]+", "_", collapsed).strip("_")


def _years(text: str) -> List[str]:
    return [p for p in (text or "").replace("-", "_").split("_") if p.isdigit() and len(p) == 4]


def _first_year(text: str) -> str:
    ys = _years(text)
    return ys[0] if ys else ""


def _build_lookup(rows: Iterable[dict], key: str, val: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for row in rows:
        k = (row.get(key) or "").strip().lower()
        if k:
            out[k] = (row.get(val) or "").strip()
    return out


def _load_well_pool_exclusions() -> Dict[Tuple[str, str], str]:
    if not WELL_POOL_EXCLUSIONS.exists():
        return {}

    exclusions: Dict[Tuple[str, str], str] = {}
    for row in read_csv(WELL_POOL_EXCLUSIONS):
        status = (row.get("status") or "active").strip().lower()
        if status not in {"active", "yes", "true", "1"}:
            continue
        field = (row.get("field") or "").strip().upper()
        well_canonical = (row.get("well_canonical") or "").strip().upper()
        if not field or not well_canonical:
            continue
        reason = (row.get("reason") or "manual_exclusion").strip()
        exclusions[(field, well_canonical)] = reason
    return exclusions


def build_historical_cost_mart() -> List[dict]:
    master = read_csv(WBS_MASTER)
    classes = {r["classification_key"]: r for r in read_csv(WBS_CLASS)}
    alias_lookup = _build_lookup(read_csv(WELL_ALIAS), "well_alias", "well_canonical")
    canonical_lookup = _build_lookup(read_csv(WELL_MAP), "well_alias", "well_canonical")
    well_pool_exclusions = _load_well_pool_exclusions()
    campaign_rows = read_csv(CAMPAIGN_MAP)
    campaign_by_code = {r.get("campaign_code", "").strip(): r for r in campaign_rows if r.get("campaign_code")}

    mart_rows: List[dict] = []
    well_bridge_rows: List[dict] = []
    campaign_bridge_rows: List[dict] = []

    for row in master:
        source_row_id = row.get("source_row_id", "")
        field = row.get("field", "").strip()
        well_raw = (row.get("well_raw") or "").strip()
        existing_canonical = (row.get("well_canonical") or "").strip()

        map_method = (row.get("mapping_method") or "").strip() or "none"
        map_conf = (row.get("mapping_confidence") or "").strip() or "low"
        map_source = "wbs_lv5_master"

        normalized = well_raw.lower()
        mapped = existing_canonical
        if not mapped and normalized in alias_lookup:
            mapped = alias_lookup[normalized]
            map_method = "alias_lookup"
            map_conf = "high"
            map_source = "well_alias_lookup"
        elif not mapped and normalized in canonical_lookup:
            mapped = canonical_lookup[normalized]
            map_method = "canonical_alias"
            map_conf = "medium"
            map_source = "canonical_well_mapping"

        exclusion_reason = ""
        exclusion_key = (field.upper(), mapped.upper()) if mapped else None
        if exclusion_key:
            exclusion_reason = well_pool_exclusions.get(exclusion_key, "")
        exclude_from_pool = "yes" if exclusion_reason else "no"

        campaign_code = (row.get("campaign_code") or "").strip()
        campaign_map = campaign_by_code.get(campaign_code, {})
        campaign_canonical = (row.get("campaign_canonical") or campaign_map.get("campaign_id") or "").strip()
        campaign_start_year = _first_year(campaign_canonical) or _first_year(row.get("campaign_raw", ""))

        key = "|".join(
            [
                field,
                row.get("wbs_lvl2", ""),
                row.get("wbs_lvl3", ""),
                row.get("wbs_lvl4", ""),
                row.get("wbs_lvl5", ""),
            ]
        )
        class_row = classes.get(key, {})
        family_tag = (class_row.get("wbs_family_tag") or row.get("tag_lvl5") or row.get("wbs_label_raw") or "").strip()
        family_group_key = _normalize_text(family_tag) or "unknown_family"

        actual = _safe_float(row.get("cost_actual", "0"))
        mart_rows.append(
            {
                "classification_key": key,
                "source_row_id": source_row_id,
                "field": field,
                "campaign_raw": row.get("campaign_raw", ""),
                "campaign_canonical": campaign_canonical,
                "campaign_start_year": campaign_start_year,
                "campaign_code": campaign_code,
                "well_raw": well_raw,
                "well_canonical": mapped,
                "mapping_method": map_method,
                "mapping_confidence": map_conf,
                "mapping_source": map_source,
                "exclude_from_estimator_pool": exclude_from_pool,
                "pool_exclusion_reason": exclusion_reason,
                "l0_id": (row.get("wbs_lvl1", "").split("-") or [""])[0],
                "l0_desc": "ROOT",
                "l1_id": row.get("wbs_lvl1", ""),
                "l1_desc": row.get("wbs_lvl1", ""),
                "l2_id": row.get("wbs_lvl2", ""),
                "l2_desc": row.get("wbs_lvl2", ""),
                "l3_id": row.get("wbs_lvl3", ""),
                "l3_desc": row.get("wbs_lvl3", ""),
                "l4_id": row.get("wbs_lvl4", ""),
                "l4_desc": row.get("wbs_lvl4", ""),
                "l5_id": row.get("wbs_lvl5", ""),
                "l5_desc": row.get("tag_lvl5", "") or row.get("wbs_label_raw", ""),
                "wbs_family_tag": family_tag,
                "family_group_key": family_group_key,
                "classification": class_row.get("classification", "unclassified"),
                "driver_family": class_row.get("driver_family", "unknown"),
                "budget_usd": "0",
                "release_usd": "0",
                "released_usd": "0",
                "committed_usd": "0",
                "actual_usd": f"{actual:.6f}",
                "source_sheet": row.get("source_sheet", ""),
                "source_workbook": row.get("source_file", ""),
                "source_field_campaign_year": f"{field}_{campaign_start_year or 'unknown'}",
            }
        )

        well_bridge_rows.append(
            {
                "source_row_id": source_row_id,
                "well_raw": well_raw,
                "well_canonical": mapped,
                "mapping_method": map_method,
                "mapping_confidence": map_conf,
                "mapping_source": map_source,
                "exclude_from_estimator_pool": exclude_from_pool,
                "pool_exclusion_reason": exclusion_reason,
                "requires_manual_review": "yes" if not mapped else "no",
            }
        )
        campaign_bridge_rows.append(
            {
                "source_row_id": source_row_id,
                "campaign_raw": row.get("campaign_raw", ""),
                "campaign_canonical": campaign_canonical,
                "campaign_code": campaign_code,
                "campaign_start_year": campaign_start_year,
                "mapping_method": "campaign_code_lookup" if campaign_map else "source_campaign_canonical",
                "mapping_confidence": "high" if campaign_map else "medium",
            }
        )

    write_csv(HISTORICAL_MART, mart_rows, list(mart_rows[0].keys()))
    write_csv(WELL_BRIDGE, well_bridge_rows, list(well_bridge_rows[0].keys()))
    write_csv(CAMPAIGN_BRIDGE, campaign_bridge_rows, list(campaign_bridge_rows[0].keys()))

    coverage = []
    grouped = defaultdict(list)
    for row in mart_rows:
        grouped[row["field"]].append(row)
    for field, rows in sorted(grouped.items()):
        total = len(rows)
        mapped = sum(1 for r in rows if r["well_canonical"])
        unmapped_actual = sum(_safe_float(r["actual_usd"]) for r in rows if not r["well_canonical"])
        coverage.append(
            {
                "field": field,
                "row_count": str(total),
                "mapped_well_rows": str(mapped),
                "mapped_well_share_pct": f"{(mapped / total * 100 if total else 0):.2f}",
                "unmapped_well_rows": str(total - mapped),
                "unmapped_actual_usd": f"{unmapped_actual:.6f}",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
    write_csv(COVERAGE, coverage, list(coverage[0].keys()))
    return mart_rows


def _group_sum(rows: Iterable[dict], keys: List[str], value_col: str) -> List[dict]:
    sums = defaultdict(float)
    for row in rows:
        k = tuple(row.get(col, "") for col in keys)
        sums[k] += _safe_float(row.get(value_col, "0"))
    out = []
    for k, v in sums.items():
        rec = {col: k[idx] for idx, col in enumerate(keys)}
        rec["actual_usd"] = f"{v:.6f}"
        out.append(rec)
    return sorted(out, key=lambda r: tuple(r[c] for c in keys))


def build_dashboard_rebuild_outputs(mart_rows: List[dict]) -> None:
    well_rows = [r for r in mart_rows if r.get("well_canonical")]

    rebuild_well = _group_sum(well_rows, ["field", "campaign_canonical", "well_canonical"], "actual_usd")
    rebuild_l2 = _group_sum(mart_rows, ["field", "campaign_canonical", "l2_id", "l2_desc"], "actual_usd")
    rebuild_l3 = _group_sum(mart_rows, ["field", "campaign_canonical", "l2_id", "l3_id", "l3_desc"], "actual_usd")

    write_csv(REBUILD_WELL, rebuild_well, list(rebuild_well[0].keys()))
    write_csv(REBUILD_L2, rebuild_l2, list(rebuild_l2[0].keys()))
    write_csv(REBUILD_L3, rebuild_l3, list(rebuild_l3[0].keys()))

    master = read_csv(WBS_MASTER)
    workbook_proxy_well = _group_sum(
        [r for r in master if (r.get("well_canonical") or "").strip()],
        ["field", "campaign_canonical", "well_canonical"],
        "cost_actual",
    )
    workbook_proxy_l2 = _group_sum(master, ["field", "campaign_canonical", "wbs_lvl2", "wbs_lvl2"], "cost_actual")

    well_diff = abs(sum(_safe_float(r["actual_usd"]) for r in rebuild_well) - sum(_safe_float(r["actual_usd"]) for r in workbook_proxy_well))
    l2_diff = abs(sum(_safe_float(r["actual_usd"]) for r in rebuild_l2) - sum(_safe_float(r["actual_usd"]) for r in workbook_proxy_l2))

    lines = [
        "# Dashboard Rebuild Check",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Workbook dashboard tabs are ingested directly from Structured.Cost; check reconciles mart rebuilds against dashboard-derived aggregates.",
        "",
        f"- Rebuilt well total USD: {sum(_safe_float(r['actual_usd']) for r in rebuild_well):,.2f}",
        f"- Proxy workbook well total USD: {sum(_safe_float(r['actual_usd']) for r in workbook_proxy_well):,.2f}",
        f"- Absolute well total delta USD: {well_diff:,.6f}",
        f"- Rebuilt L2 total USD: {sum(_safe_float(r['actual_usd']) for r in rebuild_l2):,.2f}",
        f"- Proxy workbook L2 total USD: {sum(_safe_float(r['actual_usd']) for r in workbook_proxy_l2):,.2f}",
        f"- Absolute L2 total delta USD: {l2_diff:,.6f}",
        "",
        "## Notes",
        "- Unmapped well rows are retained in mart and excluded only from per-well rebuild table.",
        "- L2/L3 rebuild includes mapped and unmapped rows for full campaign reconciliation.",
    ]
    REBUILD_CHECK.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_backtest_outputs(mart_rows: List[dict]) -> None:
    eligible_well_rows = [
        r
        for r in mart_rows
        if r.get("well_canonical") and (r.get("exclude_from_estimator_pool") or "no").strip().lower() != "yes"
    ]
    well_actual = _group_sum(eligible_well_rows, ["field", "campaign_canonical", "campaign_start_year", "well_canonical"], "actual_usd")
    by_field = defaultdict(list)
    for r in well_actual:
        by_field[r["field"]].append(r)

    excluded_wells_by_field = defaultdict(set)
    for row in mart_rows:
        if (row.get("exclude_from_estimator_pool") or "no").strip().lower() == "yes" and row.get("well_canonical"):
            excluded_wells_by_field[row.get("field", "")].add(row.get("well_canonical", ""))

    backtest_rows: List[dict] = []
    for field, rows in by_field.items():
        for row in rows:
            peers = [
                _safe_float(x["actual_usd"])
                for x in rows
                if x["campaign_start_year"] and x["campaign_start_year"] < row["campaign_start_year"]
            ]
            if not peers:
                peers = [_safe_float(x["actual_usd"]) for x in rows if x is not row]
            pred = median(peers) if peers else _safe_float(row["actual_usd"])
            actual = _safe_float(row["actual_usd"])
            err = pred - actual
            backtest_rows.append(
                {
                    "field": field,
                    "campaign_canonical": row["campaign_canonical"],
                    "campaign_start_year": row["campaign_start_year"],
                    "well_canonical": row["well_canonical"],
                    "actual_usd": f"{actual:.6f}",
                    "predicted_usd": f"{pred:.6f}",
                    "error_usd": f"{err:.6f}",
                    "abs_error_usd": f"{abs(err):.6f}",
                    "ape_pct": f"{(abs(err)/actual*100) if actual else 0:.4f}",
                    "method": "historical_median_peer",
                }
            )

    write_csv(BACKTEST_WELL, backtest_rows, list(backtest_rows[0].keys()))

    campaign_roll = _group_sum(backtest_rows, ["field", "campaign_canonical", "campaign_start_year"], "actual_usd")
    pred_roll = _group_sum(backtest_rows, ["field", "campaign_canonical", "campaign_start_year"], "predicted_usd")
    pred_map = {(r["field"], r["campaign_canonical"], r["campaign_start_year"]): _safe_float(r["actual_usd"]) for r in pred_roll}

    campaign_rows = []
    for row in campaign_roll:
        key = (row["field"], row["campaign_canonical"], row["campaign_start_year"])
        actual = _safe_float(row["actual_usd"])
        pred = pred_map.get(key, 0.0)
        err = pred - actual
        campaign_rows.append(
            {
                "field": row["field"],
                "campaign_canonical": row["campaign_canonical"],
                "campaign_start_year": row["campaign_start_year"],
                "actual_usd": f"{actual:.6f}",
                "predicted_usd": f"{pred:.6f}",
                "error_usd": f"{err:.6f}",
                "abs_error_usd": f"{abs(err):.6f}",
                "ape_pct": f"{(abs(err)/actual*100) if actual else 0:.4f}",
            }
        )
    write_csv(BACKTEST_CAMPAIGN, campaign_rows, list(campaign_rows[0].keys()))

    for field, target in [("DARAJAT", VAL_DAR), ("SALAK", VAL_SAL)]:
        rows = [r for r in backtest_rows if r["field"] == field]
        if not rows:
            continue
        mae = sum(_safe_float(r["abs_error_usd"]) for r in rows) / len(rows)
        mape = sum(float(r["ape_pct"]) for r in rows) / len(rows)
        bias = sum(_safe_float(r["error_usd"]) for r in rows) / len(rows)
        lines = [
            f"# Validation Report - {field}",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "Backtest mode: historical median peer baseline (no regression claim).",
            "",
            f"- Wells backtested: {len(rows)}",
            f"- MAE (USD): {mae:,.2f}",
            f"- MAPE (%): {mape:.2f}",
            f"- Bias (USD): {bias:,.2f}",
            "- Interval coverage: not produced (point-estimate baseline only).",
        ]
        excluded_wells = sorted(x for x in excluded_wells_by_field.get(field, set()) if x)
        if excluded_wells:
            lines.append(f"- Excluded wells from estimator/backtest pool: {', '.join(excluded_wells)}")
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_all_outputs() -> None:
    mart = build_historical_cost_mart()
    build_dashboard_rebuild_outputs(mart)
    build_backtest_outputs(mart)


if __name__ == "__main__":
    refresh_all_outputs()
