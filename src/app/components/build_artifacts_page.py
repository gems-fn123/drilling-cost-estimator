"""Build Artifacts page – runs the ETL pipeline from dashboard workbook only."""

from __future__ import annotations

import traceback
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
DASHBOARD_WORKBOOK_NAME = "20260422_Data for Dashboard.xlsx"


def _dashboard_workbook_path() -> Path:
    return RAW_DIR / DASHBOARD_WORKBOOK_NAME


def render_build_artifacts_page() -> None:
    st.markdown("# BUILD MODELLING ARTIFACTS")
    st.markdown(
        "Refresh all estimator artifacts from the dashboard workbook. "
        "This pipeline no longer depends on legacy multi-workbook inputs."
    )

    workbook_path = _dashboard_workbook_path()
    if not workbook_path.exists():
        st.warning(
            f"Dashboard workbook not found at `{workbook_path}`. "
            "Go to **Upload Data** and load the workbook first."
        )
        return

    st.subheader("Raw Input")
    size_kb = workbook_path.stat().st_size / 1024
    st.text(f"{workbook_path.name} ({size_kb:.1f} KB)")

    processed_files = sorted(PROCESSED.glob("*")) if PROCESSED.exists() else []
    artifact_count = len([f for f in processed_files if f.is_file()])
    if artifact_count > 0:
        st.info(f"Found {artifact_count} existing processed artifacts. Rebuild will overwrite refreshed outputs.")

    st.divider()

    st.subheader("Pipeline Configuration")
    col1, col2 = st.columns(2)
    with col1:
        group_by = st.selectbox("Group By", ["family", "lv5"], index=0, key="etl_group_by")
    with col2:
        use_synthetic = st.checkbox("Use Synthetic Data", value=False, key="etl_use_synthetic")

    st.divider()

    if st.button("BUILD ARTIFACTS", type="primary"):
        progress_bar = st.progress(0, text="Initializing pipeline...")
        status_container = st.empty()

        try:
            progress_bar.progress(15, text="Building canonical mappings...")
            from src.io.build_canonical_mappings import main as build_canonical_mappings

            build_canonical_mappings()

            progress_bar.progress(30, text="Building unit price history...")
            from src.modeling.unit_price_history_pipeline import main as build_unit_price_history

            build_unit_price_history()

            progress_bar.progress(45, text="Running unit price analysis...")
            from src.modeling.unit_price_well_analysis import main as build_unit_price_well

            build_unit_price_well()

            progress_bar.progress(58, text="Running macro analysis...")
            from src.modeling.unit_price_macro_analysis import main as build_macro

            build_macro()

            progress_bar.progress(70, text="Building WBS tree...")
            from src.modeling.wbs_tree_diagram import build_wbs_tree_artifacts

            build_wbs_tree_artifacts()

            progress_bar.progress(80, text="Running phase 4 preflight...")
            from src.modeling.phase4_preflight_and_baseline import run_phase4

            run_phase4(group_by=group_by, use_synthetic=use_synthetic, synthetic_policy="training")

            progress_bar.progress(90, text="Building validation artifacts...")
            from src.modeling.phase5_estimation_core import build_validation_artifacts

            build_validation_artifacts(refresh_pipeline=False)

            progress_bar.progress(96, text="Building operational assets...")
            from src.app.build_phase5_operational_assets import main as build_ops

            build_ops()

            progress_bar.progress(100, text="Pipeline complete")
            st.session_state["artifacts_built"] = True
            status_container.success("All modelling artifacts refreshed from dashboard workbook. Proceed to **WBS Tree** or **Modelling**.")

        except Exception as exc:
            progress_bar.progress(100, text="Pipeline failed")
            status_container.error(f"Pipeline error: {exc}")
            with st.expander("Full traceback"):
                st.code(traceback.format_exc())

    if PROCESSED.exists():
        processed_files = sorted(PROCESSED.glob("*"))
        artifact_count = len([f for f in processed_files if f.is_file()])
        if artifact_count > 0:
            with st.expander(f"Processed artifacts ({artifact_count} files)"):
                for file_path in processed_files:
                    if file_path.is_file():
                        size_kb = file_path.stat().st_size / 1024
                        st.text(f"{file_path.name} ({size_kb:.1f} KB)")
