"""Main Streamlit application – multipage workflow for data upload → estimator."""

from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.components.build_artifacts_page import render_build_artifacts_page
from src.app.components.modelling_page import render_modelling_page
from src.app.components.upload_page import render_upload_page
from src.app.components.wbs_tree_tab import render_wbs_tree_tab


def _page_upload() -> None:
    render_upload_page()


def _page_build_artifacts() -> None:
    render_build_artifacts_page()


def _page_wbs_tree() -> None:
    st.markdown("# WBS TREE VALIDATION")
    st.markdown("Inspect the WBS tree hierarchy built from your uploaded data.")
    render_wbs_tree_tab()


def _page_modelling() -> None:
    render_modelling_page()


def _page_audit() -> None:
    st.markdown("# AUDIT OUTPUT")
    if st.session_state.get("last_result"):
        from src.app.components.detail_tab import render_detail_tab
        render_detail_tab(st.session_state["last_result"])
    else:
        st.info("Run a cost estimation in the **Estimator** page first to view audit outputs.")


def main() -> None:
    st.set_page_config(page_title="Drilling Campaign Cost Estimator", layout="wide")

    pages = {
        "Workflow": [
            st.Page(_page_upload, title="Upload Data", icon="\U0001F4C1"),
            st.Page(_page_build_artifacts, title="Build Artifacts", icon="\u2699\uFE0F"),
            st.Page(_page_wbs_tree, title="WBS Tree", icon="\U0001F333"),
            st.Page(_page_modelling, title="Estimator", icon="\U0001F4CA"),
            st.Page(_page_audit, title="Audit", icon="\U0001F50D"),
        ]
    }

    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
