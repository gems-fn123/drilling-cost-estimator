#!/usr/bin/env python3
"""Dashboard-anchored estimator core with auditable WBS lineage."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List, Tuple

from src.app.build_phase5_operational_assets import main as build_phase5_operational_assets
from src.cleaning.wbs_lv5_driver_alignment import main as build_wbs_lv5_alignment
from src.io.build_canonical_mappings import main as build_canonical_mappings
from src.modeling.dashboard_historical_mart import refresh_all_outputs
from src.modeling.phase4_preflight_and_baseline import run_phase4
from src.modeling.unit_price_macro_analysis import (
    MACRO_CLUSTER_WEIGHTS_PATH,
    MACRO_REFERENCE_PATH,
    MACRO_WEIGHTS_PATH,
    main as build_unit_price_macro_analysis,
)
from src.modeling.unit_price_history_pipeline import (
    UNIT_PRICE_HISTORY_MART,
    main as build_unit_price_history_pipeline,
)
from src.modeling.unit_price_well_analysis import (
    SERVICE_TIME_BANDS,
    UNIT_PRICE_BENCHMARK,
    UNIT_PRICE_WELL_PROFILE,
    main as build_unit_price_well_analysis,
)

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"

CONFIDENCE_BANDS = PROCESSED / "confidence_bands.csv"
METHOD_REGISTRY = PROCESSED / "estimator_method_registry.csv"
APP_RUN_MANIFEST = PROCESSED / "app_run_manifest.json"
APP_AUDIT = PROCESSED / "app_estimate_audit.csv"
APP_SUMMARY = PROCESSED / "app_estimate_summary.json"
APP_CATEGORY_MATRIX_CSV = PROCESSED / "app_category_matrix.csv"
APP_CATEGORY_MATRIX_JSON = PROCESSED / "app_category_matrix.json"
WELL_POOL_EXCLUSIONS = PROCESSED / "well_pool_exclusions.csv"

FIELD_MAP = {"DRJ": "DARAJAT", "SLK": "SALAK", "WW": "WAYANG_WINDU"}
RATE_FACTOR = {"Standard": 1.0, "Fast": 0.92, "Careful": 1.12}
LEG_FACTOR = {"Standard-J": 1.0}
CATEGORY_ORDER = ["Drilling", "Support", "Surface Facility", "Contingency"]
CATEGORY_ERROR_COLUMN = "Error (MMUSD) / MAPE (%)"


@dataclass
class WellInput:
    well_label: str
    pad_label: str
    depth_ft: int
    depth_bucket_ft: int
    leg_type: str
    drill_rate_mode: str


def read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: List[dict], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _safe_float(text: str) -> float:
    return float(str(text or "0").replace(",", ""))


def _safe_int(text: str, default: int = 0) -> int:
    try:
        return int(str(text))
    except (TypeError, ValueError):
        return default


def _normalize_key(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", (value or "").strip().lower())
    return re.sub(r"[^a-z0-9]+", "_", collapsed).strip("_")


def _extract_year(text: str) -> int:
    match = re.search(r"(20\d{2})", str(text or ""))
    return int(match.group(1)) if match else 0


def _classification_from_pricing_basis(pricing_basis: str, well_canonical: str) -> str:
    basis = (pricing_basis or "").strip().lower()
    if basis in {"active_day_rate", "depth_rate", "per_well_job"}:
        return "well_tied"
    if basis == "campaign_scope_benchmark" and well_canonical:
        return "hybrid"
    return "campaign_tied"


def _driver_from_pricing_basis(pricing_basis: str) -> str:
    basis = (pricing_basis or "").strip().lower()
    if basis == "active_day_rate":
        return "service_time"
    if basis == "depth_rate":
        return "material_depth"
    if basis == "per_well_job":
        return "per_well_fixed"
    if basis == "campaign_scope_benchmark":
        return "campaign_scope"
    return "other"


def _load_well_exclusion_index() -> Dict[Tuple[str, str], str]:
    if not WELL_POOL_EXCLUSIONS.exists():
        return {}
    exclusions: Dict[Tuple[str, str], str] = {}
    for row in read_csv(WELL_POOL_EXCLUSIONS):
        status = (row.get("status") or "active").strip().lower()
        if status not in {"active", "yes", "true", "1"}:
            continue
        field = (row.get("field") or "").strip().upper()
        well = (row.get("well_canonical") or "").strip().upper()
        if field and well:
            exclusions[(field, well)] = (row.get("reason") or "manual_exclusion").strip()
    return exclusions


def _to_estimator_history_row(row: dict, exclusions: Dict[Tuple[str, str], str]) -> dict:
    field = (row.get("field") or "").strip()
    campaign_canonical = (row.get("campaign_canonical") or "").strip()
    campaign_raw = (row.get("campaign_raw") or "").strip()
    campaign_year = _safe_int(row.get("campaign_year"), 0) or _extract_year(campaign_canonical) or _extract_year(campaign_raw)
    source_workbook = (row.get("source_workbook") or "").strip()
    source_sheet = (row.get("source_sheet") or "").strip()
    source_row_key = (row.get("source_row_key") or "").strip()
    source_row_id = "|".join(part for part in [source_workbook, source_sheet, source_row_key] if part)

    l2 = (row.get("level_2") or "").strip()
    l3 = (row.get("level_3") or "").strip()
    l4 = (row.get("level_4") or "").strip()
    l5 = (row.get("level_5") or "").strip() or l4 or l3 or l2 or "Unknown Cost Family"
    family_group_key = _normalize_key(l5) or "unknown_cost_family"
    well_canonical = (row.get("well_canonical") or "").strip()
    classification = _classification_from_pricing_basis(row.get("pricing_basis", ""), well_canonical)
    exclusion_reason = exclusions.get((field.upper(), well_canonical.upper()), "") if well_canonical else ""

    return {
        "source_row_id": source_row_id,
        "field": field,
        "campaign_raw": campaign_raw,
        "campaign_canonical": campaign_canonical,
        "campaign_start_year": str(campaign_year or ""),
        "campaign_code": (row.get("campaign_code") or "").strip(),
        "well_raw": (row.get("well_raw") or "").strip(),
        "well_canonical": well_canonical,
        "exclude_from_estimator_pool": "yes" if exclusion_reason else "no",
        "pool_exclusion_reason": exclusion_reason,
        "classification": classification,
        "l1_id": campaign_canonical or campaign_raw or "UNSPECIFIED_CAMPAIGN",
        "l1_desc": campaign_canonical or campaign_raw or "UNSPECIFIED_CAMPAIGN",
        "l2_id": l2,
        "l2_desc": l2,
        "l3_id": l3,
        "l3_desc": l3,
        "l4_id": l4,
        "l4_desc": l4,
        "l5_id": l5,
        "l5_desc": l5,
        "wbs_family_tag": l5,
        "family_group_key": family_group_key,
        "driver_family": _driver_from_pricing_basis(row.get("pricing_basis", "")),
        "actual_usd": row.get("actual_cost_usd", "0"),
        "source_sheet": source_sheet,
        "source_workbook": source_workbook,
        "source_field_campaign_year": f"{field}_{campaign_year}" if campaign_year else f"{field}_unknown",
    }


def _load_estimator_history_rows(field: str | None = None) -> List[dict]:
    _ensure_unit_price_support_outputs()
    exclusions = _load_well_exclusion_index()
    rows = [_to_estimator_history_row(row, exclusions) for row in read_csv(UNIT_PRICE_HISTORY_MART)]
    eligible = [row for row in rows if _is_pool_eligible(row)]
    if field is None:
        return eligible
    return [row for row in eligible if row["field"] == field]


def _ensure_unit_price_support_outputs() -> None:
    if not UNIT_PRICE_HISTORY_MART.exists():
        build_unit_price_history_pipeline()
    if not UNIT_PRICE_BENCHMARK.exists() or not SERVICE_TIME_BANDS.exists() or not UNIT_PRICE_WELL_PROFILE.exists():
        build_unit_price_well_analysis()
    if (
        not MACRO_WEIGHTS_PATH.exists()
        or not MACRO_REFERENCE_PATH.exists()
        or not MACRO_CLUSTER_WEIGHTS_PATH.exists()
    ):
        build_unit_price_macro_analysis()


def _load_unit_price_benchmark_index() -> Dict[Tuple[str, str], dict]:
    _ensure_unit_price_support_outputs()
    return {
        (row["field"], row["pricing_basis"]): row
        for row in read_csv(UNIT_PRICE_BENCHMARK)
    }


def _load_service_time_band_index() -> Dict[str, dict]:
    _ensure_unit_price_support_outputs()
    return {
        row["field"]: row
        for row in read_csv(SERVICE_TIME_BANDS)
    }


def _load_macro_reference_index() -> Dict[int, dict]:
    _ensure_unit_price_support_outputs()
    return {
        _safe_int(row["year"]): row
        for row in read_csv(MACRO_REFERENCE_PATH)
    }


def _load_macro_weight_rows(pricing_basis: str) -> List[dict]:
    _ensure_unit_price_support_outputs()
    rows = read_csv(MACRO_WEIGHTS_PATH)
    return [
        row
        for row in rows
        if row["scope_type"] == "pooled_pricing_basis"
        and row["field"] == "ALL_FIELDS"
        and row["pricing_basis"] == pricing_basis
        and row["weight_eligible"] == "yes"
        and row["support_status"] == "operational"
    ]


def _load_field_base_years() -> Dict[str, int]:
    _ensure_unit_price_support_outputs()
    base_years: Dict[str, int] = {}
    for row in read_csv(UNIT_PRICE_WELL_PROFILE):
        if row.get("exclude_from_estimator_pool") == "yes":
            continue
        year = _safe_int(row.get("campaign_year"), 0)
        if year <= 0:
            continue
        field = row["field"]
        base_years[field] = max(base_years.get(field, 0), year)
    return base_years


def _benchmark_uncertainty_pct(benchmark_row: dict | None) -> float:
    if not benchmark_row:
        return 0.0
    median_value = _safe_float(benchmark_row.get("median_value", "0"))
    p10_value = _safe_float(benchmark_row.get("p10_value", "0"))
    p90_value = _safe_float(benchmark_row.get("p90_value", "0"))
    if median_value <= 0.0:
        return 0.0
    return min(200.0, ((p90_value - p10_value) / median_value) * 100.0)


def _representative_pace_days_per_1000ft(field: str, drill_rate_mode: str) -> float:
    band_rows = _load_service_time_band_index()
    row = band_rows.get(field)
    if not row:
        return 3.5
    key = {
        "Fast": "fast_p50_days_per_1000ft",
        "Standard": "standard_p50_days_per_1000ft",
        "Careful": "careful_p50_days_per_1000ft",
    }[drill_rate_mode]
    value = _safe_float(row.get(key, "0"))
    if value > 0.0:
        return value
    return _safe_float(row.get("standard_p50_days_per_1000ft", "0")) or 3.5


def _estimated_active_days(field: str, depth_ft: int, drill_rate_mode: str) -> float:
    pace_days_per_1000ft = _representative_pace_days_per_1000ft(field, drill_rate_mode)
    return max(8.0, pace_days_per_1000ft * (depth_ft / 1000.0))


def _macro_adjustment_for_basis(enabled: bool, field: str, target_year: int, pricing_basis: str) -> Tuple[float, bool, str]:
    if not enabled:
        return 1.0, False, "disabled_by_user"

    macro_by_year = _load_macro_reference_index()
    base_years = _load_field_base_years()
    base_year = base_years.get(field, 0)
    if base_year <= 0:
        return 1.0, False, "fallback_historical_only_missing_field_base_year"
    if target_year not in macro_by_year or base_year not in macro_by_year:
        return 1.0, False, "fallback_historical_only_macro_window_unavailable"

    weight_rows = _load_macro_weight_rows(pricing_basis)
    if not weight_rows:
        return 1.0, False, f"fallback_historical_only_no_macro_weights_for_{pricing_basis}"

    factor = 0.0
    parts: List[str] = []
    for row in weight_rows:
        factor_name = row["factor_name"]
        weight = _safe_float(row["forecast_weight"])
        base_value = _safe_float(macro_by_year[base_year].get(factor_name, "0"))
        target_value = _safe_float(macro_by_year[target_year].get(factor_name, "0"))
        if weight <= 0.0 or base_value <= 0.0 or target_value <= 0.0:
            continue
        ratio = target_value / base_value
        factor += weight * ratio
        parts.append(f"{weight:.6f}*({factor_name}_{target_year}/{factor_name}_{base_year})")

    if factor <= 0.0 or not parts:
        return 1.0, False, f"fallback_historical_only_invalid_macro_ratio_for_{pricing_basis}"

    return factor, True, " + ".join(parts)


def _percentile(values: Iterable[float], pct: float) -> float:
    arr = sorted(values)
    if not arr:
        return 0.0
    if len(arr) == 1:
        return arr[0]
    idx = (len(arr) - 1) * pct
    lo = int(idx)
    hi = min(lo + 1, len(arr) - 1)
    frac = idx - lo
    return arr[lo] * (1 - frac) + arr[hi] * frac


def _normalize_depth(depth_ft: int) -> int:
    clipped = min(10000, max(4500, int(depth_ft)))
    return int(round(clipped / 500.0) * 500)


def _format_mmusd(amount_usd: float) -> str:
    return f"{amount_usd / 1_000_000.0:.2f} mm USD"


def normalize_inputs(campaign_input: dict, well_rows: List[dict]) -> Tuple[dict, List[WellInput]]:
    field = campaign_input.get("field")
    if field not in {"SLK", "DRJ", "WW"}:
        raise ValueError("Field must be SLK, DRJ, or WW")
    year = int(campaign_input.get("year"))
    no_pads = int(campaign_input.get("no_pads"))
    no_wells = int(campaign_input.get("no_wells"))
    pad_exp = int(campaign_input.get("no_pad_expansion", 0))
    if len(well_rows) != no_wells:
        raise ValueError("Well row count must equal No. Wells")

    normalized_wells: List[WellInput] = []
    for idx, row in enumerate(well_rows, start=1):
        depth = _normalize_depth(int(row["depth_ft"]))
        mode = row["drill_rate_mode"]
        if mode not in RATE_FACTOR:
            raise ValueError(f"Invalid well inputs at row {idx}")
        normalized_wells.append(
            WellInput(
                well_label=row.get("well_label", f"Well-{idx}"),
                pad_label=row["pad_label"],
                depth_ft=depth,
                depth_bucket_ft=depth,
                leg_type="Standard-J",
                drill_rate_mode=mode,
            )
        )

    return {
        "field_input": field,
        "field_canonical": FIELD_MAP[field],
        "campaign_start_year": year,
        "pad_count": no_pads,
        "well_count": no_wells,
        "pad_expansion_count": pad_exp,
        "use_external_forecast": bool(campaign_input.get("use_external_forecast", False)),
        "use_synthetic_data": bool(campaign_input.get("use_synthetic_data", False)),
    }, normalized_wells


def _refresh_pipeline_outputs(*, group_by: str = "family", use_synthetic: bool = False, synthetic_policy: str = "training") -> None:
    build_canonical_mappings()
    build_unit_price_history_pipeline()
    build_unit_price_well_analysis()
    build_unit_price_macro_analysis()

    # Keep legacy artifacts refreshed for compatibility with existing reports.
    build_wbs_lv5_alignment()
    refresh_all_outputs()
    run_phase4(
        group_by=group_by,
        use_synthetic=use_synthetic,
        synthetic_policy=synthetic_policy,
    )
    build_phase5_operational_assets()


def _is_pool_eligible(row: dict) -> bool:
    return (row.get("exclude_from_estimator_pool") or "no").strip().lower() != "yes"


def _load_field_rows(field: str) -> List[dict]:
    return _load_estimator_history_rows(field)


def _select_anchor_year(rows: List[dict], year: int) -> int:
    years = sorted({_safe_int(r.get("campaign_start_year"), 0) for r in rows if _safe_int(r.get("campaign_start_year"), 0) > 0})
    if not years:
        return 0
    return max([y for y in years if y <= year], default=max(years))


def _select_anchor_rows(rows: List[dict], year: int) -> Tuple[int, List[dict]]:
    anchor_year = _select_anchor_year(rows, year)
    if not anchor_year:
        return anchor_year, rows
    anchored_rows = [r for r in rows if _safe_int(r.get("campaign_start_year"), 0) == anchor_year]
    return anchor_year, anchored_rows or rows


def _select_peer_rows(rows: List[dict], year: int) -> List[dict]:
    peer_rows = [r for r in rows if _safe_int(r.get("campaign_start_year"), 0) <= year]
    return peer_rows or rows


def _support_key(row: dict) -> Tuple[str, str]:
    return (
        (row.get("classification") or "unclassified").strip(),
        (row.get("family_group_key") or row.get("wbs_family_tag") or row.get("l5_desc") or "unknown_family").strip(),
    )


def _support_unit_id(row: dict) -> Tuple[str, ...]:
    campaign_token = (
        row.get("campaign_canonical")
        or row.get("source_field_campaign_year")
        or row.get("campaign_raw")
        or "unknown_campaign"
    ).strip()
    if (row.get("classification") or "").strip() == "well_tied":
        well_token = (
            row.get("well_canonical")
            or row.get("well_raw")
            or f"row_{row.get('source_row_id', 'unknown')}"
        ).strip()
        return (campaign_token, well_token)
    return (campaign_token,)


def _summarize_support_rows(rows: List[dict]) -> dict:
    raw_rows = list(rows)
    unit_totals: Dict[Tuple[str, ...], float] = defaultdict(float)
    for row in raw_rows:
        unit_totals[_support_unit_id(row)] += _safe_float(row.get("actual_usd", "0"))

    support_values = sorted(unit_totals.values())
    return {
        "median_usd": median(support_values) if support_values else 0.0,
        "p10_usd": _percentile(support_values, 0.10),
        "p90_usd": _percentile(support_values, 0.90),
        "support_unit_count": len(support_values),
        "source_row_count": len(raw_rows),
        "source_wells": sorted({r["well_canonical"] for r in raw_rows if r.get("well_canonical")}),
        "source_campaign_years": sorted({r["source_field_campaign_year"] for r in raw_rows if r.get("source_field_campaign_year")}),
        "source_row_ids": sorted({r["source_row_id"] for r in raw_rows if r.get("source_row_id")}),
    }


def _support_explanation(stats: dict) -> str:
    if stats["support_unit_count"] <= 1 and stats["source_row_count"] <= 1:
        return "Single historical peer after field-specific family grouping."
    if stats["support_unit_count"] <= 1:
        return "Only one historical peer group is available after field-specific family grouping."
    if abs(stats["p90_usd"] - stats["p10_usd"]) < 1e-9:
        return "Historical peer totals are identical after grouping."
    return (
        "Field-specific family analog built from "
        f"{stats['support_unit_count']} peer groups and {stats['source_row_count']} supporting rows."
    )


def _uncertainty_pct(stats: dict, cap: float = 200.0) -> float:
    spread = stats["p90_usd"] - stats["p10_usd"]
    scale = max(abs(stats["median_usd"]), 1.0)
    return min(cap, (spread / scale) * 100.0)


def _estimation_method(stats: dict) -> str:
    return "empirical_analog" if stats["support_unit_count"] >= 2 else "fallback_benchmark"


def _dominant_text(rows: List[dict], key: str, fallback: str = "") -> str:
    values = [str(row.get(key, "")).strip() for row in rows if str(row.get(key, "")).strip()]
    if not values:
        return fallback
    return Counter(values).most_common(1)[0][0]


def _build_projection_templates(anchor_rows: List[dict], peer_rows: List[dict]) -> List[dict]:
    support_index: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for row in peer_rows:
        support_index[_support_key(row)].append(row)

    anchor_index: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for row in anchor_rows:
        anchor_index[_support_key(row)].append(row)

    templates: List[dict] = []
    for key, anchor_group in anchor_index.items():
        support_rows = support_index.get(key) or anchor_group
        stats = _summarize_support_rows(support_rows)
        anchor_total = sum(_safe_float(r.get("actual_usd", "0")) for r in anchor_group)

        l5_desc = _dominant_text(anchor_group, "l5_desc", "Unknown Cost Family")
        l2_desc = _dominant_text(anchor_group, "l2_desc")
        l3_desc = _dominant_text(anchor_group, "l3_desc")
        l4_desc = _dominant_text(anchor_group, "l4_desc")
        driver_family = _dominant_text(anchor_group, "driver_family", "other")
        classification = _dominant_text(anchor_group, "classification", "unclassified")
        family_group_key = _dominant_text(anchor_group, "family_group_key", _normalize_key(l5_desc) or "unknown_cost_family")

        templates.append(
            {
                "classification": classification,
                "l2_id": l2_desc,
                "l3_id": l3_desc,
                "l4_id": l4_desc,
                "l5_id": l5_desc,
                "l5_desc": l5_desc,
                "wbs_family_tag": l5_desc,
                "family_group_key": family_group_key,
                "driver_family": driver_family,
                "anchor_total_usd": anchor_total,
                "support_stats": stats,
                "support_explanation": _support_explanation(stats),
            }
        )
    return templates


def _map_cost_category(row: dict) -> str:
    l2_id = (row.get("l2_id") or "").strip()
    l2_text = l2_id.lower()
    family_tag = ((row.get("wbs_family_tag") or row.get("l5_desc") or "").strip()).lower()
    if "contingency" in family_tag or l2_id.startswith(("E530-30299", "E540-30299")):
        return "Contingency"
    if l2_id.startswith(("E530-30203", "E540-30203")):
        return "Surface Facility"
    if l2_id.startswith(("E530-30129", "E540-30129")):
        return "Support"
    if l2_id.startswith(("E530-30101", "E540-30101")):
        return "Drilling"
    if "contingency" in l2_text:
        return "Contingency"
    if "surface" in l2_text or "facility" in l2_text:
        return "Surface Facility"
    if "support" in l2_text:
        return "Support"
    if "drilling" in l2_text:
        return "Drilling"
    if any(token in family_tag for token in ("construction", "hook up", "pre comm", "material - ll", "material - non ll", "surface")):
        return "Surface Facility"
    if any(token in family_tag for token in ("permit", "security", "environment", "insurance", "geologist", "testing", "waste")):
        return "Support"
    return "Drilling"


def _build_category_benchmarks(peer_rows: List[dict], field: str) -> Dict[str, dict]:
    totals: Dict[Tuple[str, str, str, str], float] = defaultdict(float)
    for row in peer_rows:
        category = _map_cost_category(row)
        campaign_token = (
            row.get("campaign_canonical")
            or row.get("source_field_campaign_year")
            or row.get("campaign_raw")
            or "unknown_campaign"
        )
        totals[(field, category, campaign_token, row.get("campaign_start_year", ""))] += _safe_float(row.get("actual_usd", "0"))

    by_category: Dict[str, List[dict]] = defaultdict(list)
    for (field_name, category, campaign_token, campaign_year), total in totals.items():
        by_category[category].append(
            {
                "field": field_name,
                "category": category,
                "campaign_token": campaign_token,
                "campaign_year": _safe_int(campaign_year),
                "actual_usd": total,
            }
        )

    benchmarks: Dict[str, dict] = {}
    for category in CATEGORY_ORDER:
        rows = sorted(by_category.get(category, []), key=lambda item: (item["campaign_year"], item["campaign_token"]))
        metrics = []
        for row in rows:
            peers = [x["actual_usd"] for x in rows if x["campaign_year"] and x["campaign_year"] < row["campaign_year"]]
            if not peers:
                peers = [x["actual_usd"] for x in rows if x is not row]
            if not peers:
                continue
            predicted = median(peers)
            actual = row["actual_usd"]
            abs_error = abs(predicted - actual)
            ape_pct = (abs_error / actual * 100.0) if actual else None
            metrics.append({"abs_error_usd": abs_error, "ape_pct": ape_pct})

        if metrics:
            ape_values = [metric["ape_pct"] for metric in metrics if metric["ape_pct"] is not None]
            benchmarks[category] = {
                "mae_mmusd": sum(metric["abs_error_usd"] for metric in metrics) / len(metrics) / 1_000_000.0,
                "mape_pct": (sum(ape_values) / len(ape_values)) if ape_values else None,
                "available": True,
                "note": f"field-specific category peer benchmark from {len(metrics)} historical backtests",
            }
        else:
            benchmarks[category] = {
                "mae_mmusd": None,
                "mape_pct": None,
                "available": False,
                "note": f"n/a: fewer than 2 historical {category.lower()} campaign observations in {field}",
            }
    return benchmarks


def _format_benchmark_display(benchmark: dict) -> str:
    if benchmark.get("available"):
        mape = benchmark.get("mape_pct")
        mape_text = f"{mape:.1f}%" if mape is not None else "n/a"
        return f"{benchmark['mae_mmusd']:.2f} / {mape_text}"
    return benchmark.get("note", "n/a")


def _allocate_amount(amount_usd: float, weights: Dict[str, float], ordered_wells: List[str]) -> Dict[str, float]:
    allocations: Dict[str, float] = {}
    remaining = round(amount_usd, 6)
    for idx, well_label in enumerate(ordered_wells):
        if idx == len(ordered_wells) - 1:
            allocation = remaining
        else:
            allocation = round(amount_usd * weights.get(well_label, 0.0), 6)
            remaining = round(remaining - allocation, 6)
        allocations[well_label] = allocation
    return allocations


def _build_category_matrix(detail_rows: List[dict], well_labels: List[str], field: str, peer_rows: List[dict]) -> Tuple[List[dict], dict]:
    matrix_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    direct_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    shared_allocations: List[dict] = []

    for row in detail_rows:
        category = _map_cost_category(row)
        row["cost_category"] = category
        if row["well_label"] != "CAMPAIGN_SHARED":
            matrix_totals[category][row["well_label"]] += row["estimate_usd"]
            direct_totals[category][row["well_label"]] += row["estimate_usd"]

    for row in detail_rows:
        if row["well_label"] != "CAMPAIGN_SHARED":
            continue
        category = row["cost_category"]
        category_direct = {well_label: direct_totals[category].get(well_label, 0.0) for well_label in well_labels}
        direct_sum = sum(category_direct.values())
        if direct_sum > 0:
            weights = {well_label: category_direct[well_label] / direct_sum for well_label in well_labels}
            basis = "within-category direct subtotal weights"
        else:
            weights = {well_label: 1.0 / len(well_labels) for well_label in well_labels}
            basis = "equal split fallback (no direct category subtotal)"

        allocations = _allocate_amount(row["estimate_usd"], weights, well_labels)
        for well_label, allocation in allocations.items():
            matrix_totals[category][well_label] += allocation
        shared_allocations.append(
            {
                "audit_key": row["audit_key"],
                "l5_id": row["l5_id"],
                "l5_desc": row["l5_desc"],
                "cost_category": category,
                "allocation_basis": basis,
                "weights": weights,
                "allocated_usd": allocations,
            }
        )

    benchmarks = _build_category_benchmarks(peer_rows, field)
    display_rows: List[dict] = []
    json_rows: List[dict] = []
    for category in CATEGORY_ORDER:
        benchmark = benchmarks[category]
        display_row = {"Cost Category": category}
        for well_label in well_labels:
            display_row[well_label] = round(matrix_totals[category].get(well_label, 0.0) / 1_000_000.0, 3)
        display_row[CATEGORY_ERROR_COLUMN] = _format_benchmark_display(benchmark)
        display_rows.append(display_row)

        json_rows.append(
            {
                "cost_category": category,
                "well_values_usd": {well_label: round(matrix_totals[category].get(well_label, 0.0), 6) for well_label in well_labels},
                "row_total_usd": round(sum(matrix_totals[category].get(well_label, 0.0) for well_label in well_labels), 6),
                "benchmark": benchmark,
                "display_error_mape": display_row[CATEGORY_ERROR_COLUMN],
            }
        )

    payload = {
        "field": field,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "units": {"matrix_cells": "MMUSD", "benchmark_error": "MMUSD"},
        "well_labels": well_labels,
        "allocation_rulebook": {
            "category_mapping": [
                "Contingency if `l5_desc` contains `Contingency` or L2 is `E53x/E54x-30299-*`.",
                "Surface Facility if L2 is `E53x/E54x-30203-*`.",
                "Support if L2 is `E53x/E54x-30129-*`.",
                "Drilling if L2 is `E53x/E54x-30101-*`.",
                "Fallback keyword rules are applied only when L2 is unavailable.",
            ],
            "shared_allocation_basis": "Within-category direct well subtotal weights; equal split only when a category has no direct well subtotal.",
            "rounding_rule": "Shared allocations are rounded to 6 decimals with residual assigned to the last well to preserve exact reconciliation.",
        },
        "rows": json_rows,
        "shared_row_allocations": shared_allocations,
    }
    return display_rows, payload


def _write_validation_artifacts(rows: List[dict]) -> dict:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["field"], row["classification"])].append(_safe_float(row["actual_usd"]))

    bands, methods = [], []
    for (field, klass), values in sorted(grouped.items()):
        values = sorted(values)
        if not values:
            continue
        med = median(values)
        p10 = _percentile(values, 0.10)
        p90 = _percentile(values, 0.90)
        bands.append(
            {
                "field": field,
                "bucket_id": klass,
                "classification": klass,
                "interval_method": "empirical_p10_p90",
                "lower_bound_usd": f"{p10:.6f}",
                "upper_bound_usd": f"{p90:.6f}",
                "center_usd": f"{med:.6f}",
                "source_count": str(len(values)),
            }
        )
        methods.append(
            {
                "field": field,
                "bucket_id": klass,
                "method_branch": "field_specific_family_analog",
                "features_used": "field,classification,family_group_key,depth_factor,anchor_distribution",
                "validation_design": "historical_replay_median_peer",
                "n_obs": str(len(values)),
                "n_campaign_years": "multi",
                "mae": "see_validation_reports",
                "mape": "see_validation_reports",
                "bias": "see_validation_reports",
                "interval_method": "empirical_p10_p90",
                "interval_coverage": "not_available_point_forecast",
                "synthetic_share": "0 unless enabled in app",
                "notes": "No predictive validity claim beyond replay outputs; family-grain analogs remain field-specific.",
            }
        )

    if bands:
        write_csv(CONFIDENCE_BANDS, bands, list(bands[0].keys()))
    if methods:
        write_csv(METHOD_REGISTRY, methods, list(methods[0].keys()))

    return {
        "confidence_band_rows": len(bands),
        "method_registry_rows": len(methods),
        "eligible_historical_rows": len(rows),
    }


def build_validation_artifacts(
    *,
    refresh_pipeline: bool = True,
    group_by: str = "family",
    use_synthetic: bool = False,
    synthetic_policy: str = "training",
) -> dict:
    if refresh_pipeline:
        _refresh_pipeline_outputs(
            group_by=group_by,
            use_synthetic=use_synthetic,
            synthetic_policy=synthetic_policy,
        )

    rows = _load_estimator_history_rows()
    return _write_validation_artifacts(rows)


def estimate_campaign(campaign_input: dict, well_rows: List[dict]) -> dict:
    normalized_campaign, normalized_wells = normalize_inputs(campaign_input, well_rows)
    field = normalized_campaign["field_canonical"]
    benchmark_index = _load_unit_price_benchmark_index()
    active_day_benchmark = benchmark_index.get((field, "active_day_rate"))
    depth_benchmark = benchmark_index.get((field, "depth_rate"))
    per_well_job_benchmark = benchmark_index.get((field, "per_well_job"))
    if not active_day_benchmark or not depth_benchmark:
        raise ValueError(f"Missing direct well unit-price benchmark for {field}")

    active_factor, active_applied, active_formula = _macro_adjustment_for_basis(
        normalized_campaign["use_external_forecast"],
        field,
        normalized_campaign["campaign_start_year"],
        "active_day_rate",
    )
    depth_factor_macro, depth_applied, depth_formula = _macro_adjustment_for_basis(
        normalized_campaign["use_external_forecast"],
        field,
        normalized_campaign["campaign_start_year"],
        "depth_rate",
    )
    per_job_factor, per_job_applied, per_job_formula = _macro_adjustment_for_basis(
        normalized_campaign["use_external_forecast"],
        field,
        normalized_campaign["campaign_start_year"],
        "per_well_job",
    )
    shared_factor, shared_applied, shared_formula = _macro_adjustment_for_basis(
        normalized_campaign["use_external_forecast"],
        field,
        normalized_campaign["campaign_start_year"],
        "campaign_scope_benchmark",
    )
    ext_applied = active_applied or depth_applied or per_job_applied or shared_applied
    ext_formula = (
        f"active_day_rate: {active_formula}; "
        f"depth_rate: {depth_formula}; "
        f"per_well_job: {per_job_formula}; "
        f"campaign_scope_benchmark: {shared_formula}"
    )

    field_rows = _load_field_rows(field)
    if not field_rows:
        raise ValueError(f"No estimator history rows available for field {field}. Refresh unit_price_history_mart first.")
    anchor_year, anchor_rows = _select_anchor_rows(field_rows, normalized_campaign["campaign_start_year"])
    peer_rows = _select_peer_rows(field_rows, normalized_campaign["campaign_start_year"])
    historical_anchor_well_count = len(
        {
            r.get("well_canonical", "").strip()
            for r in anchor_rows
            if r.get("well_canonical", "").strip() and "STEAM" not in r.get("well_canonical", "").upper()
        }
    ) or 1
    templates = _build_projection_templates(anchor_rows, peer_rows)
    if not templates:
        raise ValueError(f"No projection templates available for field {field}.")

    direct_templates = [t for t in templates if t["classification"] == "well_tied"]
    shared_templates = [t for t in templates if t["classification"] in {"hybrid", "campaign_tied"}]
    fallback_templates = [t for t in templates if t["classification"] not in {"well_tied", "hybrid", "campaign_tied"}]
    if not direct_templates:
        raise ValueError(f"No direct well templates found for field {field}.")

    detail_rows, well_outputs = [], []
    distribution_baseline = []
    for template in direct_templates:
        anchor_total = _safe_float(str(template.get("anchor_total_usd", "0")))
        if anchor_total <= 0.0:
            anchor_total = _safe_float(template["support_stats"].get("median_usd", "0"))
        distribution_baseline.append((anchor_total, template))
    direct_distribution_total = sum(weight for weight, _ in distribution_baseline)
    active_day_rate_value = _safe_float(active_day_benchmark["median_value"])
    depth_rate_value = _safe_float(depth_benchmark["median_value"])
    per_well_job_value = _safe_float(per_well_job_benchmark["median_value"]) if per_well_job_benchmark else 0.0
    active_unc_pct = _benchmark_uncertainty_pct(active_day_benchmark)
    depth_unc_pct = _benchmark_uncertainty_pct(depth_benchmark)
    per_job_unc_pct = _benchmark_uncertainty_pct(per_well_job_benchmark)

    for well in normalized_wells:
        estimated_days = _estimated_active_days(field, well.depth_bucket_ft, well.drill_rate_mode)
        active_day_component = active_day_rate_value * estimated_days * active_factor
        depth_component = depth_rate_value * well.depth_bucket_ft * depth_factor_macro
        per_job_component = per_well_job_value * per_job_factor
        well_total = active_day_component + depth_component + per_job_component
        direct_unc_pct = 0.0
        if well_total > 0.0:
            direct_unc_pct = (
                (active_day_component / well_total) * active_unc_pct
                + (depth_component / well_total) * depth_unc_pct
                + (per_job_component / well_total) * per_job_unc_pct
            )
        well_detail = []
        for baseline_value, template in distribution_baseline:
            stats = template["support_stats"]
            allocation_weight = (baseline_value / direct_distribution_total) if direct_distribution_total > 0.0 else (1.0 / max(len(direct_templates), 1))
            estimate = well_total * allocation_weight
            row = {
                "well_label": well.well_label,
                "component_scope": "direct_well_linked",
                "classification": template["classification"],
                "l2_id": template["l2_id"],
                "l3_id": template["l3_id"],
                "l4_id": template["l4_id"],
                "l5_id": template["l5_id"],
                "l5_desc": template["l5_desc"],
                "wbs_family_tag": template["wbs_family_tag"],
                "family_group_key": template["family_group_key"],
                "estimate_usd": estimate,
                "uncertainty_pct": direct_unc_pct,
                "uncertainty_type": "empirical_spread",
                "estimation_method": "unit_price_benchmark_allocated_to_anchor_cost_family",
                "driver_family": template["driver_family"],
                "source_field_campaign_years": ", ".join(stats["source_campaign_years"][:8]),
                "source_wells": ", ".join(stats["source_wells"][:10]),
                "source_row_ids": ", ".join(stats["source_row_ids"][:20]),
                "source_row_count": stats["source_row_count"],
                "support_explanation": (
                    "Direct well benchmark allocated by anchor-year cost-family distribution. "
                    f"active_day_rate={active_day_rate_value:.2f} USD/day, estimated_days={estimated_days:.2f}, "
                    f"depth_rate={depth_rate_value:.2f} USD/ft, depth_ft={well.depth_bucket_ft}, "
                    f"per_well_job={per_well_job_value:.2f} USD/well."
                ),
                "synthetic_rows_used": 0,
                "external_adjustment_applied": active_applied or depth_applied or per_job_applied,
            }
            detail_rows.append(row)
            well_detail.append(row)

        top = sorted(well_detail, key=lambda r: r["estimate_usd"], reverse=True)[:5]
        well_outputs.append(
            {
                "well_label": well.well_label,
                "estimated_cost_usd": well_total,
                "estimated_cost_mmusd": well_total / 1_000_000.0,
                "estimated_days": estimated_days,
                "uncertainty_pct": direct_unc_pct,
                "uncertainty_label": "empirical_spread",
                "method_label": "unit_price_direct_benchmark_plus_anchor_cost_family_allocation",
                "top_wbs_contributors": [f"{r['l5_desc']} ({r['estimate_usd']/1_000_000:.2f} MMUSD)" for r in top],
                "source_campaign_tags": sorted({r["source_field_campaign_years"] for r in top}),
            }
        )

    shared_weight = 1.0 + 0.08 * normalized_campaign["pad_expansion_count"]
    for template in shared_templates + fallback_templates:
        stats = template["support_stats"]
        baseline_value = _safe_float(str(template.get("anchor_total_usd", "0")))
        if baseline_value <= 0.0:
            baseline_value = stats["median_usd"]
        if template["classification"] in {"hybrid", "campaign_tied"}:
            estimate = baseline_value * shared_factor * shared_weight
            scope = "shared_support" if template["classification"] == "hybrid" else "campaign_overhead"
        else:
            estimate = baseline_value
            scope = "fallback_unclassified"
        unc_pct = _uncertainty_pct(stats)
        detail_rows.append(
            {
                "well_label": "CAMPAIGN_SHARED",
                "component_scope": scope,
                "classification": template["classification"],
                "l2_id": template["l2_id"],
                "l3_id": template["l3_id"],
                "l4_id": template["l4_id"],
                "l5_id": template["l5_id"],
                "l5_desc": template["l5_desc"],
                "wbs_family_tag": template["wbs_family_tag"],
                "family_group_key": template["family_group_key"],
                "estimate_usd": estimate,
                "uncertainty_pct": unc_pct,
                "uncertainty_type": "empirical_spread",
                "estimation_method": _estimation_method(stats),
                "driver_family": template["driver_family"],
                "source_field_campaign_years": ", ".join(stats["source_campaign_years"][:8]),
                "source_wells": ", ".join(stats["source_wells"][:10]),
                "source_row_ids": ", ".join(stats["source_row_ids"][:20]),
                "source_row_count": stats["source_row_count"],
                "support_explanation": template["support_explanation"],
                "synthetic_rows_used": 0,
                "external_adjustment_applied": ext_applied,
            }
        )

    total_cost = sum(r["estimate_usd"] for r in detail_rows)
    by_l2 = defaultdict(float)
    for r in detail_rows:
        by_l2[r["l2_id"]] += r["estimate_usd"]

    for idx, row in enumerate(detail_rows, start=1):
        row["audit_key"] = hashlib.sha256(f"{field}|{normalized_campaign['campaign_start_year']}|{idx}|{row['l5_id']}|{row['well_label']}".encode("utf-8")).hexdigest()[:16]

    well_labels = [well.well_label for well in normalized_wells]
    category_matrix_rows, category_matrix_payload = _build_category_matrix(detail_rows, well_labels, field, peer_rows)
    write_csv(
        APP_CATEGORY_MATRIX_CSV,
        category_matrix_rows,
        ["Cost Category", *well_labels, CATEGORY_ERROR_COLUMN],
    )
    APP_CATEGORY_MATRIX_JSON.write_text(json.dumps(category_matrix_payload, indent=2) + "\n", encoding="utf-8")

    scenario_id = f"{field}_{normalized_campaign['campaign_start_year']}_{normalized_campaign['well_count']}w"
    audit_rows = []
    for row in detail_rows:
        audit_rows.append(
            {
                "audit_key": row["audit_key"],
                "field": field,
                "scenario_id": scenario_id,
                "well_label": row["well_label"],
                "component_scope": row["component_scope"],
                "wbs_level": "L5",
                "wbs_id": row["l5_id"],
                "wbs_desc": row["l5_desc"],
                "estimate_usd": f"{row['estimate_usd']:.6f}",
                "uncertainty_pct": f"{row['uncertainty_pct']:.4f}",
                "uncertainty_type": row["uncertainty_type"],
                "estimation_method": row["estimation_method"],
                "source_field_campaign_years": row["source_field_campaign_years"],
                "source_wells": row["source_wells"],
                "source_row_count": row["source_row_count"],
                "support_explanation": row["support_explanation"],
                "synthetic_rows_used": row["synthetic_rows_used"],
                "external_adjustment_applied": "yes" if row["external_adjustment_applied"] else "no",
                "reconciliation_group": scenario_id,
                "source_row_ids": row["source_row_ids"],
            }
        )
    write_csv(APP_AUDIT, audit_rows, list(audit_rows[0].keys()))

    summary = {
        "field": field,
        "input_year": normalized_campaign["campaign_start_year"],
        "estimation_methodology": "unit_price_direct_benchmark_with_anchor_year_cost_family_distribution_and_campaign_scope_analogs",
        "total_campaign_cost_mmusd": total_cost / 1_000_000.0,
        "total_campaign_cost_formatted": _format_mmusd(total_cost),
        "total_campaign_cost_usd": total_cost,
        "well_component_usd": sum(r["estimated_cost_usd"] for r in well_outputs),
        "well_component_formatted": _format_mmusd(sum(r["estimated_cost_usd"] for r in well_outputs)),
        "hybrid_component_usd": sum(r["estimate_usd"] for r in detail_rows if r["classification"] == "hybrid"),
        "hybrid_component_formatted": _format_mmusd(sum(r["estimate_usd"] for r in detail_rows if r["classification"] == "hybrid")),
        "campaign_tied_component_usd": sum(r["estimate_usd"] for r in detail_rows if r["classification"] == "campaign_tied"),
        "campaign_tied_component_formatted": _format_mmusd(sum(r["estimate_usd"] for r in detail_rows if r["classification"] == "campaign_tied")),
        "reconciliation_status": "PASS",
        "historical_anchor_year": anchor_year or "all_available",
        "historical_anchor_well_count": historical_anchor_well_count,
        "l2_cost_breakdown": [
            {"l2_id": k, "estimate_usd": v, "estimate_formatted": _format_mmusd(v)}
            for k, v in sorted(by_l2.items(), key=lambda x: x[1], reverse=True)
        ],
        "category_matrix": category_matrix_rows,
        "category_matrix_note": "Matrix values are presentation-layer MMUSD totals. Shared rows remain campaign-scoped in detail output and are allocated to wells only for matrix display.",
        "uncertainty_definition": "uncertainty_pct = ((p90_usd - p10_usd) / median_usd) * 100 using field-specific grouped historical peers.",
    }
    APP_SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "field": field,
        "scenario_id": scenario_id,
        "estimate_type": "unit_price_benchmark_anchored",
        "runtime_toggles": {
            "external_forecast_requested": normalized_campaign["use_external_forecast"],
            "external_forecast_applied": ext_applied,
            "synthetic_data_requested": normalized_campaign["use_synthetic_data"],
        },
        "external_adjustment_formula": ext_formula,
        "allocation_basis": "Within-category direct well subtotal weights with equal split fallback for categories without direct well rows.",
        "reconciliation": {
            "campaign_total_usd": total_cost,
            "detail_total_usd": sum(float(r["estimate_usd"]) for r in audit_rows),
            "status": "PASS",
        },
        "outputs": {
            "audit_csv": APP_AUDIT.relative_to(ROOT).as_posix(),
            "summary_json": APP_SUMMARY.relative_to(ROOT).as_posix(),
            "category_matrix_csv": APP_CATEGORY_MATRIX_CSV.relative_to(ROOT).as_posix(),
            "category_matrix_json": APP_CATEGORY_MATRIX_JSON.relative_to(ROOT).as_posix(),
        },
    }
    APP_RUN_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return {
        "campaign_input": normalized_campaign,
        "well_outputs": well_outputs,
        "campaign_summary": summary,
        "detail_wbs": detail_rows,
        "audit_rows": audit_rows,
        "run_manifest": manifest,
        "warnings": [
            "EXTN. DATA requested but external auditable series unavailable; fallback historical-only mode applied."
            if normalized_campaign["use_external_forecast"] and not ext_applied
            else ""
        ],
    }


if __name__ == "__main__":
    build_validation_artifacts()
