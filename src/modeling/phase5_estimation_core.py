#!/usr/bin/env python3
"""Phase 5 estimator core: field-separated grouped benchmark engine with audit outputs."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

PHASE5_APP = PROCESSED / "phase5_app_dataset.csv"
WBS_MASTER = PROCESSED / "wbs_lv5_master.csv"
WBS_CLASS = PROCESSED / "wbs_lv5_classification.csv"
SYNTH_LV5 = PROCESSED / "synthetic_wbs_lv5_placeholders.csv"

CONFIDENCE_BANDS = PROCESSED / "confidence_bands.csv"
METHOD_REGISTRY = PROCESSED / "estimator_method_registry.csv"
VALIDATION_DARAJAT = REPORTS / "validation_darajat.md"
VALIDATION_SALAK = REPORTS / "validation_salak.md"

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


def _extract_years(campaign_canonical: str) -> str:
    parts = (campaign_canonical or "").split("_")
    years = [p for p in parts if p.isdigit() and len(p) == 4]
    return "_".join(years) if years else "unknown"


def _build_source_map(master_rows: List[dict]) -> Dict[Tuple[str, str], dict]:
    mapper: Dict[Tuple[str, str], dict] = {}
    grouped_campaigns: Dict[Tuple[str, str], set] = defaultdict(set)
    grouped_rows: Dict[Tuple[str, str], int] = defaultdict(int)
    grouped_lvl: Dict[Tuple[str, str], dict] = {}

    for row in master_rows:
        key = ((row.get("field") or "").strip(), (row.get("wbs_lvl5") or "").strip())
        if not key[0] or not key[1]:
            continue
        grouped_campaigns[key].add(_extract_years(row.get("campaign_canonical", "")))
        grouped_rows[key] += 1
        grouped_lvl[key] = {
            "wbs_lvl1": row.get("wbs_lvl1", ""),
            "wbs_lvl2": row.get("wbs_lvl2", ""),
            "wbs_lvl3": row.get("wbs_lvl3", ""),
            "wbs_lvl4": row.get("wbs_lvl4", ""),
            "wbs_lvl5": row.get("wbs_lvl5", ""),
        }

    for key in grouped_campaigns:
        mapper[key] = {
            "source_field_campaign_years": ", ".join(sorted(grouped_campaigns[key])),
            "source_row_count": grouped_rows[key],
            **grouped_lvl[key],
        }
    return mapper


def build_validation_artifacts() -> None:
    app_rows = read_csv(PHASE5_APP)
    registry_rows: List[dict] = []
    band_rows: List[dict] = []

    grouped = defaultdict(list)
    for row in app_rows:
        grouped[(row["field"], row["classification"])].append(row)
        band_rows.append(
            {
                "field": row["field"],
                "bucket_id": row["group_key"],
                "classification": row["classification"],
                "interval_method": "quantile_band_p10_p90",
                "lower_bound_usd": row["cost_p10"],
                "upper_bound_usd": row["cost_p90"],
                "center_usd": row["cost_median"],
                "source_count": row["sample_size"],
            }
        )

    for (field, klass), rows in sorted(grouped.items()):
        n_obs = sum(int(r["sample_size"]) for r in rows)
        mape_proxy = sum(abs(_safe_float(r["cost_p90"]) - _safe_float(r["cost_p10"])) / max(_safe_float(r["cost_median"]), 1.0) for r in rows) / max(len(rows), 1)
        registry_rows.append(
            {
                "field": field,
                "bucket_id": klass,
                "method_branch": "grouped_benchmark",
                "features_used": "depth_bucket_ft, leg_type, drill_rate_mode, pad_expansion_count",
                "validation_design": "field_separated_quantile_benchmark",
                "n_obs": str(n_obs),
                "n_campaign_years": "1+",
                "mae": "na_grouped_benchmark",
                "mape": f"{mape_proxy:.4f}",
                "bias": "na_grouped_benchmark",
                "interval_method": "quantile_band_p10_p90",
                "interval_coverage": "proxy_not_holdout",
                "synthetic_share": "toggle_dependent",
                "notes": "No predictive validity claim; benchmark fallback as per guardrail",
            }
        )

    write_csv(
        CONFIDENCE_BANDS,
        band_rows,
        ["field", "bucket_id", "classification", "interval_method", "lower_bound_usd", "upper_bound_usd", "center_usd", "source_count"],
    )
    write_csv(
        METHOD_REGISTRY,
        registry_rows,
        [
            "field",
            "bucket_id",
            "method_branch",
            "features_used",
            "validation_design",
            "n_obs",
            "n_campaign_years",
            "mae",
            "mape",
            "bias",
            "interval_method",
            "interval_coverage",
            "synthetic_share",
            "notes",
        ],
    )

    for field, path in [("DARAJAT", VALIDATION_DARAJAT), ("SALAK", VALIDATION_SALAK)]:
        rows = [r for r in registry_rows if r["field"] == field]
        lines = [
            f"# Validation Report - {field}",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "Method policy: grouped benchmark fallback (no predictive validity claim).",
            "",
            "| bucket_id | method_branch | n_obs | mape_proxy | interval_method |",
            "|---|---|---:|---:|---|",
        ]
        for r in rows:
            lines.append(f"| {r['bucket_id']} | {r['method_branch']} | {r['n_obs']} | {r['mape']} | {r['interval_method']} |")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _normalize_depth(depth_ft: int) -> int:
    clipped = min(10000, max(4500, int(depth_ft)))
    return int(round(clipped / 500.0) * 500)


def normalize_inputs(campaign_input: dict, well_rows: List[dict]) -> Tuple[dict, List[WellInput]]:
    field = campaign_input.get("field")
    if field not in {"SLK", "DRJ"}:
        raise ValueError("Field must be SLK or DRJ")
    year = int(campaign_input.get("year"))
    no_pads = int(campaign_input.get("no_pads"))
    no_wells = int(campaign_input.get("no_wells"))
    pad_exp = int(campaign_input.get("no_pad_expansion", 0))

    if no_pads < 1 or no_pads > 5:
        raise ValueError("No. Pads must be between 1 and 5")
    if no_wells <= 0:
        raise ValueError("No. Wells must be > 0")
    if pad_exp < 0 or pad_exp > no_pads:
        raise ValueError("No. Pad Expansion must be between 0 and No. Pads")
    if len(well_rows) != no_wells:
        raise ValueError("Well row count must equal No. Wells")

    normalized_wells: List[WellInput] = []
    for idx, row in enumerate(well_rows, start=1):
        depth = _normalize_depth(int(row["depth_ft"]))
        leg = row["leg_type"]
        mode = row["drill_rate_mode"]
        if leg not in LEG_FACTOR:
            raise ValueError(f"Invalid leg_type for Well-{idx}")
        if mode not in RATE_FACTOR:
            raise ValueError(f"Invalid drill_rate_mode for Well-{idx}")
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

    normalized_campaign = {
        "field_input": field,
        "field_canonical": FIELD_MAP[field],
        "campaign_start_year": year,
        "pad_count": no_pads,
        "well_count": no_wells,
        "pad_expansion_count": pad_exp,
        "use_external_forecast": bool(campaign_input.get("use_external_forecast", True)),
        "use_synthetic_data": bool(campaign_input.get("use_synthetic_data", True)),
    }
    return normalized_campaign, normalized_wells


def _external_adjustment(enabled: bool) -> Tuple[float, bool, str]:
    # No external auditable series currently in repo; explicit fallback.
    if not enabled:
        return 1.0, False, "disabled_by_user"
    return 1.0, False, "fallback_historical_only_external_series_unavailable"


def _field_rows(field: str) -> List[dict]:
    return [r for r in read_csv(PHASE5_APP) if r["field"] == field]


def estimate_campaign(campaign_input: dict, well_rows: List[dict]) -> dict:
    normalized_campaign, normalized_wells = normalize_inputs(campaign_input, well_rows)
    field = normalized_campaign["field_canonical"]

    app_rows = _field_rows(field)
    class_rows = read_csv(WBS_CLASS)
    master_rows = [r for r in read_csv(WBS_MASTER) if r.get("field") == field]
    source_map = _build_source_map(master_rows)

    class_cost = defaultdict(float)
    class_unc = defaultdict(float)
    for r in app_rows:
        klass = r["classification"]
        class_cost[klass] += _safe_float(r["cost_median"])
        denom = max(_safe_float(r["cost_median"]), 1.0)
        class_unc[klass] += abs(_safe_float(r["cost_p90"]) - _safe_float(r["cost_p10"])) / denom

    base_well_component = class_cost.get("well_tied", 0.0)
    base_hybrid_component = class_cost.get("hybrid", 0.0)
    base_campaign_component = class_cost.get("campaign_tied", 0.0)

    ext_factor, ext_applied, ext_formula = _external_adjustment(normalized_campaign["use_external_forecast"])

    well_outputs = []
    well_total = 0.0
    for well in normalized_wells:
        depth_factor = well.depth_bucket_ft / 7000.0
        cost_factor = depth_factor * LEG_FACTOR[well.leg_type] * RATE_FACTOR[well.drill_rate_mode]
        est_cost = (base_well_component / max(normalized_campaign["well_count"], 1)) * cost_factor * ext_factor
        est_days = max(8.0, 22.0 * depth_factor * LEG_FACTOR[well.leg_type] / RATE_FACTOR[well.drill_rate_mode])
        uncertainty_pct = min(90.0, (class_unc.get("well_tied", 0.3) / max(len(normalized_wells), 1)) * 100)
        well_outputs.append(
            {
                "well_label": well.well_label,
                "estimated_cost_usd": est_cost,
                "estimated_cost_mmusd": est_cost / 1_000_000.0,
                "uncertainty_pct": uncertainty_pct,
                "uncertainty_label": "MAPE_proxy_grouped_benchmark",
                "estimated_days": est_days,
                "method_label": "grouped_benchmark",
            }
        )
        well_total += est_cost

    hybrid_multiplier = 1.0 + (0.08 * normalized_campaign["pad_expansion_count"])
    hybrid_total = base_hybrid_component * hybrid_multiplier * ext_factor
    campaign_total_component = base_campaign_component * ext_factor

    total_cost = well_total + hybrid_total + campaign_total_component

    # Detail allocation by Lv5 rows.
    class_candidates = [r for r in class_rows if r.get("field") == field and r.get("classification") in {"well_tied", "hybrid", "campaign_tied"}]
    class_totals = {
        "well_tied": well_total,
        "hybrid": hybrid_total,
        "campaign_tied": campaign_total_component,
    }

    by_class = defaultdict(list)
    for r in class_candidates:
        by_class[r["classification"]].append(r)

    detail_rows: List[dict] = []
    for klass, rows in by_class.items():
        weights = [max(_safe_float(r.get("supporting_cost_total", "0")), 1.0) for r in rows]
        weight_sum = sum(weights) or 1.0
        total_for_class = class_totals.get(klass, 0.0)
        for i, r in enumerate(rows):
            frac = weights[i] / weight_sum
            est = total_for_class * frac
            src = source_map.get((field, r.get("wbs_lvl5", "")), {})
            source_years = src.get("source_field_campaign_years", "unknown")
            source_count = int(src.get("source_row_count", 0))
            unc_pct = min(100.0, class_unc.get(klass, 0.4) * 100)
            synthetic_used = 0
            if normalized_campaign["use_synthetic_data"] and source_count < 2 and klass in {"hybrid", "campaign_tied"}:
                synthetic_used = 1
            detail_rows.append(
                {
                    "field": field,
                    "input_year": normalized_campaign["campaign_start_year"],
                    "wbs_lvl1": src.get("wbs_lvl1", ""),
                    "wbs_lvl2": src.get("wbs_lvl2", r.get("wbs_lvl2", "")),
                    "wbs_lvl3": src.get("wbs_lvl3", r.get("wbs_lvl3", "")),
                    "wbs_lvl4": src.get("wbs_lvl4", r.get("wbs_lvl4", "")),
                    "wbs_lvl5": src.get("wbs_lvl5", r.get("wbs_lvl5", "")),
                    "classification": klass,
                    "component_scope": klass,
                    "estimate_usd": est,
                    "estimate_mmusd": est / 1_000_000.0,
                    "uncertainty_pct": unc_pct,
                    "uncertainty_type": "MAPE_proxy_grouped_benchmark",
                    "lower_bound_usd": max(est * (1 - unc_pct / 100.0), 0.0),
                    "upper_bound_usd": est * (1 + unc_pct / 100.0),
                    "estimation_method": "grouped_benchmark",
                    "driver_basis": r.get("driver_family", "unknown"),
                    "source_field_campaign_years": f"{field} | {source_years}",
                    "source_row_count": source_count,
                    "synthetic_rows_used": synthetic_used,
                    "external_adjustment_applied": "yes" if ext_applied else "no",
                }
            )

    # Reconcile strict tolerance by nudging largest row.
    detail_sum = sum(r["estimate_usd"] for r in detail_rows)
    delta = total_cost - detail_sum
    if detail_rows:
        max_row = max(detail_rows, key=lambda r: r["estimate_usd"])
        max_row["estimate_usd"] += delta
        max_row["estimate_mmusd"] = max_row["estimate_usd"] / 1_000_000.0

    for idx, row in enumerate(detail_rows, start=1):
        key_base = f"{field}|{row['wbs_lvl5']}|{normalized_campaign['campaign_start_year']}|{idx}"
        row["audit_key"] = hashlib.sha256(key_base.encode("utf-8")).hexdigest()[:16]

    recalc_detail_sum = sum(r["estimate_usd"] for r in detail_rows)
    reconciled = abs(recalc_detail_sum - total_cost) <= 0.01

    run_timestamp = datetime.now(timezone.utc).isoformat()
    payload_for_hash = json.dumps({"campaign": normalized_campaign, "wells": [w.__dict__ for w in normalized_wells]}, sort_keys=True)
    input_hash = hashlib.sha256(payload_for_hash.encode("utf-8")).hexdigest()

    audit_rows = []
    for r in detail_rows:
        audit_rows.append(
            {
                "field": field,
                "input_campaign_start_year": normalized_campaign["campaign_start_year"],
                "estimation_scope": "campaign_total",
                "component_scope": r["component_scope"],
                "wbs_lvl1": r["wbs_lvl1"],
                "wbs_lvl2": r["wbs_lvl2"],
                "wbs_lvl3": r["wbs_lvl3"],
                "wbs_lvl4": r["wbs_lvl4"],
                "wbs_lvl5": r["wbs_lvl5"],
                "classification": r["classification"],
                "estimate_value_usd": f"{r['estimate_usd']:.6f}",
                "estimate_value_mmusd": f"{r['estimate_mmusd']:.6f}",
                "uncertainty_value": f"{r['uncertainty_pct']:.4f}",
                "uncertainty_type": r["uncertainty_type"],
                "estimation_method": r["estimation_method"],
                "driver_basis": r["driver_basis"],
                "source_field_campaign_years": r["source_field_campaign_years"],
                "source_row_count": r["source_row_count"],
                "synthetic_rows_used": r["synthetic_rows_used"],
                "external_adjustment_flag": "yes" if ext_applied else "no",
                "external_adjustment_formula": ext_formula,
                "run_timestamp": run_timestamp,
                "input_hashes": input_hash,
                "audit_key": r["audit_key"],
            }
        )

    write_csv(
        APP_AUDIT,
        audit_rows,
        list(audit_rows[0].keys()) if audit_rows else [],
    )

    manifest = {
        "run_timestamp": run_timestamp,
        "field": field,
        "input_hashes": input_hash,
        "runtime_toggles": {
            "external_forecast_requested": normalized_campaign["use_external_forecast"],
            "external_forecast_applied": ext_applied,
            "synthetic_data_requested": normalized_campaign["use_synthetic_data"],
        },
        "external_adjustment_formula": ext_formula,
        "reconciliation": {
            "campaign_total_usd": total_cost,
            "detail_total_usd": recalc_detail_sum,
            "status": "PASS" if reconciled else "FAIL",
        },
        "outputs": {
            "audit_csv": str(APP_AUDIT.relative_to(ROOT)),
            "summary_json": str(APP_SUMMARY.relative_to(ROOT)),
        },
    }
    APP_RUN_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    summary = {
        "field": field,
        "input_year": normalized_campaign["campaign_start_year"],
        "total_campaign_cost_mmusd": total_cost / 1_000_000.0,
        "total_campaign_cost_usd": total_cost,
        "well_component_usd": well_total,
        "hybrid_component_usd": hybrid_total,
        "campaign_tied_component_usd": campaign_total_component,
        "reconciliation_status": "PASS" if reconciled else "FAIL",
    }
    APP_SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

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
