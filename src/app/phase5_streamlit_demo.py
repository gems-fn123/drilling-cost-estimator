#!/usr/bin/env python3
"""Phase 5 Streamlit demo shell for design review.

This is intentionally a review-ready prototype scaffold, not a production app.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[2]
APP_DATASET = ROOT / "data" / "processed" / "phase5_app_dataset.csv"
KPI_DATASET = ROOT / "data" / "processed" / "phase5_monitoring_kpis.csv"


def _read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_data() -> Tuple[List[dict], List[dict]]:
    return _read_csv(APP_DATASET), _read_csv(KPI_DATASET)


def filter_field(app_rows: List[dict], kpi_rows: List[dict], field: str) -> Tuple[List[dict], List[dict]]:
    return [r for r in app_rows if r.get("field") == field], [r for r in kpi_rows if r.get("field") == field]


def render() -> None:
    import streamlit as st

    st.set_page_config(page_title="Phase 5 Cost Estimator Demo", layout="wide")
    st.title("Phase 5 Demo - Drilling Cost Estimator")
    st.caption("Design review scaffold using Phase 5 operational assets.")

    app_rows, kpi_rows = load_data()
    fields = sorted({r["field"] for r in app_rows})
    selected_field = st.selectbox("Field", fields, index=0)

    field_app_rows, field_kpi_rows = filter_field(app_rows, kpi_rows, selected_field)
    kpi = field_kpi_rows[0] if field_kpi_rows else {"kpi_ready_share_pct": "n/a", "kpi_hard_gate_failures": "n/a"}

    col1, col2, col3 = st.columns(3)
    col1.metric("Groups", len(field_app_rows))
    col2.metric("Ready share (%)", kpi["kpi_ready_share_pct"])
    col3.metric("Hard gate failures", kpi["kpi_hard_gate_failures"])

    st.subheader("Estimator Group View")
    st.dataframe(
        [
            {
                "group_key": r["group_key"],
                "classification": r["classification"],
                "driver_family": r["driver_family"],
                "sample_size": r["sample_size"],
                "cost_p10": r["cost_p10"],
                "cost_median": r["cost_median"],
                "cost_p90": r["cost_p90"],
                "confidence_tier": r["confidence_tier"],
                "estimator_readiness": r["estimator_readiness"],
            }
            for r in field_app_rows
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Scenario Controls (design-only)")
    depth_delta = st.slider("Depth adjustment (%)", -20, 20, 0)
    operation_mode = st.selectbox("Operation mode", ["base", "accelerated", "conservative"], index=0)
    st.info(
        f"Preview only: depth adjustment={depth_delta}%, mode={operation_mode}. "
        "Scenario engine remains pending validated feature coefficients."
    )

    st.subheader("Known Limits")
    st.warning("G7/G8 remain tracked separately; this demo keeps those caveats visible.")


if __name__ == "__main__":
    render()
