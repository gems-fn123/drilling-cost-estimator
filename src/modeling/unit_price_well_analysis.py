#!/usr/bin/env python3
"""Build standard-only direct well benchmark artifacts from dashboard history."""

from __future__ import annotations

import csv
import math
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeling.unit_price_history_pipeline import UNIT_PRICE_HISTORY_CONTEXT, UNIT_PRICE_HISTORY_MART

PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

UNIT_PRICE_WELL_PROFILE = PROCESSED / "unit_price_well_profile.csv"
UNIT_PRICE_BENCHMARK = PROCESSED / "unit_price_benchmark.csv"
SERVICE_TIME_BANDS = PROCESSED / "service_time_band_reference.csv"
WELL_ANALYSIS_REPORT = REPORTS / "unit_price_well_analysis.md"
WELL_POOL_EXCLUSIONS = PROCESSED / "well_pool_exclusions.csv"

STANDARD_ASSUMPTION = "Standard-J"


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


def percentile(values: List[float], pct: float) -> float:
    arr = sorted(values)
    if not arr:
        return 0.0
    if len(arr) == 1:
        return arr[0]
    idx = (len(arr) - 1) * pct
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    frac = idx - lo
    if lo == hi:
        return arr[lo]
    return arr[lo] * (1.0 - frac) + arr[hi] * frac


def ensure_history_outputs() -> None:
    if UNIT_PRICE_HISTORY_MART.exists() and UNIT_PRICE_HISTORY_CONTEXT.exists():
        return
    subprocess.run([sys.executable, "src/modeling/unit_price_history_pipeline.py"], cwd=ROOT, check=True)


def load_active_exclusions() -> dict[tuple[str, str], dict]:
    if not WELL_POOL_EXCLUSIONS.exists():
        return {}
    return {
        (row["field"], normalize_exclusion_well(row["well_canonical"])): row
        for row in read_csv(WELL_POOL_EXCLUSIONS)
        if row.get("status", "").strip().lower() == "active"
    }


def build_well_profile_rows(context_rows: List[dict], mart_rows: List[dict], active_exclusions: dict[tuple[str, str], dict]) -> List[dict]:
    cost_lookup: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in mart_rows:
        well = row.get("well_canonical", "")
        if not well:
            continue
        key = (row["campaign_canonical"], well)
        cost_lookup[key][row["pricing_basis"]] += parse_float(row.get("actual_cost_usd", "0"))

    profile_rows: List[dict] = []
    for row in sorted(context_rows, key=lambda item: (item["field"], item["campaign_year"], item["well_canonical"])):
        key = (row["campaign_canonical"], row["well_canonical"])
        exclusion = active_exclusions.get((row["field"], normalize_exclusion_well(row["well_canonical"])))
        basis_costs = cost_lookup.get(key, {})
        active_days = parse_float(row.get("active_operational_days", "0"))
        depth_ft = parse_float(row.get("actual_depth_ft", "0"))
        actual_days = parse_float(row.get("actual_days", "0"))
        npt_days = parse_float(row.get("npt_days", "0"))

        pace_days_per_1000ft = active_days / (depth_ft / 1000.0) if active_days > 0.0 and depth_ft > 0.0 else 0.0
        ft_per_active_day = depth_ft / active_days if active_days > 0.0 and depth_ft > 0.0 else 0.0

        active_day_cost = basis_costs.get("active_day_rate", 0.0)
        depth_cost = basis_costs.get("depth_rate", 0.0)
        per_well_job_cost = basis_costs.get("per_well_job", 0.0)
        total_direct_cost = active_day_cost + depth_cost + per_well_job_cost

        profile_rows.append(
            {
                "field": row["field"],
                "campaign_canonical": row["campaign_canonical"],
                "campaign_year": row["campaign_year"],
                "well_canonical": row["well_canonical"],
                "well_name_actual": row["well_name_actual"],
                "estimator_well_type": STANDARD_ASSUMPTION,
                "exclude_from_estimator_pool": "yes" if exclusion else "no",
                "exclusion_reason": exclusion["reason"] if exclusion else "",
                "actual_depth_ft": f"{depth_ft:.6f}",
                "actual_days": f"{actual_days:.6f}",
                "npt_days": f"{npt_days:.6f}",
                "active_operational_days": f"{active_days:.6f}",
                "pace_days_per_1000ft": f"{pace_days_per_1000ft:.6f}" if pace_days_per_1000ft else "",
                "ft_per_active_day": f"{ft_per_active_day:.6f}" if ft_per_active_day else "",
                "service_time_band": "",
                "active_day_cost_usd": f"{active_day_cost:.6f}",
                "active_day_rate_usd_per_day": f"{(active_day_cost / active_days):.6f}" if active_day_cost > 0.0 and active_days > 0.0 else "",
                "depth_cost_usd": f"{depth_cost:.6f}",
                "depth_rate_usd_per_ft": f"{(depth_cost / depth_ft):.6f}" if depth_cost > 0.0 and depth_ft > 0.0 else "",
                "per_well_job_cost_usd": f"{per_well_job_cost:.6f}",
                "total_direct_well_cost_usd": f"{total_direct_cost:.6f}",
            }
        )

    return profile_rows


def build_service_band_rows(profile_rows: List[dict]) -> List[dict]:
    band_rows: List[dict] = []
    profiles_by_field: dict[str, List[dict]] = defaultdict(list)
    for row in profile_rows:
        if row["exclude_from_estimator_pool"] == "yes":
            continue
        profiles_by_field[row["field"]].append(row)

    for field in sorted(profiles_by_field):
        rows = profiles_by_field[field]
        pace_values = [parse_float(row["pace_days_per_1000ft"]) for row in rows if row["pace_days_per_1000ft"]]
        fast_upper = percentile(pace_values, 1.0 / 3.0)
        careful_lower = percentile(pace_values, 2.0 / 3.0)

        for row in rows:
            pace = parse_float(row["pace_days_per_1000ft"])
            if not pace:
                row["service_time_band"] = ""
            elif pace <= fast_upper:
                row["service_time_band"] = "Fast"
            elif pace >= careful_lower:
                row["service_time_band"] = "Careful"
            else:
                row["service_time_band"] = "Standard"

        fast_values = [parse_float(row["pace_days_per_1000ft"]) for row in rows if row["service_time_band"] == "Fast"]
        standard_values = [parse_float(row["pace_days_per_1000ft"]) for row in rows if row["service_time_band"] == "Standard"]
        careful_values = [parse_float(row["pace_days_per_1000ft"]) for row in rows if row["service_time_band"] == "Careful"]

        band_rows.append(
            {
                "field": field,
                "estimator_well_type": STANDARD_ASSUMPTION,
                "observation_count": str(len(pace_values)),
                "fast_observation_count": str(len(fast_values)),
                "standard_observation_count": str(len(standard_values)),
                "careful_observation_count": str(len(careful_values)),
                "pace_metric": "active_operational_days_per_1000ft",
                "fast_rule": f"<= {fast_upper:.6f}",
                "standard_rule": f"> {fast_upper:.6f} and < {careful_lower:.6f}",
                "careful_rule": f">= {careful_lower:.6f}",
                "fast_upper_days_per_1000ft": f"{fast_upper:.6f}",
                "standard_lower_days_per_1000ft": f"{fast_upper:.6f}",
                "standard_upper_days_per_1000ft": f"{careful_lower:.6f}",
                "careful_lower_days_per_1000ft": f"{careful_lower:.6f}",
                "fast_p50_days_per_1000ft": f"{median(fast_values):.6f}" if fast_values else "",
                "standard_p50_days_per_1000ft": f"{median(standard_values):.6f}" if standard_values else "",
                "careful_p50_days_per_1000ft": f"{median(careful_values):.6f}" if careful_values else "",
                "fast_lower_ft_per_active_day": f"{(1000.0 / fast_upper):.6f}" if fast_upper > 0.0 else "",
                "standard_lower_ft_per_active_day": f"{(1000.0 / careful_lower):.6f}" if careful_lower > 0.0 else "",
                "standard_upper_ft_per_active_day": f"{(1000.0 / fast_upper):.6f}" if fast_upper > 0.0 else "",
                "careful_upper_ft_per_active_day": f"{(1000.0 / careful_lower):.6f}" if careful_lower > 0.0 else "",
                "source_note": "Field-specific terciles on active_operational_days per 1000 ft. NPT is excluded from the base time metric.",
            }
        )

    return band_rows


def build_benchmark_rows(profile_rows: List[dict]) -> List[dict]:
    profile_fields = [
        ("active_day_rate", "active_day_rate_usd_per_day", "usd_per_active_day"),
        ("depth_rate", "depth_rate_usd_per_ft", "usd_per_ft"),
        ("per_well_job", "per_well_job_cost_usd", "usd_per_well"),
        ("total_direct_well_cost", "total_direct_well_cost_usd", "usd_per_well"),
    ]

    basis_cost_totals: dict[tuple[str, str], float] = defaultdict(float)
    field_direct_totals: dict[str, float] = defaultdict(float)
    for row in profile_rows:
        if row["exclude_from_estimator_pool"] == "yes":
            continue
        field = row["field"]
        active = parse_float(row["active_day_cost_usd"])
        depth = parse_float(row["depth_cost_usd"])
        per_job = parse_float(row["per_well_job_cost_usd"])
        basis_cost_totals[(field, "active_day_rate")] += active
        basis_cost_totals[(field, "depth_rate")] += depth
        basis_cost_totals[(field, "per_well_job")] += per_job
        field_direct_totals[field] += active + depth + per_job

    benchmark_rows: List[dict] = []
    for field in sorted({row["field"] for row in profile_rows}):
        for pricing_basis, value_column, unit_label in profile_fields:
            values = [
                parse_float(row[value_column])
                for row in profile_rows
                if row["field"] == field
                and row["exclude_from_estimator_pool"] == "no"
                and parse_float(row[value_column]) > 0.0
            ]
            if not values:
                continue

            if pricing_basis == "total_direct_well_cost":
                share_pct = 100.0
            else:
                share_pct = 0.0
                if field_direct_totals[field] > 0.0:
                    share_pct = 100.0 * basis_cost_totals[(field, pricing_basis)] / field_direct_totals[field]

            benchmark_rows.append(
                {
                    "field": field,
                    "estimator_well_type": STANDARD_ASSUMPTION,
                    "pricing_basis": pricing_basis,
                    "value_unit": unit_label,
                    "observation_count": str(len(values)),
                    "median_value": f"{median(values):.6f}",
                    "mean_value": f"{mean(values):.6f}",
                    "p10_value": f"{percentile(values, 0.10):.6f}",
                    "p90_value": f"{percentile(values, 0.90):.6f}",
                    "min_value": f"{min(values):.6f}",
                    "max_value": f"{max(values):.6f}",
                    "direct_cost_share_pct": f"{share_pct:.6f}",
                }
            )

    return benchmark_rows


def write_report(profile_rows: List[dict], benchmark_rows: List[dict], band_rows: List[dict]) -> None:
    direct_share = {
        (row["field"], row["pricing_basis"]): parse_float(row["direct_cost_share_pct"])
        for row in benchmark_rows
        if row["pricing_basis"] in {"active_day_rate", "depth_rate", "per_well_job"}
    }
    benchmark_lookup = {(row["field"], row["pricing_basis"]): row for row in benchmark_rows}

    lines = [
        "# Unit Price Well Analysis",
        "",
        "Standard-only direct well analysis for the dashboard-driven estimator path.",
        "",
        "## Rules Applied",
        "- All new estimated wells are treated as `Standard-J` in the estimator path.",
        "- Base well time uses `active_operational_days = actual_days - npt_days`.",
        "- Service-time bands are field-specific terciles on `active_operational_days per 1000 ft`.",
        "- Historical complexity is not used to split the direct well benchmark in this branch.",
        "",
        "## Coverage",
        f"- Direct well profiles built: **{len(profile_rows)}** wells.",
        f"- Estimator-pool direct wells after exclusions: **{sum(1 for row in profile_rows if row['exclude_from_estimator_pool'] == 'no')}** wells.",
        f"- Fields covered: **{', '.join(sorted({row['field'] for row in profile_rows}))}**.",
        "",
        "## Direct Well Cost Mix",
        "| field | service/time share % | material/depth share % | per-well job share % |",
        "|---|---:|---:|---:|",
    ]

    for field in sorted({row["field"] for row in profile_rows}):
        lines.append(
            f"| {field} | {direct_share.get((field, 'active_day_rate'), 0.0):.2f} | "
            f"{direct_share.get((field, 'depth_rate'), 0.0):.2f} | "
            f"{direct_share.get((field, 'per_well_job'), 0.0):.2f} |"
        )

    lines.extend(
        [
            "",
            "## Benchmark Medians",
            "| field | active day rate (USD/day) | depth rate (USD/ft) | total direct well cost (USD/well) |",
            "|---|---:|---:|---:|",
        ]
    )

    for field in sorted({row["field"] for row in profile_rows}):
        active_row = benchmark_lookup.get((field, "active_day_rate"))
        depth_row = benchmark_lookup.get((field, "depth_rate"))
        total_row = benchmark_lookup.get((field, "total_direct_well_cost"))
        lines.append(
            f"| {field} | {active_row['median_value'] if active_row else 'n/a'} | "
            f"{depth_row['median_value'] if depth_row else 'n/a'} | "
            f"{total_row['median_value'] if total_row else 'n/a'} |"
        )

    lines.extend(
        [
            "",
            "## Service-Time Bands",
            "| field | fast | standard | careful | observation_count |",
            "|---|---|---|---|---:|",
        ]
    )

    for row in band_rows:
        lines.append(
            f"| {row['field']} | {row['fast_rule']} days/1000ft | "
            f"{row['standard_rule']} days/1000ft | {row['careful_rule']} days/1000ft | "
            f"{row['observation_count']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "- The dominant direct-well cost chunk remains the service/time side (`active_day_rate`) across all three fields.",
            "- DARAJAT and WW show slower pace bands than SALAK, which is why field-specific service-time references are retained even though complexity splitting was removed.",
            "- These outputs are suitable as the standard-well direct benchmark layer; shared/campaign scope should stay outside this file and remain in campaign/hybrid logic.",
        ]
    )

    WELL_ANALYSIS_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_history_outputs()
    context_rows = read_csv(UNIT_PRICE_HISTORY_CONTEXT)
    mart_rows = read_csv(UNIT_PRICE_HISTORY_MART)
    active_exclusions = load_active_exclusions()
    profile_rows = build_well_profile_rows(context_rows, mart_rows, active_exclusions)
    band_rows = build_service_band_rows(profile_rows)
    benchmark_rows = build_benchmark_rows(profile_rows)

    write_csv(UNIT_PRICE_WELL_PROFILE, profile_rows, list(profile_rows[0].keys()))
    write_csv(UNIT_PRICE_BENCHMARK, benchmark_rows, list(benchmark_rows[0].keys()))
    write_csv(SERVICE_TIME_BANDS, band_rows, list(band_rows[0].keys()))
    write_report(profile_rows, benchmark_rows, band_rows)
    print("Wrote unit_price_well_profile, unit_price_benchmark, service_time_band_reference, and unit_price_well_analysis report.")


if __name__ == "__main__":
    main()
