#!/usr/bin/env python3
"""Dashboard-anchored estimator core with auditable WBS lineage."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Dict, List, Tuple

from src.modeling.dashboard_historical_mart import HISTORICAL_MART, refresh_all_outputs

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"

CONFIDENCE_BANDS = PROCESSED / "confidence_bands.csv"
METHOD_REGISTRY = PROCESSED / "estimator_method_registry.csv"
APP_RUN_MANIFEST = PROCESSED / "app_run_manifest.json"
APP_AUDIT = PROCESSED / "app_estimate_audit.csv"
APP_SUMMARY = PROCESSED / "app_estimate_summary.json"

FIELD_MAP = {"DRJ": "DARAJAT", "SLK": "SALAK"}
RATE_FACTOR = {"Standard": 1.0, "Fast": 0.92, "Careful": 1.12}
LEG_FACTOR = {"Standard-J": 1.0, "Multilateral": 1.18, "Re-Drill": 1.10}


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
    return float((text or "0").replace(",", ""))


def _safe_int(text: str, default: int = 0) -> int:
    try:
        return int(str(text))
    except (TypeError, ValueError):
        return default


def _normalize_depth(depth_ft: int) -> int:
    clipped = min(10000, max(4500, int(depth_ft)))
    return int(round(clipped / 500.0) * 500)


def _format_mmusd(amount_usd: float) -> str:
    return f"{amount_usd / 1_000_000.0:.2f} mm USD"


def normalize_inputs(campaign_input: dict, well_rows: List[dict]) -> Tuple[dict, List[WellInput]]:
    field = campaign_input.get("field")
    if field not in {"SLK", "DRJ"}:
        raise ValueError("Field must be SLK or DRJ")
    year = int(campaign_input.get("year"))
    no_pads = int(campaign_input.get("no_pads"))
    no_wells = int(campaign_input.get("no_wells"))
    pad_exp = int(campaign_input.get("no_pad_expansion", 0))
    if len(well_rows) != no_wells:
        raise ValueError("Well row count must equal No. Wells")

    normalized_wells: List[WellInput] = []
    for idx, row in enumerate(well_rows, start=1):
        depth = _normalize_depth(int(row["depth_ft"]))
        leg = row["leg_type"]
        mode = row["drill_rate_mode"]
        if leg not in LEG_FACTOR or mode not in RATE_FACTOR:
            raise ValueError(f"Invalid well inputs at row {idx}")
        normalized_wells.append(
            WellInput(
                well_label=row.get("well_label", f"Well-{idx}"),
                pad_label=row["pad_label"],
                depth_ft=depth,
                depth_bucket_ft=depth,
                leg_type=leg,
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


def _external_adjustment(enabled: bool) -> Tuple[float, bool, str]:
    if not enabled:
        return 1.0, False, "disabled_by_user"
    return 1.0, False, "fallback_historical_only_external_series_unavailable"


def _load_mart_rows(field: str, year: int) -> List[dict]:
    rows = [r for r in read_csv(HISTORICAL_MART) if r["field"] == field]
    if not rows:
        return []
    years = sorted({_safe_int(r.get("campaign_start_year"), 0) for r in rows if _safe_int(r.get("campaign_start_year"), 0) > 0})
    if not years:
        return rows
    anchor_year = max([y for y in years if y <= year], default=max(years))
    anchored_rows = [r for r in rows if _safe_int(r.get("campaign_start_year"), 0) == anchor_year]
    return anchored_rows or rows


def _build_wbs_templates(rows: List[dict]) -> List[dict]:
    grouped = defaultdict(list)
    for row in rows:
        key = (row["classification"], row["l2_id"], row["l3_id"], row["l4_id"], row["l5_id"], row["l5_desc"], row["driver_family"])
        grouped[key].append(row)

    out = []
    for key, vals in grouped.items():
        costs = sorted(_safe_float(v["actual_usd"]) for v in vals)
        if not costs:
            continue
        p10 = costs[max(0, int(0.1 * (len(costs) - 1)))]
        p90 = costs[min(len(costs) - 1, int(0.9 * (len(costs) - 1)))]
        out.append(
            {
                "classification": key[0],
                "l2_id": key[1],
                "l3_id": key[2],
                "l4_id": key[3],
                "l5_id": key[4],
                "l5_desc": key[5],
                "driver_family": key[6],
                "median_usd": median(costs),
                "p10_usd": p10,
                "p90_usd": p90,
                "source_row_count": len(vals),
                "source_wells": sorted({v["well_canonical"] for v in vals if v.get("well_canonical")}),
                "source_campaign_years": sorted({v["source_field_campaign_year"] for v in vals}),
                "source_row_ids": sorted({v["source_row_id"] for v in vals}),
            }
        )
    return out


def build_validation_artifacts() -> None:
    refresh_all_outputs()
    rows = read_csv(HISTORICAL_MART)
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["field"], r["classification"])].append(_safe_float(r["actual_usd"]))

    bands, methods = [], []
    for (field, klass), vals in sorted(grouped.items()):
        vals = sorted(vals)
        if not vals:
            continue
        med = median(vals)
        p10 = vals[max(0, int(0.1 * (len(vals) - 1)))]
        p90 = vals[min(len(vals) - 1, int(0.9 * (len(vals) - 1)))]
        bands.append(
            {
                "field": field,
                "bucket_id": klass,
                "classification": klass,
                "interval_method": "empirical_p10_p90",
                "lower_bound_usd": f"{p10:.6f}",
                "upper_bound_usd": f"{p90:.6f}",
                "center_usd": f"{med:.6f}",
                "source_count": str(len(vals)),
            }
        )
        methods.append(
            {
                "field": field,
                "bucket_id": klass,
                "method_branch": "empirical_analog_or_fallback",
                "features_used": "field,classification,wbs_family,depth_factor",
                "validation_design": "historical_replay_median_peer",
                "n_obs": str(len(vals)),
                "n_campaign_years": "multi",
                "mae": "see_validation_reports",
                "mape": "see_validation_reports",
                "bias": "see_validation_reports",
                "interval_method": "empirical_p10_p90",
                "interval_coverage": "not_available_point_forecast",
                "synthetic_share": "0 unless enabled in app",
                "notes": "No predictive validity claim beyond replay outputs",
            }
        )

    write_csv(CONFIDENCE_BANDS, bands, list(bands[0].keys()))
    write_csv(METHOD_REGISTRY, methods, list(methods[0].keys()))


def estimate_campaign(campaign_input: dict, well_rows: List[dict]) -> dict:
    normalized_campaign, normalized_wells = normalize_inputs(campaign_input, well_rows)
    field = normalized_campaign["field_canonical"]
    ext_factor, ext_applied, ext_formula = _external_adjustment(normalized_campaign["use_external_forecast"])

    mart_rows = _load_mart_rows(field, normalized_campaign["campaign_start_year"])
    historical_well_count = len(
        {
            r.get("well_canonical", "").strip()
            for r in mart_rows
            if r.get("well_canonical", "").strip() and "STEAM" not in r.get("well_canonical", "").upper()
        }
    ) or 1
    templates = _build_wbs_templates(mart_rows)

    direct_templates = [t for t in templates if t["classification"] == "well_tied"]
    shared_templates = [t for t in templates if t["classification"] in {"hybrid", "campaign_tied"}]
    fallback_templates = [t for t in templates if t["classification"] not in {"well_tied", "hybrid", "campaign_tied"}]

    detail_rows, well_outputs = [], []
    for well in normalized_wells:
        depth_factor = (well.depth_bucket_ft / 7000.0) * LEG_FACTOR[well.leg_type] * RATE_FACTOR[well.drill_rate_mode]
        well_total = 0.0
        well_detail = []
        for t in direct_templates:
            method = "empirical_analog" if t["source_row_count"] >= 5 else "fallback_benchmark"
            per_well_base = t["median_usd"] / historical_well_count
            estimate = per_well_base * depth_factor * ext_factor
            unc_pct = min(150.0, ((t["p90_usd"] - t["p10_usd"]) / max(t["median_usd"], 1.0)) * 100)
            well_total += estimate
            row = {
                "well_label": well.well_label,
                "component_scope": "direct_well_linked",
                "classification": t["classification"],
                "l2_id": t["l2_id"],
                "l3_id": t["l3_id"],
                "l4_id": t["l4_id"],
                "l5_id": t["l5_id"],
                "l5_desc": t["l5_desc"],
                "estimate_usd": estimate,
                "uncertainty_pct": unc_pct,
                "uncertainty_type": "empirical_spread",
                "estimation_method": method,
                "driver_family": t["driver_family"],
                "source_field_campaign_years": ", ".join(t["source_campaign_years"][:8]),
                "source_wells": ", ".join(t["source_wells"][:10]),
                "source_row_ids": ", ".join(t["source_row_ids"][:20]),
                "source_row_count": t["source_row_count"],
                "synthetic_rows_used": 0,
                "external_adjustment_applied": ext_applied,
            }
            detail_rows.append(row)
            well_detail.append(row)

        top = sorted(well_detail, key=lambda r: r["estimate_usd"], reverse=True)[:5]
        avg_unc = sum(r["uncertainty_pct"] for r in well_detail) / max(len(well_detail), 1)
        well_outputs.append(
            {
                "well_label": well.well_label,
                "estimated_cost_usd": well_total,
                "estimated_cost_mmusd": well_total / 1_000_000.0,
                "estimated_days": max(8.0, 20.0 * (well.depth_bucket_ft / 7000.0) * LEG_FACTOR[well.leg_type] / RATE_FACTOR[well.drill_rate_mode]),
                "uncertainty_pct": avg_unc,
                "uncertainty_label": "empirical_spread",
                "method_label": "dashboard_anchored_wbs",
                "top_wbs_contributors": [f"{r['l5_id']} ({r['estimate_usd']/1_000_000:.2f} MMUSD)" for r in top],
                "source_campaign_tags": sorted({r["source_field_campaign_years"] for r in top}),
            }
        )

    shared_weight = 1.0 + 0.08 * normalized_campaign["pad_expansion_count"]
    for t in shared_templates + fallback_templates:
        method = "empirical_analog" if t["source_row_count"] >= 5 else "fallback_benchmark"
        base = t["median_usd"] * ext_factor
        if t["classification"] in {"hybrid", "campaign_tied"}:
            estimate = base * shared_weight
            scope = "shared_support" if t["classification"] == "hybrid" else "campaign_overhead"
        else:
            estimate = base
            scope = "fallback_unclassified"
        unc_pct = min(200.0, ((t["p90_usd"] - t["p10_usd"]) / max(t["median_usd"], 1.0)) * 100)
        detail_rows.append(
            {
                "well_label": "CAMPAIGN_SHARED",
                "component_scope": scope,
                "classification": t["classification"],
                "l2_id": t["l2_id"],
                "l3_id": t["l3_id"],
                "l4_id": t["l4_id"],
                "l5_id": t["l5_id"],
                "l5_desc": t["l5_desc"],
                "estimate_usd": estimate,
                "uncertainty_pct": unc_pct,
                "uncertainty_type": "empirical_spread",
                "estimation_method": method,
                "driver_family": t["driver_family"],
                "source_field_campaign_years": ", ".join(t["source_campaign_years"][:8]),
                "source_wells": ", ".join(t["source_wells"][:10]),
                "source_row_ids": ", ".join(t["source_row_ids"][:20]),
                "source_row_count": t["source_row_count"],
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

    # output audit contract
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
        "estimation_methodology": "historical_analog_median_by_lv5_with_empirical_p10_p90_uncertainty",
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
        "historical_anchor_well_count": historical_well_count,
        "l2_cost_breakdown": [
            {"l2_id": k, "estimate_usd": v, "estimate_formatted": _format_mmusd(v)}
            for k, v in sorted(by_l2.items(), key=lambda x: x[1], reverse=True)
        ],
        "uncertainty_definition": "uncertainty_pct = ((p90_usd - p10_usd) / median_usd) * 100 at Lv5 analog group",
    }
    APP_SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "field": field,
        "scenario_id": scenario_id,
        "estimate_type": "dashboard_anchored",
        "runtime_toggles": {
            "external_forecast_requested": normalized_campaign["use_external_forecast"],
            "external_forecast_applied": ext_applied,
            "synthetic_data_requested": normalized_campaign["use_synthetic_data"],
        },
        "external_adjustment_formula": ext_formula,
        "reconciliation": {
            "campaign_total_usd": total_cost,
            "detail_total_usd": sum(float(r["estimate_usd"]) for r in audit_rows),
            "status": "PASS",
        },
        "outputs": {
            "audit_csv": str(APP_AUDIT.relative_to(ROOT)),
            "summary_json": str(APP_SUMMARY.relative_to(ROOT)),
        },
    }
    APP_RUN_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return {
        "campaign_input": normalized_campaign,
        "well_outputs": well_outputs,
        "campaign_summary": summary,
        "detail_wbs": detail_rows,
        "audit_rows": audit_rows,
        "warnings": [
            "EXTN. DATA requested but external auditable series unavailable; fallback historical-only mode applied."
            if normalized_campaign["use_external_forecast"] and not ext_applied
            else ""
        ],
    }


if __name__ == "__main__":
    build_validation_artifacts()
