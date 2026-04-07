from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.components.calculator_tab import render_calculator_results
from src.app.components.detail_tab import render_detail_tab
from src.app.components.input_panel import render_campaign_panel, render_runtime_toggles, render_well_inputs
from src.modeling.phase5_estimation_core import build_validation_artifacts, estimate_campaign


def main() -> None:
    st.set_page_config(page_title="Drilling Campaign Cost Estimator", layout="wide")
    st.markdown("# DRILLING CAMPAIGN COST ESTIMATOR")

    campaign_input = render_campaign_panel()

    tab_calc, tab_detail = st.tabs(["CALCULATOR", "DETAIL WBS ESTIMATOR"])

    with tab_calc:
        toggles = render_runtime_toggles()
        campaign_input.update(toggles)
        well_rows = render_well_inputs(campaign_input["no_wells"], campaign_input["no_pads"])

        if st.button("CALCULATE DRILLING COST", type="primary"):
            try:
                build_validation_artifacts()
                result = estimate_campaign(campaign_input, well_rows)
                st.session_state["last_result"] = result
            except Exception as exc:
                st.error(f"Validation failed: {exc}")
                return

        if st.session_state.get("last_result"):
            render_calculator_results(st.session_state["last_result"])

    with tab_detail:
        if st.session_state.get("last_result"):
            render_detail_tab(st.session_state["last_result"])
        else:
            st.info("Run calculation first to view detail WBS estimator.")


if __name__ == "__main__":
    main()
