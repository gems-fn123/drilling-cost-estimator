#!/usr/bin/env python3
"""Build yearly macro factor and Pearson weighting artifacts for unit-price forecasts."""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean
from typing import Dict, List, Tuple

from src.config import PROCESSED, REFERENCE_DIR, REPORTS, ROOT
from src.modeling.unit_price_history_pipeline import UNIT_PRICE_HISTORY_MART
from src.utils import format_float, normalize_exclusion_well, parse_float, pearson, read_csv, write_csv

log = logging.getLogger(__name__)

MACRO_REFERENCE_PATH = REFERENCE_DIR / "macro_series_2019_2026.csv"
MACRO_FACTORS_PATH = PROCESSED / "unit_price_macro_factors.csv"
MACRO_WEIGHTS_PATH = PROCESSED / "unit_price_macro_weights.csv"
MACRO_CLUSTER_WEIGHTS_PATH = PROCESSED / "unit_price_macro_cluster_weights.csv"
MACRO_REPORT_PATH = REPORTS / "unit_price_macro_correlation.md"
WELL_POOL_EXCLUSIONS = PROCESSED / "well_pool_exclusions.csv"

YEAR_START = 2019
YEAR_END = 2026
MIN_OPERATIONAL_YEARS = 4
ALL_FIELDS = "ALL_FIELDS"
CLUSTER_SCOPE_TYPE = "pooled_wbs_cluster"
CLUSTER_BALANCE_METHOD = "equal_field_mean"
CLUSTER_MIN_FIELD_COUNT = 2
CLUSTER_MIN_OPERATIONAL_YEARS = 4

WEIGHT_ELIGIBLE_FACTORS = (
    "brent_usd_bbl",
    "indonesia_cpi_index",
    "steel_commodity_proxy_usd_ton",
)
ALL_FACTORS = WEIGHT_ELIGIBLE_FACTORS + ("indonesia_inflation_pct",)
FACTOR_LABELS = {
    "brent_usd_bbl": "Brent oil price",
    "indonesia_cpi_index": "Indonesia CPI index",
    "indonesia_inflation_pct": "Indonesia inflation rate",
    "steel_commodity_proxy_usd_ton": "Steel proxy commodity price",
}
STEEL_PROXY_NOTE = (
    "Annual direct steel-HRC series was not available in the official annual IMF/WB datasets used here, "
    "so the analysis uses IMF `PIORECR` iron ore as the auditable steel-input proxy."
)


def markdown_table_cell(value: str) -> str:
    return str(value).replace("|", r"\|")


def normalize_wbs_cluster_component(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _cluster_level4_description(level_4: str, level_5: str = "") -> str:
    label = normalize_wbs_cluster_component(level_4)
    if label:
        return label
    return normalize_wbs_cluster_component(level_5)


def _build_fuzzy_l4_cluster_map(history_rows: List[dict], *, threshold: float = 0.86) -> dict[str, str]:
    unique_labels = {
        _cluster_level4_description(row.get("level_4", ""), row.get("level_5", ""))
        for row in history_rows
    }
    canonical_labels: List[str] = []
    cluster_map: dict[str, str] = {}

    for label in sorted((item for item in unique_labels if item), key=lambda item: (-len(item), item)):
        best_label = ""
        best_score = 0.0
        for canonical_label in canonical_labels:
            score = SequenceMatcher(None, label, canonical_label).ratio()
            if score > best_score:
                best_score = score
                best_label = canonical_label

        if best_label and best_score >= threshold:
            cluster_map[label] = best_label
        else:
            canonical_labels.append(label)
            cluster_map[label] = label

    return cluster_map


def build_wbs_cluster_key(level_4: str, level_5: str, cluster_map: dict[str, str] | None = None) -> str:
    label = _cluster_level4_description(level_4, level_5)
    if not label:
        return ""
    if cluster_map:
        return cluster_map.get(label, label)
    return label


def ensure_history_mart() -> None:
    if UNIT_PRICE_HISTORY_MART.exists():
        return
    subprocess.run([sys.executable, "src/modeling/unit_price_history_pipeline.py"], cwd=ROOT, check=True)


def load_active_exclusions() -> set[tuple[str, str]]:
    if not WELL_POOL_EXCLUSIONS.exists():
        return set()
    return {
        (row["field"], normalize_exclusion_well(row["well_canonical"]))
        for row in read_csv(WELL_POOL_EXCLUSIONS)
        if row.get("status", "").strip().lower() == "active"
    }


def aggregate_yearly_unit_prices(history_rows: List[dict]) -> dict[Tuple[str, str, str, int], dict]:
    active_exclusions = load_active_exclusions()
    unit_buckets: dict[Tuple[str, ...], dict] = {}

    for row in history_rows:
        year = int(row.get("campaign_year") or 0)
        if year < YEAR_START or year > YEAR_END:
            continue

        pricing_basis = row.get("pricing_basis", "")
        field = row.get("field", "")
        campaign = row.get("campaign_canonical", "")
        cost = parse_float(row.get("actual_cost_usd", "0"))

        if pricing_basis == "campaign_scope_benchmark":
            quantity = 1.0
            unit_key: Tuple[str, ...] = (field, campaign, pricing_basis)
        else:
            well = row.get("well_canonical", "")
            if not well:
                continue
            if (field, normalize_exclusion_well(well)) in active_exclusions:
                continue
            if pricing_basis == "active_day_rate":
                quantity = parse_float(row.get("active_operational_days", "0"))
            elif pricing_basis == "depth_rate":
                quantity = parse_float(row.get("actual_depth_ft", "0"))
            elif pricing_basis == "per_well_job":
                quantity = 1.0
            else:
                continue
            unit_key = (field, campaign, pricing_basis, well)

        if quantity <= 0.0:
            continue

        unit_bucket = unit_buckets.setdefault(
            unit_key,
            {
                "field": field,
                "campaign": campaign,
                "pricing_basis": pricing_basis,
                "year": year,
                "total_cost_usd": 0.0,
                "quantity": quantity,
                "source_row_count": 0,
            },
        )
        unit_bucket["total_cost_usd"] += cost
        unit_bucket["quantity"] = quantity
        unit_bucket["source_row_count"] += 1

    buckets: dict[Tuple[str, str, str, int], dict] = {}
    for unit_bucket in unit_buckets.values():
        for scope_type, scope_field in (
            ("pooled_pricing_basis", ALL_FIELDS),
            ("field_pricing_basis", unit_bucket["field"]),
        ):
            key = (scope_type, scope_field, unit_bucket["pricing_basis"], unit_bucket["year"])
            bucket = buckets.setdefault(
                key,
                {
                    "annual_cost_usd": 0.0,
                    "annual_quantity": 0.0,
                    "campaigns": set(),
                    "unit_observation_count": 0,
                    "source_row_count": 0,
                },
            )
            bucket["annual_cost_usd"] += unit_bucket["total_cost_usd"]
            bucket["annual_quantity"] += unit_bucket["quantity"]
            bucket["campaigns"].add(unit_bucket["campaign"])
            bucket["unit_observation_count"] += 1
            bucket["source_row_count"] += unit_bucket["source_row_count"]

    return buckets


def aggregate_yearly_wbs_cluster_prices(history_rows: List[dict]) -> dict[Tuple[str, str, str, str, int], dict]:
    active_exclusions = load_active_exclusions()
    cluster_map = _build_fuzzy_l4_cluster_map(history_rows)
    field_buckets: dict[Tuple[str, str, str, int], dict] = {}

    for row in history_rows:
        year = int(row.get("campaign_year") or 0)
        if year < YEAR_START or year > YEAR_END:
            continue

        pricing_basis = row.get("pricing_basis", "")
        field = row.get("field", "")
        cluster_key = build_wbs_cluster_key(row.get("level_4", ""), row.get("level_5", ""), cluster_map=cluster_map)
        if not cluster_key:
            continue

        cost = parse_float(row.get("actual_cost_usd", "0"))

        if pricing_basis == "campaign_scope_benchmark":
            quantity = 1.0
        else:
            well = row.get("well_canonical", "")
            if not well:
                continue
            if (field, normalize_exclusion_well(well)) in active_exclusions:
                continue
            if pricing_basis == "active_day_rate":
                quantity = parse_float(row.get("active_operational_days", "0"))
            elif pricing_basis == "depth_rate":
                quantity = parse_float(row.get("actual_depth_ft", "0"))
            elif pricing_basis == "per_well_job":
                quantity = 1.0
            else:
                continue

        if quantity <= 0.0:
            continue

        field_key = (field, cluster_key, pricing_basis, year)
        field_bucket = field_buckets.setdefault(
            field_key,
            {
                "field": field,
                "cluster": cluster_key,
                "pricing_basis": pricing_basis,
                "year": year,
                "total_cost_usd": 0.0,
                "quantity": 0.0,
                "campaigns": set(),
                "source_row_count": 0,
            },
        )
        field_bucket["total_cost_usd"] += cost
        field_bucket["quantity"] += quantity
        field_bucket["campaigns"].add(row.get("campaign_canonical", ""))
        field_bucket["source_row_count"] += 1

    buckets: dict[Tuple[str, str, str, str, int], dict] = {}
    for field_bucket in field_buckets.values():
        bucket_key = (CLUSTER_SCOPE_TYPE, ALL_FIELDS, field_bucket["cluster"], field_bucket["pricing_basis"], field_bucket["year"])
        bucket = buckets.setdefault(
            bucket_key,
            {
                "field_count_set": set(),
                "field_unit_prices": [],
                "pooled_cost_usd": 0.0,
                "pooled_quantity": 0.0,
                "campaigns": set(),
                "field_bucket_count": 0,
                "source_row_count": 0,
            },
        )
        field_unit_price = field_bucket["total_cost_usd"] / field_bucket["quantity"]
        bucket["field_count_set"].add(field_bucket["field"])
        bucket["field_unit_prices"].append(field_unit_price)
        bucket["pooled_cost_usd"] += field_bucket["total_cost_usd"]
        bucket["pooled_quantity"] += field_bucket["quantity"]
        bucket["campaigns"].update(c for c in field_bucket["campaigns"] if c)
        bucket["field_bucket_count"] += 1
        bucket["source_row_count"] += field_bucket["source_row_count"]

    return buckets


def build_factor_rows(history_rows: List[dict], macro_rows: List[dict]) -> List[dict]:
    buckets = aggregate_yearly_unit_prices(history_rows)
    scope_keys = sorted({key[:3] for key in buckets})

    rows: List[dict] = []
    for scope_type, field, pricing_basis in scope_keys:
        for macro in macro_rows:
            year = int(macro["year"])
            bucket = buckets.get((scope_type, field, pricing_basis, year))
            discount_factor = parse_float(macro["cpi_discount_factor_to_2026"])

            annual_unit_price = ""
            unit_price_real = ""
            annual_cost = ""
            annual_quantity = ""
            campaign_count = "0"
            unit_count = "0"
            source_row_count = "0"
            has_history = "no"

            if bucket and bucket["annual_quantity"] > 0.0:
                annual_cost = f"{bucket['annual_cost_usd']:.6f}"
                annual_quantity = f"{bucket['annual_quantity']:.6f}"
                annual_unit_price_value = bucket["annual_cost_usd"] / bucket["annual_quantity"]
                annual_unit_price = f"{annual_unit_price_value:.6f}"
                unit_price_real = f"{annual_unit_price_value * discount_factor:.6f}"
                campaign_count = str(len(bucket["campaigns"]))
                unit_count = str(bucket["unit_observation_count"])
                source_row_count = str(bucket["source_row_count"])
                has_history = "yes"

            rows.append(
                {
                    "scope_type": scope_type,
                    "field": field,
                    "pricing_basis": pricing_basis,
                    "year": macro["year"],
                    "has_unit_price_history": has_history,
                    "campaign_observation_count": campaign_count,
                    "unit_observation_count": unit_count,
                    "source_row_count": source_row_count,
                    "annual_cost_usd": annual_cost,
                    "annual_quantity": annual_quantity,
                    "annual_unit_price_usd": annual_unit_price,
                    "unit_price_real_2026_usd": unit_price_real,
                    "brent_usd_bbl": macro["brent_usd_bbl"],
                    "indonesia_cpi_index": macro["indonesia_cpi_index"],
                    "indonesia_inflation_pct": macro["indonesia_inflation_pct"],
                    "steel_commodity_proxy_usd_ton": macro["steel_commodity_proxy_usd_ton"],
                    "steel_proxy_name": macro["steel_proxy_name"],
                    "cpi_discount_factor_to_2026": macro["cpi_discount_factor_to_2026"],
                    "brent_real_2026_usd_bbl": f"{parse_float(macro['brent_usd_bbl']) * discount_factor:.6f}",
                    "steel_commodity_proxy_real_2026_usd_ton": f"{parse_float(macro['steel_commodity_proxy_usd_ton']) * discount_factor:.6f}",
                    "source_note": macro["source_note"],
                    "source_url": macro["source_url"],
                }
            )

    return rows


def build_cluster_factor_rows(history_rows: List[dict], macro_rows: List[dict]) -> List[dict]:
    buckets = aggregate_yearly_wbs_cluster_prices(history_rows)
    scope_keys = sorted({key[:4] for key in buckets})

    rows: List[dict] = []
    for scope_type, field, cluster_key, pricing_basis in scope_keys:
        for macro in macro_rows:
            year = int(macro["year"])
            bucket = buckets.get((scope_type, field, cluster_key, pricing_basis, year))
            discount_factor = parse_float(macro["cpi_discount_factor_to_2026"])

            pooled_cost = ""
            pooled_quantity = ""
            pooled_unit_price = ""
            pooled_unit_price_real = ""
            field_balanced_unit_price = ""
            field_balanced_unit_price_real = ""
            field_count = "0"
            field_coverage_count = "0"
            field_coverage_fields = ""
            campaign_count = "0"
            unit_count = "0"
            source_row_count = "0"
            has_history = "no"

            if bucket and bucket["pooled_quantity"] > 0.0 and bucket["field_unit_prices"]:
                pooled_cost_value = bucket["pooled_cost_usd"]
                pooled_quantity_value = bucket["pooled_quantity"]
                pooled_unit_price_value = pooled_cost_value / pooled_quantity_value
                field_balanced_unit_price_value = mean(bucket["field_unit_prices"])

                pooled_cost = f"{pooled_cost_value:.6f}"
                pooled_quantity = f"{pooled_quantity_value:.6f}"
                pooled_unit_price = f"{pooled_unit_price_value:.6f}"
                pooled_unit_price_real = f"{pooled_unit_price_value * discount_factor:.6f}"
                field_balanced_unit_price = f"{field_balanced_unit_price_value:.6f}"
                field_balanced_unit_price_real = f"{field_balanced_unit_price_value * discount_factor:.6f}"
                field_count = str(len(bucket["field_count_set"]))
                field_coverage_count = field_count
                field_coverage_fields = ",".join(sorted(bucket["field_count_set"]))
                campaign_count = str(len(bucket["campaigns"]))
                unit_count = str(bucket["field_bucket_count"])
                source_row_count = str(bucket["source_row_count"])
                has_history = "yes"

            rows.append(
                {
                    "scope_type": scope_type,
                    "field": field,
                    "pricing_basis": pricing_basis,
                    "wbs_cluster": cluster_key,
                    "balance_method": CLUSTER_BALANCE_METHOD,
                    "year": macro["year"],
                    "has_unit_price_history": has_history,
                    "field_count": field_count,
                    "field_coverage_count": field_coverage_count,
                    "field_coverage_fields": field_coverage_fields,
                    "campaign_observation_count": campaign_count,
                    "unit_observation_count": unit_count,
                    "source_row_count": source_row_count,
                    "pooled_cost_usd": pooled_cost,
                    "pooled_quantity": pooled_quantity,
                    "pooled_unit_price_usd": pooled_unit_price,
                    "pooled_unit_price_real_2026_usd": pooled_unit_price_real,
                    "field_balanced_unit_price_usd": field_balanced_unit_price,
                    "field_balanced_unit_price_real_2026_usd": field_balanced_unit_price_real,
                    "brent_usd_bbl": macro["brent_usd_bbl"],
                    "indonesia_cpi_index": macro["indonesia_cpi_index"],
                    "indonesia_inflation_pct": macro["indonesia_inflation_pct"],
                    "steel_commodity_proxy_usd_ton": macro["steel_commodity_proxy_usd_ton"],
                    "steel_proxy_name": macro["steel_proxy_name"],
                    "cpi_discount_factor_to_2026": macro["cpi_discount_factor_to_2026"],
                    "brent_real_2026_usd_bbl": f"{parse_float(macro['brent_usd_bbl']) * discount_factor:.6f}",
                    "steel_commodity_proxy_real_2026_usd_ton": f"{parse_float(macro['steel_commodity_proxy_usd_ton']) * discount_factor:.6f}",
                    "source_note": macro["source_note"],
                    "source_url": macro["source_url"],
                }
            )

    return rows


def support_status(scope_type: str, overlap_year_count: int) -> str:
    if overlap_year_count < 3:
        return "insufficient_history"
    if scope_type == "pooled_pricing_basis" and overlap_year_count >= MIN_OPERATIONAL_YEARS:
        return "operational"
    return "diagnostic_only_thin_history"


def cluster_support_status(field_coverage_count: int, overlap_year_count: int) -> str:
    if overlap_year_count < 3:
        return "insufficient_history"
    if field_coverage_count < CLUSTER_MIN_FIELD_COUNT:
        return "diagnostic_only_thin_history"
    if overlap_year_count >= CLUSTER_MIN_OPERATIONAL_YEARS:
        return "operational"
    return "diagnostic_only_thin_history"


def direction_label(value: float | None) -> str:
    if value is None:
        return "not_available"
    if abs(value) < 0.05:
        return "flat"
    if value > 0:
        return "positive"
    return "negative"


def build_weight_rows(factor_rows: List[dict]) -> List[dict]:
    grouped: dict[Tuple[str, str, str], List[dict]] = defaultdict(list)
    for row in factor_rows:
        grouped[(row["scope_type"], row["field"], row["pricing_basis"])].append(row)

    out: List[dict] = []
    for key in sorted(grouped):
        scope_type, field, pricing_basis = key
        rows = sorted(grouped[key], key=lambda item: int(item["year"]))
        overlap = [row for row in rows if row["has_unit_price_history"] == "yes"]
        years = [row["year"] for row in overlap]
        year_count = len(years)
        status = support_status(scope_type, year_count)

        unit_price_nominal = [parse_float(row["annual_unit_price_usd"]) for row in overlap]
        unit_price_real = [parse_float(row["unit_price_real_2026_usd"]) for row in overlap]

        nominal_results: dict[str, float | None] = {}
        discounted_results: dict[str, float | None] = {}
        for factor_name in ALL_FACTORS:
            nominal_series = [parse_float(row[factor_name]) for row in overlap]
            nominal_results[factor_name] = pearson(unit_price_nominal, nominal_series)

            if factor_name == "brent_usd_bbl":
                discounted_series = [parse_float(row["brent_real_2026_usd_bbl"]) for row in overlap]
                discounted_results[factor_name] = pearson(unit_price_real, discounted_series)
            elif factor_name == "steel_commodity_proxy_usd_ton":
                discounted_series = [parse_float(row["steel_commodity_proxy_real_2026_usd_ton"]) for row in overlap]
                discounted_results[factor_name] = pearson(unit_price_real, discounted_series)
            else:
                discounted_results[factor_name] = None

        denom = 0.0
        if status == "operational":
            denom = sum(
                abs(nominal_results[factor_name] or 0.0)
                for factor_name in WEIGHT_ELIGIBLE_FACTORS
                if nominal_results[factor_name] is not None
            )

        for factor_name in ALL_FACTORS:
            nominal_value = nominal_results[factor_name]
            discounted_value = discounted_results[factor_name]
            weight_eligible = "yes" if factor_name in WEIGHT_ELIGIBLE_FACTORS else "no"
            weight_basis = "diagnostic_only"
            forecast_weight = 0.0

            if status == "operational" and weight_eligible == "yes" and denom > 0.0 and nominal_value is not None:
                forecast_weight = abs(nominal_value) / denom
                weight_basis = "nominal_abs_pearson"
            elif status != "operational":
                weight_basis = "not_used_thin_history"
            elif weight_eligible == "no":
                weight_basis = "diagnostic_factor_not_weighted"
            else:
                weight_basis = "not_used_missing_signal"

            out.append(
                {
                    "scope_type": scope_type,
                    "field": field,
                    "pricing_basis": pricing_basis,
                    "factor_name": factor_name,
                    "factor_display_name": FACTOR_LABELS[factor_name],
                    "weight_eligible": weight_eligible,
                    "observation_year_count": str(year_count),
                    "observation_years": ",".join(years),
                    "support_status": status,
                    "pearson_r_nominal": format_float(nominal_value),
                    "pearson_r_discounted_2026": format_float(discounted_value),
                    "direction": direction_label(nominal_value),
                    "abs_nominal_correlation": format_float(abs(nominal_value) if nominal_value is not None else None),
                    "forecast_weight": f"{forecast_weight:.6f}",
                    "weight_basis": weight_basis,
                    "steel_proxy_note": STEEL_PROXY_NOTE if factor_name == "steel_commodity_proxy_usd_ton" else "",
                }
            )

    return out


def build_cluster_weight_rows(factor_rows: List[dict]) -> List[dict]:
    grouped: dict[Tuple[str, str, str, str], List[dict]] = defaultdict(list)
    for row in factor_rows:
        grouped[(row["scope_type"], row["field"], row["pricing_basis"], row["wbs_cluster"])].append(row)

    out: List[dict] = []
    for key in sorted(grouped):
        scope_type, field, pricing_basis, wbs_cluster = key
        rows = sorted(grouped[key], key=lambda item: int(item["year"]))
        overlap = [row for row in rows if row["has_unit_price_history"] == "yes"]
        years = [row["year"] for row in overlap]
        year_count = len(years)
        field_counts = [int(row["field_count"]) for row in overlap if row["field_count"]]
        field_count_floor = min(field_counts) if field_counts else 0
        field_count_peak = max(field_counts) if field_counts else 0
        field_coverage = sorted({field for row in overlap for field in row.get("field_coverage_fields", "").split(",") if field})
        field_coverage_count = len(field_coverage)
        status = cluster_support_status(field_coverage_count, year_count)

        cluster_unit_price_nominal = [parse_float(row["field_balanced_unit_price_usd"]) for row in overlap]
        cluster_unit_price_real = [parse_float(row["field_balanced_unit_price_real_2026_usd"]) for row in overlap]

        nominal_results: dict[str, float | None] = {}
        discounted_results: dict[str, float | None] = {}
        for factor_name in ALL_FACTORS:
            nominal_series = [parse_float(row[factor_name]) for row in overlap]
            nominal_results[factor_name] = pearson(cluster_unit_price_nominal, nominal_series)

            if factor_name == "brent_usd_bbl":
                discounted_series = [parse_float(row["brent_real_2026_usd_bbl"]) for row in overlap]
                discounted_results[factor_name] = pearson(cluster_unit_price_real, discounted_series)
            elif factor_name == "steel_commodity_proxy_usd_ton":
                discounted_series = [parse_float(row["steel_commodity_proxy_real_2026_usd_ton"]) for row in overlap]
                discounted_results[factor_name] = pearson(cluster_unit_price_real, discounted_series)
            else:
                discounted_results[factor_name] = None

        denom = 0.0
        if status == "operational":
            denom = sum(
                abs(nominal_results[factor_name] or 0.0)
                for factor_name in WEIGHT_ELIGIBLE_FACTORS
                if nominal_results[factor_name] is not None
            )

        for factor_name in ALL_FACTORS:
            nominal_value = nominal_results[factor_name]
            discounted_value = discounted_results[factor_name]
            weight_eligible = "yes" if factor_name in WEIGHT_ELIGIBLE_FACTORS else "no"
            weight_basis = "diagnostic_only"
            forecast_weight = 0.0

            if status == "operational" and weight_eligible == "yes" and denom > 0.0 and nominal_value is not None:
                forecast_weight = abs(nominal_value) / denom
                weight_basis = "nominal_abs_pearson"
            elif status != "operational":
                weight_basis = "not_used_thin_history"
            elif weight_eligible == "no":
                weight_basis = "diagnostic_factor_not_weighted"
            else:
                weight_basis = "not_used_missing_signal"

            out.append(
                {
                    "scope_type": scope_type,
                    "field": field,
                    "pricing_basis": pricing_basis,
                    "wbs_cluster": wbs_cluster,
                    "balance_method": CLUSTER_BALANCE_METHOD,
                    "factor_name": factor_name,
                    "factor_display_name": FACTOR_LABELS[factor_name],
                    "weight_eligible": weight_eligible,
                    "observation_year_count": str(year_count),
                    "observation_years": ",".join(years),
                    "field_count_floor": str(field_count_floor),
                    "field_count_peak": str(field_count_peak),
                    "field_coverage_count": str(field_coverage_count),
                    "field_coverage_fields": ",".join(field_coverage),
                    "support_status": status,
                    "pearson_r_nominal": format_float(nominal_value),
                    "pearson_r_discounted_2026": format_float(discounted_value),
                    "direction": direction_label(nominal_value),
                    "abs_nominal_correlation": format_float(abs(nominal_value) if nominal_value is not None else None),
                    "forecast_weight": f"{forecast_weight:.6f}",
                    "weight_basis": weight_basis,
                    "steel_proxy_note": STEEL_PROXY_NOTE if factor_name == "steel_commodity_proxy_usd_ton" else "",
                }
            )

    return out


def write_report(macro_rows: List[dict], weight_rows: List[dict], cluster_weight_rows: List[dict]) -> None:
    operational_rows = [
        row
        for row in weight_rows
        if row["scope_type"] == "pooled_pricing_basis"
        and row["support_status"] == "operational"
        and row["weight_eligible"] == "yes"
    ]
    diagnostic_scope_rows = [
        row
        for row in weight_rows
        if row["factor_name"] == "brent_usd_bbl"
    ]
    cluster_summary_rows = []
    seen_clusters: set[Tuple[str, str]] = set()
    for row in cluster_weight_rows:
        if row["factor_name"] != "brent_usd_bbl":
            continue
        key = (row["pricing_basis"], row["wbs_cluster"])
        if key in seen_clusters:
            continue
        seen_clusters.add(key)
        cluster_summary_rows.append(row)

    cluster_summary_rows.sort(
        key=lambda row: (
            -int(row["field_count_floor"] or 0),
            -int(row["observation_year_count"] or 0),
            row["pricing_basis"],
            row["wbs_cluster"],
        )
    )
    cluster_operational_rows = [
        row
        for row in cluster_weight_rows
        if row["support_status"] == "operational" and row["weight_eligible"] == "yes"
    ]
    cluster_operational_rows.sort(
        key=lambda row: (
            row["pricing_basis"],
            row["wbs_cluster"],
            row["factor_name"],
        )
    )

    lines = [
        "# Unit Price Macro Correlation",
        "",
        "Ground-up yearly macro correlation support for the dashboard-driven unit-price estimator.",
        "",
        "## Source Package",
        "- Macro reference window: **2019-2026**.",
        "- Source: **IMF World Economic Outlook (April 2026)** annual dataset, published **April 15, 2026**.",
        f"- Reference URL: `{macro_rows[0]['source_url']}`.",
        "- Brent series uses `POILBRE`.",
        "- Indonesia inflation context uses `PCPI` and `PCPIPCH`.",
        "- Steel commodity input uses `PIORECR` iron ore as a steel-input proxy because a direct annual steel-HRC series was not available in the official annual files used here.",
        "- The deeper WBS cluster layer uses fuzzy-matched Level 4 descriptions, with Level 5 acting only as a fallback when Level 4 is missing, so campaign structure drift stays inside the same audit bucket.",
        "",
        "## Operational Rule",
        "- Operational forecast weights are computed on the **pooled pricing-basis yearly series** only.",
        "- Field-specific yearly Pearson outputs are retained for audit, but they are **diagnostic only** because DARAJAT has 3 overlap years, SALAK has 2, and WW has 1 in the current unit-price history window.",
        "- The clustered WBS depth layer is published as a separate diagnostic and screening view; it is not yet wired into live estimator scaling even when a cluster has enough support to calculate weights.",
        "- **Nominal/as-is Pearson** is the active weight basis. CPI-discounted 2026-equivalent comparisons are diagnostic only because the discounted treatment materially changes ordering/sign in several cells.",
        "- Correlation direction is preserved for audit, but weight magnitudes use absolute Pearson values. Negative signs indicate historical co-movement in this sparse sample, not a recommended inverse causal escalator.",
        "",
        "## Recommended Operational Weights",
        "| pricing_basis | factor | pearson_nominal | pearson_discounted_2026 | forecast_weight | direction | overlap_years |",
        "|---|---|---:|---:|---:|---|---|",
    ]

    for row in operational_rows:
        lines.append(
            f"| {row['pricing_basis']} | {row['factor_display_name']} | "
            f"{row['pearson_r_nominal'] or 'n/a'} | {row['pearson_r_discounted_2026'] or 'n/a'} | "
            f"{row['forecast_weight']} | {row['direction']} | {row['observation_years']} |"
        )

    lines.extend(
        [
            "",
            "## Clustered WBS Depth Layer",
            "| pricing_basis | wbs_cluster | field_coverage_count | field_count_floor | overlap_year_count | support_status | factor | pearson_nominal | pearson_discounted_2026 | forecast_weight | direction |",
            "|---|---|---:|---:|---:|---|---|---:|---:|---:|---|",
        ]
    )

    for row in cluster_operational_rows:
        lines.append(
            f"| {row['pricing_basis']} | {markdown_table_cell(row['wbs_cluster'])} | {row['field_coverage_count']} | {row['field_count_floor']} | {row['observation_year_count']} | {row['support_status']} | "
            f"{row['factor_display_name']} | {row['pearson_r_nominal'] or 'n/a'} | {row['pearson_r_discounted_2026'] or 'n/a'} | "
            f"{row['forecast_weight']} | {row['direction']} |"
        )

    lines.extend(
        [
            "",
            "## Cluster Coverage",
            "| pricing_basis | wbs_cluster | field_coverage_count | field_count_floor | field_count_peak | overlap_year_count | support_status | observation_years |",
            "|---|---|---:|---:|---:|---:|---|---|",
        ]
    )

    for row in cluster_summary_rows:
        lines.append(
            f"| {row['pricing_basis']} | {markdown_table_cell(row['wbs_cluster'])} | {row['field_coverage_count']} | {row['field_count_floor']} | {row['field_count_peak']} | "
            f"{row['observation_year_count']} | {row['support_status']} | {row['observation_years']} |"
        )

    lines.extend(
        [
            "",
            "## Scope Support",
            "| scope_type | field | pricing_basis | overlap_year_count | support_status |",
            "|---|---|---|---:|---|",
        ]
    )

    support_rows = sorted(
        {(row["scope_type"], row["field"], row["pricing_basis"], row["observation_year_count"], row["support_status"]) for row in diagnostic_scope_rows}
    )
    for scope_type, field, pricing_basis, year_count, status in support_rows:
        lines.append(f"| {scope_type} | {field} | {pricing_basis} | {year_count} | {status} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "- `active_day_rate` is the cleanest direct-well macro series after correcting the denominator to unique wells rather than repeated cost rows.",
            "- `depth_rate` remains materially different from `active_day_rate`, which supports keeping material/depth and service/day logic separate in the estimator.",
            "- `campaign_scope_benchmark` is the most steel-sensitive pooled basis in the current sample.",
            "- `per_well_job` remains unsupported for macro weighting because only one in-range observation exists.",
            "- The recurring cluster layer shows that casing, mud, rig, and other service-time families can be screened with the same annual macro proxies across all fields.",
            "",
            "## Recommendation",
            "- Keep macro weighting as a separate external-adjustment layer only.",
            "- Use the pooled pricing-basis rows as the auditable weight source when an external scenario is requested.",
            "- Use the clustered WBS layer to prioritize which subdrivers deserve future estimator promotion once the field-balanced signal is proven stable.",
            "- Keep field-specific rows visible in processed outputs, but do not let them drive estimator scaling until more yearly history is added.",
        ]
    )

    MACRO_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_history_mart()
    history_rows = read_csv(UNIT_PRICE_HISTORY_MART)
    macro_rows = read_csv(MACRO_REFERENCE_PATH)
    factor_rows = build_factor_rows(history_rows, macro_rows)
    weight_rows = build_weight_rows(factor_rows)
    cluster_factor_rows = build_cluster_factor_rows(history_rows, macro_rows)
    cluster_weight_rows = build_cluster_weight_rows(cluster_factor_rows)

    write_csv(MACRO_FACTORS_PATH, factor_rows, list(factor_rows[0].keys()))
    write_csv(MACRO_WEIGHTS_PATH, weight_rows, list(weight_rows[0].keys()))
    write_csv(MACRO_CLUSTER_WEIGHTS_PATH, cluster_weight_rows, list(cluster_weight_rows[0].keys()))
    write_report(macro_rows, weight_rows, cluster_weight_rows)
    print(
        "Wrote unit_price_macro_factors, unit_price_macro_weights, unit_price_macro_cluster_weights, and unit_price_macro_correlation report."
    )


if __name__ == "__main__":
    main()
