#!/usr/bin/env python3
"""Streamlined ETL + estimator endpoint for frontend handover."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from src.app.build_phase5_operational_assets import APP_DATASET_PATH, MONITORING_KPI_PATH
from src.modeling.dashboard_historical_mart import HISTORICAL_MART
from src.modeling.phase4_preflight_and_baseline import BASELINE_DARAJAT_PATH, BASELINE_SALAK_PATH, GATE_RESULTS_PATH
from src.modeling.phase5_estimation_core import (
    APP_AUDIT,
    APP_RUN_MANIFEST,
    APP_SUMMARY,
    CONFIDENCE_BANDS,
    METHOD_REGISTRY,
    build_validation_artifacts,
    estimate_campaign,
)
from src.modeling.unit_price_macro_analysis import (
    MACRO_CLUSTER_WEIGHTS_PATH,
    MACRO_FACTORS_PATH,
    MACRO_REPORT_PATH,
    MACRO_WEIGHTS_PATH,
    main as build_unit_price_macro_analysis,
)
from src.modeling.unit_price_npt_analysis import NPT_CONTRIBUTION_SUMMARY, NPT_PENALTY_REFERENCE
from src.modeling.unit_price_well_analysis import SERVICE_TIME_BANDS, UNIT_PRICE_BENCHMARK, UNIT_PRICE_WELL_PROFILE
from src.modeling.wbs_tree_diagram import (
    WBS_TREE_COMBINED_JSON,
    WBS_TREE_DARAJAT_JSON,
    WBS_TREE_HTML,
    WBS_TREE_REPORT,
    WBS_TREE_SALAK_JSON,
    WBS_TREE_WW_JSON,
    build_wbs_tree_artifacts,
)

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"

PIPELINE_MANIFEST_PATH = PROCESSED / "etl_pipeline_manifest.json"
PIPELINE_ENDPOINT_OUTPUT_PATH = PROCESSED / "etl_pipeline_endpoint_output.json"


def _relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _read_csv_rows(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _artifact_entry(path: Path) -> dict:
    entry = {
        "path": _relpath(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }
    if path.exists() and path.suffix.lower() == ".csv":
        entry["row_count"] = len(_read_csv_rows(path))
    return entry


def _ensure_unit_price_macro_outputs() -> None:
    required = [MACRO_FACTORS_PATH, MACRO_WEIGHTS_PATH, MACRO_CLUSTER_WEIGHTS_PATH, MACRO_REPORT_PATH]
    if not all(path.exists() for path in required):
        build_unit_price_macro_analysis()


def run_streamlined_etl(
    *,
    group_by: str = "family",
    use_synthetic: bool = False,
    synthetic_policy: str = "training",
) -> dict:
    validation_summary = build_validation_artifacts(
        refresh_pipeline=True,
        group_by=group_by,
        use_synthetic=use_synthetic,
        synthetic_policy=synthetic_policy,
    )
    wbs_tree_summary = build_wbs_tree_artifacts()
    _ensure_unit_price_macro_outputs()

    artifacts = [
        HISTORICAL_MART,
        GATE_RESULTS_PATH,
        BASELINE_DARAJAT_PATH,
        BASELINE_SALAK_PATH,
        APP_DATASET_PATH,
        MONITORING_KPI_PATH,
        CONFIDENCE_BANDS,
        METHOD_REGISTRY,
        APP_AUDIT,
        APP_SUMMARY,
        APP_RUN_MANIFEST,
        UNIT_PRICE_WELL_PROFILE,
        UNIT_PRICE_BENCHMARK,
        SERVICE_TIME_BANDS,
        MACRO_FACTORS_PATH,
        MACRO_WEIGHTS_PATH,
        MACRO_CLUSTER_WEIGHTS_PATH,
        MACRO_REPORT_PATH,
        NPT_CONTRIBUTION_SUMMARY,
        NPT_PENALTY_REFERENCE,
        WBS_TREE_COMBINED_JSON,
        WBS_TREE_DARAJAT_JSON,
        WBS_TREE_SALAK_JSON,
        WBS_TREE_WW_JSON,
        WBS_TREE_HTML,
        WBS_TREE_REPORT,
    ]

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": "streamlined_etl_v1",
        "runtime_toggles": {
            "group_by": group_by,
            "use_synthetic": use_synthetic,
            "synthetic_policy": synthetic_policy if use_synthetic else "not_applied",
        },
        "field_partition_rule": "DARAJAT, SALAK, and WAYANG_WINDU are processed independently and never pooled.",
        "validation_summary": validation_summary,
        "wbs_tree_summary": wbs_tree_summary,
        "artifacts": [_artifact_entry(path) for path in artifacts],
    }
    _write_json(PIPELINE_MANIFEST_PATH, payload)
    return payload


def run_pipeline_endpoint(
    campaign_input: dict,
    well_rows: List[dict],
    *,
    refresh_pipeline: bool = True,
    group_by: str = "family",
    use_synthetic: bool = False,
    synthetic_policy: str = "training",
) -> dict:
    if refresh_pipeline:
        run_streamlined_etl(
            group_by=group_by,
            use_synthetic=use_synthetic,
            synthetic_policy=synthetic_policy,
        )

    result = estimate_campaign(campaign_input, well_rows)
    payload = {
        **result,
        "pipeline_manifest_path": _relpath(PIPELINE_MANIFEST_PATH),
    }
    _write_json(PIPELINE_ENDPOINT_OUTPUT_PATH, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run streamlined ETL and optional estimator endpoint output.")
    parser.add_argument("--refresh-only", action="store_true", help="Run ETL refresh only and stop.")
    parser.add_argument(
        "--request-json",
        type=Path,
        help="Path to JSON payload with keys: campaign_input, well_rows.",
    )
    parser.add_argument("--skip-refresh", action="store_true", help="Skip ETL refresh and use existing processed artifacts.")
    parser.add_argument("--group-by", choices=["family", "lv5"], default="family")
    parser.add_argument("--use-synthetic", action="store_true")
    parser.add_argument("--synthetic-policy", choices=["training", "all"], default="training")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PIPELINE_ENDPOINT_OUTPUT_PATH,
        help="Optional output path for CLI result payload.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.refresh_only:
        payload = run_streamlined_etl(
            group_by=args.group_by,
            use_synthetic=args.use_synthetic,
            synthetic_policy=args.synthetic_policy,
        )
        _write_json(args.output_json, payload)
        print(f"Wrote ETL manifest: {args.output_json}")
        return

    if args.request_json is None:
        raise SystemExit("--request-json is required unless --refresh-only is used.")

    request = json.loads(args.request_json.read_text(encoding="utf-8"))
    if "campaign_input" not in request or "well_rows" not in request:
        raise SystemExit("Request JSON must contain 'campaign_input' and 'well_rows'.")

    payload = run_pipeline_endpoint(
        request["campaign_input"],
        request["well_rows"],
        refresh_pipeline=not args.skip_refresh,
        group_by=args.group_by,
        use_synthetic=args.use_synthetic,
        synthetic_policy=args.synthetic_policy,
    )
    _write_json(args.output_json, payload)
    print(f"Wrote endpoint payload: {args.output_json}")


if __name__ == "__main__":
    main()
