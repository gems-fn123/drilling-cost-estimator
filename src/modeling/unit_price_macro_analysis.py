#!/usr/bin/env python3
"""Build yearly macro factor and Pearson weighting artifacts for unit-price forecasts."""

from __future__ import annotations

import csv
import math
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeling.unit_price_history_pipeline import UNIT_PRICE_HISTORY_MART

REFERENCE_DIR = ROOT / "data" / "reference"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

MACRO_REFERENCE_PATH = REFERENCE_DIR / "macro_series_2019_2026.csv"
MACRO_FACTORS_PATH = PROCESSED / "unit_price_macro_factors.csv"
MACRO_WEIGHTS_PATH = PROCESSED / "unit_price_macro_weights.csv"
MACRO_REPORT_PATH = REPORTS / "unit_price_macro_correlation.md"
WELL_POOL_EXCLUSIONS = PROCESSED / "well_pool_exclusions.csv"

YEAR_START = 2019
YEAR_END = 2026
MIN_OPERATIONAL_YEARS = 4
ALL_FIELDS = "ALL_FIELDS"

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


def read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: List[dict], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def parse_float(value: str) -> float:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return 0.0
    return float(text)


def normalize_exclusion_well(well: str) -> str:
    text = str(well or "").strip().upper()
    text = re.sub(r"([ -])(RD|ML|OH)$", "", text)
    return re.sub(r"\s+", " ", text).strip()


def format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def pearson(xs: List[float], ys: List[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None

    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0.0 or den_y == 0.0:
        return None
    return num / (den_x * den_y)


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


def support_status(scope_type: str, overlap_year_count: int) -> str:
    if overlap_year_count < 3:
        return "insufficient_history"
    if scope_type == "pooled_pricing_basis" and overlap_year_count >= MIN_OPERATIONAL_YEARS:
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


def write_report(macro_rows: List[dict], weight_rows: List[dict]) -> None:
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
        "",
        "## Operational Rule",
        "- Operational forecast weights are computed on the **pooled pricing-basis yearly series** only.",
        "- Field-specific yearly Pearson outputs are retained for audit, but they are **diagnostic only** because DARAJAT has 3 overlap years, SALAK has 2, and WW has 1 in the current unit-price history window.",
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
            "",
            "## Recommendation",
            "- Keep macro weighting as a separate external-adjustment layer only.",
            "- Use the pooled pricing-basis rows as the auditable weight source when an external scenario is requested.",
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

    write_csv(MACRO_FACTORS_PATH, factor_rows, list(factor_rows[0].keys()))
    write_csv(MACRO_WEIGHTS_PATH, weight_rows, list(weight_rows[0].keys()))
    write_report(macro_rows, weight_rows)
    print("Wrote unit_price_macro_factors, unit_price_macro_weights, and unit_price_macro_correlation report.")


if __name__ == "__main__":
    main()
