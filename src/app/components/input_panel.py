from __future__ import annotations

import csv
from statistics import mean, median
from typing import List

import streamlit as st

from src.modeling.phase5_estimation_core import RATE_FACTOR
from src.modeling.unit_price_well_analysis import SERVICE_TIME_BANDS


def _load_service_band_rows() -> list[dict[str, str]]:
    if not SERVICE_TIME_BANDS.exists():
        return []
    with SERVICE_TIME_BANDS.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _format_depth(value: float) -> str:
    return f"{value:,.0f} ft"


def _render_service_pace_explainer(field: str | None) -> None:
    st.caption(
        f"Fast multiplies the active-day component by {RATE_FACTOR['Fast']:.2f}, Standard is {RATE_FACTOR['Standard']:.2f}, and Careful is {RATE_FACTOR['Careful']:.2f}. "
        "The field bands below come from historical active-operational-days per 1000 ft terciles."
    )
    rows = _load_service_band_rows()
    if not rows:
        st.info("Service pace bands will appear after the build artifacts run and service_time_band_reference.csv is present.")
        return

    display_rows = [
        {
            "field": row.get("field", ""),
            "fast_rule": row.get("fast_rule", ""),
            "standard_rule": row.get("standard_rule", ""),
            "careful_rule": row.get("careful_rule", ""),
            "observation_count": row.get("observation_count", ""),
        }
        for row in rows
    ]
    if field:
        normalized_field = field.upper().strip()
        filtered = [row for row in display_rows if row["field"].upper() == normalized_field]
        if filtered:
            display_rows = filtered

    st.dataframe(display_rows, width="stretch", hide_index=True)


def render_campaign_panel() -> dict:
    st.sidebar.header("Campaign Inputs")
    year = st.sidebar.number_input("Year", min_value=2018, max_value=2035, value=2026, step=1)
    field = st.sidebar.selectbox("Field", ["SLK", "DRJ", "WW"], index=0)
    no_pads = st.sidebar.number_input("No. Pads", min_value=1, max_value=5, value=2, step=1)
    no_wells = st.sidebar.number_input("No. Wells", min_value=1, max_value=20, value=3, step=1)
    no_pad_expansion = st.sidebar.number_input("No. Pad Expansion", min_value=0, max_value=int(no_pads), value=0, step=1)

    return {
        "year": int(year),
        "field": field,
        "no_pads": int(no_pads),
        "no_wells": int(no_wells),
        "no_pad_expansion": int(no_pad_expansion),
    }


def render_well_inputs(no_wells: int, no_pads: int, field: str | None = None) -> List[dict]:
    st.subheader("Individual Well Parameters")
    st.caption("Complexity split is disabled on this branch; all new estimated wells are treated as Standard-J.")
    options = [f"Pad-{idx}" for idx in range(1, no_pads + 1)]
    rows: List[dict] = []
    for idx in range(1, no_wells + 1):
        st.markdown(f"**Well-{idx}**")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            pad_label = st.selectbox("Pad", options, key=f"pad_{idx}")
        with c2:
            depth_ft = st.select_slider(
                "Depth",
                options=list(range(4500, 10001, 500)),
                value=7000,
                key=f"depth_{idx}",
            )
        with c3:
            drill_rate_mode = st.selectbox("Service Pace", ["Standard", "Fast", "Careful"], key=f"rate_{idx}")

        rows.append(
            {
                "well_label": f"Well-{idx}",
                "pad_label": pad_label,
                "depth_ft": int(depth_ft),
                "leg_type": "Standard-J",
                "drill_rate_mode": drill_rate_mode,
            }
        )

    if rows:
        depths = [row["depth_ft"] for row in rows]
        pace_counts = {mode: sum(1 for row in rows if row["drill_rate_mode"] == mode) for mode in ["Fast", "Standard", "Careful"]}
        st.markdown("**Loaded well depth snapshot**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Wells", len(rows))
        c2.metric("Min depth", _format_depth(min(depths)))
        c3.metric("Median depth", _format_depth(median(depths)))
        c4.metric("Mean depth", _format_depth(mean(depths)))
        st.caption(
            f"Max depth: {_format_depth(max(depths))} | Pace mix: Fast {pace_counts['Fast']}, Standard {pace_counts['Standard']}, Careful {pace_counts['Careful']}"
        )

    with st.expander("Service pace guide", expanded=False):
        _render_service_pace_explainer(field)

    return rows
