from __future__ import annotations

import csv
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"

SUMMARY_PATH = PROCESSED / "dashboard_x_summary_metrics.csv"
WELL_PATH = PROCESSED / "dashboard_x_cost_by_well.csv"
L3_PATH = PROCESSED / "dashboard_x_l3_breakdown.csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(value: str) -> float:
    try:
        return float((value or "0").replace(",", ""))
    except ValueError:
        return 0.0


def render_dashboard_tab() -> None:
    st.subheader("HISTORICAL DASHBOARD SNAPSHOT")

    summary_rows = _read_csv(SUMMARY_PATH)
    well_rows = _read_csv(WELL_PATH)
    l3_rows = _read_csv(L3_PATH)

    if not summary_rows and not well_rows and not l3_rows:
        st.info("Run the alignment refresh to generate dashboard snapshot artifacts.")
        return

    summary_map = {row["metric_name"]: row["metric_value"] for row in summary_rows}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Budget", summary_map.get("Total Budget (USD)", "n/a"))
    c2.metric("Total Actual", summary_map.get("Total Actual (USD)", "n/a"))
    c3.metric("Utilization", summary_map.get("Budget Utilization %", "n/a"))
    c4.metric("Remaining Budget", summary_map.get("Remaining Budget", "n/a"))

    st.caption(f"Source sheet: Dashboard_x | summary rows: {len(summary_rows)} | well rows: {len(well_rows)} | L3 rows: {len(l3_rows)}")

    if well_rows:
        st.markdown("### Cost By Well")
        ordered_wells = sorted(well_rows, key=lambda row: _as_float(row.get("actual_usd", "0")), reverse=True)
        st.dataframe(ordered_wells, use_container_width=True, hide_index=True)

    if l3_rows:
        st.markdown("### L3 Breakdown")
        ordered_l3 = sorted(l3_rows, key=lambda row: _as_float(row.get("actual_usd", "0")), reverse=True)
        st.dataframe(ordered_l3, use_container_width=True, hide_index=True)

    with st.expander("Dashboard Snapshot Metadata"):
        st.dataframe(summary_rows, use_container_width=True, hide_index=True)
