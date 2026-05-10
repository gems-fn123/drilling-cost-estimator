#!/usr/bin/env python3
"""Build Phase 5 operational artifacts for app integration and monitoring.

Outputs:
- data/processed/phase5_app_dataset.csv
- data/processed/phase5_monitoring_kpis.csv
- data/processed/phase5_operational_manifest.json
- reports/phase5_app_integration_prerequisites.md
- reports/phase5_monitoring_skeleton.md
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from src.config import PROCESSED, REPORTS, ROOT
from src.utils import read_csv, relpath, write_csv

log = logging.getLogger(__name__)

BASELINE_DARAJAT = PROCESSED / "baseline_estimates_darajat.csv"
BASELINE_SALAK = PROCESSED / "baseline_estimates_salak.csv"
GATE_RESULTS = PROCESSED / "phase4_gate_results.csv"

APP_DATASET_PATH = PROCESSED / "phase5_app_dataset.csv"
MONITORING_KPI_PATH = PROCESSED / "phase5_monitoring_kpis.csv"
MANIFEST_PATH = PROCESSED / "phase5_operational_manifest.json"

APP_REPORT_PATH = REPORTS / "phase5_app_integration_prerequisites.md"
MONITORING_REPORT_PATH = REPORTS / "phase5_monitoring_skeleton.md"


def load_baseline_rows() -> List[dict]:
    rows: List[dict] = []
    for path in [BASELINE_DARAJAT, BASELINE_SALAK]:
        rows.extend(read_csv(path))
    return rows


def build_app_dataset(baseline_rows: List[dict]) -> List[dict]:
    dataset: List[dict] = []
    for row in baseline_rows:
        readiness = (row.get("estimator_readiness") or "").strip()
        sample_size = int(float(row.get("sample_size") or 0))
        confidence_tier = "high" if readiness == "ready" and sample_size >= 5 else "medium" if sample_size >= 3 else "low"
        dataset.append(
            {
                "field": row["field"],
                "group_key": row["group_key"],
                "classification": row["classification"],
                "driver_family": row["driver_family"],
                "sample_size": str(sample_size),
                "cost_median": row["cost_median"],
                "cost_p10": row["cost_p10"],
                "cost_p90": row["cost_p90"],
                "confidence_tier": confidence_tier,
                "estimator_readiness": readiness,
            }
        )
    dataset.sort(key=lambda r: (r["field"], r["group_key"]))
    return dataset


def build_monitoring_kpis(baseline_rows: List[dict], gate_rows: List[dict]) -> List[dict]:
    grouped: Dict[str, dict] = defaultdict(lambda: {"rows": 0, "ready_rows": 0, "sample_total": 0})

    for row in baseline_rows:
        field = row["field"]
        grouped[field]["rows"] += 1
        grouped[field]["sample_total"] += int(float(row.get("sample_size") or 0))
        if (row.get("estimator_readiness") or "").strip() == "ready":
            grouped[field]["ready_rows"] += 1

    hard_gate_failures = sum(1 for g in gate_rows if g["gate_id"] in {"G1", "G2", "G3", "G4", "G5", "G6"} and g["status"] != "PASS")
    known_limitations = sum(1 for g in gate_rows if g["status"] == "KNOWN LIMITATION")

    now = datetime.now(timezone.utc).isoformat()
    kpis: List[dict] = []
    for field, summary in sorted(grouped.items()):
        rows = summary["rows"] or 1
        kpis.append(
            {
                "snapshot_ts_utc": now,
                "field": field,
                "kpi_ready_share_pct": f"{(summary['ready_rows'] / rows) * 100:.2f}",
                "kpi_avg_sample_size": f"{summary['sample_total'] / rows:.2f}",
                "kpi_hard_gate_failures": str(hard_gate_failures),
                "kpi_known_limitations": str(known_limitations),
            }
        )
    return kpis


def write_reports(app_rows: List[dict], kpi_rows: List[dict]) -> None:
    fields = sorted({row["field"] for row in app_rows})
    app_lines = [
        "# Phase 5 App Integration Prerequisites",
        "",
        "Date: " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "",
        "## Output Contract",
        "- Source artifact: `data/processed/phase5_app_dataset.csv`",
        "- Required columns: `field, group_key, classification, driver_family, sample_size, cost_median, cost_p10, cost_p90, confidence_tier, estimator_readiness`",
        "- Field-specific behavior: app filters are hard-partitioned by `field` so DARAJAT and SALAK are never pooled.",
        "",
        "## UI Prerequisites",
        "1. Field selector defaults to a single field per session.",
        "2. Group table sorts by `group_key` and shows P10/P50/P90 cost bands.",
        "3. Confidence indicator maps `confidence_tier` to badge colors.",
        "4. Records with `estimator_readiness != ready` remain visible but marked as watchlist.",
        "",
        "## Snapshot",
        f"- Fields in current dataset: {', '.join(fields)}",
        f"- Total app rows: {len(app_rows)}",
    ]
    APP_REPORT_PATH.write_text("\n".join(app_lines) + "\n", encoding="utf-8")

    monitor_lines = [
        "# Phase 5 Monitoring Skeleton",
        "",
        "Date: " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "",
        "## KPI Feed",
        "- Source artifact: `data/processed/phase5_monitoring_kpis.csv`",
        "- KPI fields: `kpi_ready_share_pct`, `kpi_avg_sample_size`, `kpi_hard_gate_failures`, `kpi_known_limitations`",
        "",
        "## Alert Rules (initial)",
        "1. Critical: `kpi_hard_gate_failures > 0`",
        "2. Warning: `kpi_ready_share_pct < 60`",
        "3. Warning: `kpi_known_limitations > 2`",
        "",
        "## Current Snapshot",
    ]
    for row in kpi_rows:
        monitor_lines.append(
            "- "
            f"{row['field']}: ready_share={row['kpi_ready_share_pct']}%, "
            f"avg_sample={row['kpi_avg_sample_size']}, "
            f"hard_gate_failures={row['kpi_hard_gate_failures']}, "
            f"known_limitations={row['kpi_known_limitations']}"
        )

    MONITORING_REPORT_PATH.write_text("\n".join(monitor_lines) + "\n", encoding="utf-8")


def write_manifest(app_rows: List[dict], kpi_rows: List[dict]) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "phase5",
        "inputs": [relpath(BASELINE_DARAJAT, ROOT), relpath(BASELINE_SALAK, ROOT), relpath(GATE_RESULTS, ROOT)],
        "outputs": [relpath(APP_DATASET_PATH, ROOT), relpath(MONITORING_KPI_PATH, ROOT), relpath(APP_REPORT_PATH, ROOT), relpath(MONITORING_REPORT_PATH, ROOT)],
        "app_rows": len(app_rows),
        "kpi_rows": len(kpi_rows),
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    baseline_rows = load_baseline_rows()
    gate_rows = read_csv(GATE_RESULTS)

    app_rows = build_app_dataset(baseline_rows)
    kpi_rows = build_monitoring_kpis(baseline_rows, gate_rows)

    write_csv(
        APP_DATASET_PATH,
        app_rows,
        [
            "field",
            "group_key",
            "classification",
            "driver_family",
            "sample_size",
            "cost_median",
            "cost_p10",
            "cost_p90",
            "confidence_tier",
            "estimator_readiness",
        ],
    )
    write_csv(
        MONITORING_KPI_PATH,
        kpi_rows,
        [
            "snapshot_ts_utc",
            "field",
            "kpi_ready_share_pct",
            "kpi_avg_sample_size",
            "kpi_hard_gate_failures",
            "kpi_known_limitations",
        ],
    )

    write_reports(app_rows, kpi_rows)
    write_manifest(app_rows, kpi_rows)


if __name__ == "__main__":
    main()
