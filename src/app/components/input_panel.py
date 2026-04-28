from __future__ import annotations

from typing import List

import streamlit as st


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


def render_runtime_toggles() -> dict:
    col1, col2 = st.columns([1, 1])
    with col1:
        use_external_forecast = st.toggle("EXTN. DATA", value=True)
    with col2:
        use_synthetic_data = st.toggle("SYNTH DATA", value=True)
    return {
        "use_external_forecast": use_external_forecast,
        "use_synthetic_data": use_synthetic_data,
    }


def render_well_inputs(no_wells: int, no_pads: int) -> List[dict]:
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
    return rows
