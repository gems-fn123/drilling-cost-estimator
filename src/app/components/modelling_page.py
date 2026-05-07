"""Estimator page – the main estimation interface (current stable feature)."""

from __future__ import annotations

import streamlit as st

from src.app.components.calculator_tab import render_calculator_results
from src.app.components.input_panel import render_campaign_panel, render_well_inputs
from src.modeling.phase5_estimation_core import build_validation_artifacts, estimate_campaign


def render_modelling_page() -> None:
    st.markdown("# DRILLING CAMPAIGN ESTIMATOR")

    campaign_input = render_campaign_panel()
    campaign_input.update({"use_external_forecast": True, "use_synthetic_data": False})
    st.caption("Defaults: external forecast enabled; synthetic data disabled.")
    well_rows = render_well_inputs(campaign_input["no_wells"], campaign_input["no_pads"], field=campaign_input["field"])

    if st.button("CALCULATE DRILLING COST", type="primary"):
        try:
            build_validation_artifacts(refresh_pipeline=False)
            result = estimate_campaign(campaign_input, well_rows)
            st.session_state["last_result"] = result
        except Exception as exc:
            st.error(f"Estimation failed: {exc}")
            return

    if st.session_state.get("last_result"):
        render_calculator_results(st.session_state["last_result"])
