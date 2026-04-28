#!/usr/bin/env python3
"""Build field-level NPT contribution and penalty reference artifacts."""

from __future__ import annotations

import csv
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeling.unit_price_history_pipeline import UNIT_PRICE_HISTORY_CONTEXT
from src.modeling.unit_price_well_analysis import UNIT_PRICE_BENCHMARK

PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

WELL_INSTANCE_CONTEXT = PROCESSED / "well_instance_context.csv"
WELL_INSTANCE_EVENT_CONTEXT = PROCESSED / "well_instance_event_context.csv"
WELL_POOL_EXCLUSIONS = PROCESSED / "well_pool_exclusions.csv"

NPT_EVENT_ENRICHED = PROCESSED / "npt_event_enriched.csv"
NPT_CONTRIBUTION_SUMMARY = PROCESSED / "npt_contribution_summary.csv"
NPT_PENALTY_REFERENCE = PROCESSED / "npt_penalty_reference.csv"
NPT_REPORT = REPORTS / "unit_price_npt_contribution.md"

FIELDS = ["DARAJAT", "SALAK", "WAYANG_WINDU"]


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


def format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


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


def normalize_exclusion_well(well: str) -> str:
    text = str(well or "").strip().upper()
    text = re.sub(r"([ -])(RD|ML|OH)$", "", text)
    return re.sub(r"\s+", " ", text).strip()


def infer_field_from_well_name(well: str) -> str:
    text = str(well or "").strip().upper()
    if text.startswith("AWI"):
        return "SALAK"
    if text.startswith("DRJ"):
        return "DARAJAT"
    if text.startswith(("MBA", "MBI", "MBD")):
        return "WAYANG_WINDU"
    return ""


def ensure_dependencies() -> None:
    missing = [
        path
        for path in [WELL_INSTANCE_CONTEXT, WELL_INSTANCE_EVENT_CONTEXT, UNIT_PRICE_HISTORY_CONTEXT, UNIT_PRICE_BENCHMARK]
        if not path.exists()
    ]
    if not missing:
        return
    subprocess.run([sys.executable, "src/modeling/unit_price_well_analysis.py"], cwd=ROOT, check=True)


def load_active_exclusions() -> set[tuple[str, str]]:
    if not WELL_POOL_EXCLUSIONS.exists():
        return set()
    return {
        (row["field"], normalize_exclusion_well(row["well_canonical"]))
        for row in read_csv(WELL_POOL_EXCLUSIONS)
        if row.get("status", "").strip().lower() == "active"
    }


def build_context_index() -> dict[str, set[tuple[str, str, str]]]:
    index: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for source_row in read_csv(WELL_INSTANCE_CONTEXT):
        for key in [source_row.get("well_canonical", ""), source_row.get("well_base_canonical", "")]:
            if key:
                index[key].add((source_row.get("field", ""), source_row.get("campaign_canonical", ""), source_row.get("well_base_canonical", "") or source_row.get("well_canonical", "")))

    for source_row in read_csv(UNIT_PRICE_HISTORY_CONTEXT):
        key = source_row.get("well_canonical", "")
        if key:
            index[key].add((source_row.get("field", ""), source_row.get("campaign_canonical", ""), source_row.get("well_canonical", "")))

    return index


def enrich_npt_events() -> List[dict]:
    exclusions = load_active_exclusions()
    context_index = build_context_index()
    enriched_rows: List[dict] = []

    for row in read_csv(WELL_INSTANCE_EVENT_CONTEXT):
        if row.get("event_type", "").strip().upper() != "NPT":
            continue

        well_canonical = row.get("well_canonical", "") or row.get("well_base_canonical", "")
        well_base = row.get("well_base_canonical", "") or well_canonical
        field = row.get("field", "")
        campaign = row.get("campaign_canonical", "")
        mapping_status = "source_full"

        matches = context_index.get(well_canonical) or context_index.get(well_base) or set()
        fields = {match[0] for match in matches if match[0]}
        campaigns = {match[1] for match in matches if match[1]}
        base_names = {match[2] for match in matches if match[2]}

        if not field and len(fields) == 1:
            field = next(iter(fields))
            mapping_status = "field_imputed_from_unique_context"
        if not campaign and len(campaigns) == 1:
            campaign = next(iter(campaigns))
            mapping_status = "campaign_imputed_from_unique_context" if mapping_status == "source_full" else "field_campaign_imputed_from_unique_context"
        if not well_base and len(base_names) == 1:
            well_base = next(iter(base_names))
        if not field:
            inferred_field = infer_field_from_well_name(well_canonical or well_base)
            if inferred_field:
                field = inferred_field
                mapping_status = "field_inferred_from_name_prefix"
        if not well_base:
            well_base = well_canonical

        coverage_status = "field_available" if field else "unresolved"
        if field and campaign:
            coverage_status = "field_campaign_available"

        analysis_well_key = ""
        if field:
            normalized_base = normalize_exclusion_well(well_base)
            analysis_well_key = f"{campaign}|{normalized_base}" if campaign else f"{field}|{normalized_base}"
        excluded = "yes" if field and (field, normalize_exclusion_well(well_base or well_canonical)) in exclusions else "no"

        enriched_rows.append(
            {
                "field": field,
                "campaign_canonical": campaign,
                "well_canonical": well_canonical,
                "well_base_canonical": well_base,
                "analysis_well_key": analysis_well_key,
                "event_major_category": row.get("event_major_category", ""),
                "event_detail": row.get("event_detail", ""),
                "event_duration_days": row.get("event_duration_days", ""),
                "mapping_status": mapping_status,
                "coverage_status": coverage_status,
                "confidence": row.get("confidence", ""),
                "exclude_from_estimator_pool": excluded,
            }
        )

    return enriched_rows


def build_summary_rows(enriched_rows: List[dict]) -> List[dict]:
    usable_rows = [
        row
        for row in enriched_rows
        if row["field"] and row["exclude_from_estimator_pool"] == "no"
    ]

    rows_by_field: dict[str, List[dict]] = defaultdict(list)
    for row in usable_rows:
        rows_by_field[row["field"]].append(row)

    summary_rows: List[dict] = []
    for field in FIELDS:
        field_rows = rows_by_field.get(field, [])
        if not field_rows:
            summary_rows.append(
                {
                    "field": field,
                    "group_level": "coverage",
                    "event_major_category": "",
                    "event_detail": "",
                    "event_count": "0",
                    "distinct_well_count": "0",
                    "total_npt_days": "0.000000",
                    "share_of_field_npt_days": "0.000000",
                    "avg_event_duration_days": "",
                    "median_impacted_well_npt_days": "",
                    "category_to_total_npt_pearson": "",
                    "category_to_total_npt_r2": "",
                    "support_status": "no_event_context",
                }
            )
            continue

        field_total_npt = sum(parse_float(row["event_duration_days"]) for row in field_rows)
        well_totals: dict[str, float] = defaultdict(float)
        for row in field_rows:
            well_totals[row["analysis_well_key"]] += parse_float(row["event_duration_days"])
        all_well_keys = sorted(well_totals)

        for group_level, group_fn in (
            ("major_category", lambda item: (item["event_major_category"], "")),
            ("detail", lambda item: (item["event_major_category"], item["event_detail"])),
        ):
            grouped: dict[tuple[str, str], List[dict]] = defaultdict(list)
            for row in field_rows:
                grouped[group_fn(row)].append(row)

            for (major, detail), group_rows in sorted(grouped.items(), key=lambda item: sum(parse_float(row["event_duration_days"]) for row in item[1]), reverse=True):
                by_well: dict[str, float] = defaultdict(float)
                for row in group_rows:
                    by_well[row["analysis_well_key"]] += parse_float(row["event_duration_days"])
                impacted_values = sorted(by_well.values())
                total_days = sum(impacted_values)
                avg_event = mean(parse_float(row["event_duration_days"]) for row in group_rows)
                x = [by_well.get(well_key, 0.0) for well_key in all_well_keys]
                y = [well_totals[well_key] for well_key in all_well_keys]
                corr = pearson(x, y)

                summary_rows.append(
                    {
                        "field": field,
                        "group_level": group_level,
                        "event_major_category": major,
                        "event_detail": detail,
                        "event_count": str(len(group_rows)),
                        "distinct_well_count": str(len(impacted_values)),
                        "total_npt_days": f"{total_days:.6f}",
                        "share_of_field_npt_days": f"{(100.0 * total_days / field_total_npt):.6f}" if field_total_npt > 0.0 else "0.000000",
                        "avg_event_duration_days": f"{avg_event:.6f}",
                        "median_impacted_well_npt_days": f"{median(impacted_values):.6f}" if impacted_values else "",
                        "category_to_total_npt_pearson": format_float(corr),
                        "category_to_total_npt_r2": format_float((corr ** 2) if corr is not None else None),
                        "support_status": "supported",
                    }
                )

    return summary_rows


def load_benchmark_lookup() -> dict[tuple[str, str], dict]:
    return {
        (row["field"], row["pricing_basis"]): row
        for row in read_csv(UNIT_PRICE_BENCHMARK)
    }


def build_penalty_rows(enriched_rows: List[dict], summary_rows: List[dict]) -> List[dict]:
    benchmark_lookup = load_benchmark_lookup()
    usable_rows = [
        row
        for row in enriched_rows
        if row["field"] and row["exclude_from_estimator_pool"] == "no"
    ]
    rows_by_field: dict[str, List[dict]] = defaultdict(list)
    for row in usable_rows:
        rows_by_field[row["field"]].append(row)

    penalty_rows: List[dict] = []
    for field in FIELDS:
        field_rows = rows_by_field.get(field, [])
        active_day_benchmark = benchmark_lookup.get((field, "active_day_rate"))
        direct_cost_benchmark = benchmark_lookup.get((field, "total_direct_well_cost"))
        if not field_rows or not active_day_benchmark or not direct_cost_benchmark:
            penalty_rows.append(
                {
                    "field": field,
                    "rank_in_field": "",
                    "event_major_category": "",
                    "top_event_detail": "",
                    "support_status": "no_event_context",
                    "total_npt_days": "0.000000",
                    "share_of_field_npt_days": "0.000000",
                    "impacted_well_count": "0",
                    "median_impacted_well_npt_days": "",
                    "p90_impacted_well_npt_days": "",
                    "active_day_rate_median_usd_per_day": active_day_benchmark["median_value"] if active_day_benchmark else "",
                    "median_direct_well_cost_usd": direct_cost_benchmark["median_value"] if direct_cost_benchmark else "",
                    "penalty_cost_p50_usd": "",
                    "penalty_cost_p90_usd": "",
                    "penalty_pct_of_median_direct_well_cost": "",
                    "category_to_total_npt_r2": "",
                }
            )
            continue

        grouped: dict[str, List[dict]] = defaultdict(list)
        for row in field_rows:
            grouped[row["event_major_category"]].append(row)

        ranked_majors = sorted(grouped, key=lambda key: sum(parse_float(row["event_duration_days"]) for row in grouped[key]), reverse=True)
        active_day_rate = parse_float(active_day_benchmark["median_value"])
        median_direct_cost = parse_float(direct_cost_benchmark["median_value"])

        summary_lookup = {
            (row["field"], row["group_level"], row["event_major_category"], row["event_detail"]): row
            for row in summary_rows
        }

        for rank, major in enumerate(ranked_majors, start=1):
            group_rows = grouped[major]
            by_well: dict[str, float] = defaultdict(float)
            detail_totals: Counter[str] = Counter()
            for row in group_rows:
                duration = parse_float(row["event_duration_days"])
                by_well[row["analysis_well_key"]] += duration
                detail_totals[row["event_detail"]] += duration
            impacted_values = sorted(by_well.values())
            total_days = sum(impacted_values)
            top_detail, top_detail_days = detail_totals.most_common(1)[0]
            penalty_p50 = median(impacted_values) * active_day_rate
            penalty_p90 = percentile(impacted_values, 0.90) * active_day_rate
            summary_row = summary_lookup.get((field, "major_category", major, ""))

            penalty_rows.append(
                {
                    "field": field,
                    "rank_in_field": str(rank),
                    "event_major_category": major,
                    "top_event_detail": top_detail,
                    "support_status": "supported",
                    "total_npt_days": f"{total_days:.6f}",
                    "share_of_field_npt_days": summary_row["share_of_field_npt_days"] if summary_row else "",
                    "impacted_well_count": str(len(impacted_values)),
                    "median_impacted_well_npt_days": f"{median(impacted_values):.6f}",
                    "p90_impacted_well_npt_days": f"{percentile(impacted_values, 0.90):.6f}",
                    "active_day_rate_median_usd_per_day": active_day_benchmark["median_value"],
                    "median_direct_well_cost_usd": direct_cost_benchmark["median_value"],
                    "penalty_cost_p50_usd": f"{penalty_p50:.6f}",
                    "penalty_cost_p90_usd": f"{penalty_p90:.6f}",
                    "penalty_pct_of_median_direct_well_cost": f"{(100.0 * penalty_p50 / median_direct_cost):.6f}" if median_direct_cost > 0.0 else "",
                    "category_to_total_npt_r2": summary_row["category_to_total_npt_r2"] if summary_row else "",
                }
            )

    return penalty_rows


def write_report(enriched_rows: List[dict], summary_rows: List[dict], penalty_rows: List[dict]) -> None:
    mapping_counts = Counter(row["mapping_status"] for row in enriched_rows)
    usable_rows = [row for row in enriched_rows if row["field"] and row["exclude_from_estimator_pool"] == "no"]
    unresolved_rows = [row for row in enriched_rows if not row["field"]]

    lines = [
        "# NPT Contribution Analysis",
        "",
        "Field-level statistical support for what contributes most toward NPT, plus penalty references tied to the standard-well service-day benchmark.",
        "",
        "## Coverage",
        f"- NPT event rows analyzed after active pool exclusions: **{len(usable_rows)}**.",
        f"- Unresolved event rows with no field attribution kept out of contribution stats: **{len(unresolved_rows)}**.",
        "- Event context is strongest for **DARAJAT** and **SALAK** with direct context linkage.",
        "- **WAYANG_WINDU** is currently supported at field level through well-name-prefix mapping, but campaign-specific WW attribution is not yet available in the local event context.",
        "",
        "## Mapping Support",
    ]
    for key, value in sorted(mapping_counts.items()):
        lines.append(f"- `{key}`: **{value}** rows")

    lines.extend(
        [
            "",
            "## Top Major Contributors",
            "| field | major category | total NPT days | share of field NPT % | impacted wells | R^2 vs total field-well NPT |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )

    top_major_rows = [
        row
        for row in summary_rows
        if row["group_level"] == "major_category" and row["support_status"] == "supported"
    ]
    top_major_rows.sort(key=lambda row: (row["field"], -parse_float(row["total_npt_days"])))
    seen_fields: set[str] = set()
    for row in top_major_rows:
        if row["field"] in seen_fields:
            continue
        field_rows = [candidate for candidate in top_major_rows if candidate["field"] == row["field"]][:5]
        for candidate in field_rows:
            lines.append(
                f"| {candidate['field']} | {candidate['event_major_category']} | {candidate['total_npt_days']} | "
                f"{candidate['share_of_field_npt_days']} | {candidate['distinct_well_count']} | "
                f"{candidate['category_to_total_npt_r2'] or 'n/a'} |"
            )
        seen_fields.add(row["field"])

    lines.extend(
        [
            "",
            "## Penalty Reference",
            "| field | rank | major category | top detail | penalty p50 (USD) | penalty as % of median direct well cost |",
            "|---|---:|---|---|---:|---:|",
        ]
    )

    for row in penalty_rows:
        if row["support_status"] != "supported":
            lines.append(f"| {row['field']} |  | no event context |  |  |  |")
            continue
        if int(row["rank_in_field"]) > 5:
            continue
        lines.append(
            f"| {row['field']} | {row['rank_in_field']} | {row['event_major_category']} | {row['top_event_detail']} | "
            f"{row['penalty_cost_p50_usd']} | {row['penalty_pct_of_median_direct_well_cost']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "- Contribution rank is driven first by total NPT days and then supported with a per-well correlation/R^2 against total well NPT, so dominant categories are both frequent and explanatory rather than just one-off long events.",
            "- Penalty references multiply field median active-day service rate by the median/p90 impacted-well NPT days for each category. They are intended as category-specific add-ons, not as the base direct well estimate.",
            "- WW penalty support is field-level only at this stage; campaign-level WW penalty attribution should stay flagged as not yet supported.",
        ]
    )

    NPT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dependencies()
    enriched_rows = enrich_npt_events()
    summary_rows = build_summary_rows(enriched_rows)
    penalty_rows = build_penalty_rows(enriched_rows, summary_rows)

    write_csv(NPT_EVENT_ENRICHED, enriched_rows, list(enriched_rows[0].keys()))
    write_csv(NPT_CONTRIBUTION_SUMMARY, summary_rows, list(summary_rows[0].keys()))
    write_csv(NPT_PENALTY_REFERENCE, penalty_rows, list(penalty_rows[0].keys()))
    write_report(enriched_rows, summary_rows, penalty_rows)
    print("Wrote npt_event_enriched, npt_contribution_summary, npt_penalty_reference, and unit_price_npt_contribution report.")


if __name__ == "__main__":
    main()
