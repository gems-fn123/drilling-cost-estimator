"""Build Artifacts page – runs the ETL pipeline and generates modelling inputs."""

from __future__ import annotations

import traceback
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def _raw_files_present() -> list[Path]:
    """List raw data files currently available."""
    if not RAW_DIR.exists():
        return []
    return sorted(f for f in RAW_DIR.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS)


def _run_etl_pipeline() -> dict:
    """Run the streamlined ETL pipeline to generate all modelling artifacts."""
    from src.modeling.streamlined_etl_pipeline import run_streamlined_etl

    return run_streamlined_etl(
        group_by="family",
        use_synthetic=False,
        synthetic_policy="training",
    )


def render_build_artifacts_page() -> None:
    st.markdown("# BUILD MODELLING ARTIFACTS")
    st.markdown(
        "This step processes uploaded raw data to generate the modelling artifacts "
        "required by the estimation engine."
    )

    raw_files = _raw_files_present()
    if not raw_files:
        st.warning(
            "No raw data files found. Go to **Upload Data** first to load your files."
        )
        return

    st.subheader("Raw Data Files")
    for f in raw_files:
        size_kb = f.stat().st_size / 1024
        st.text(f"  {f.name}  ({size_kb:.1f} KB)")

    st.divider()

    # Pipeline options
    st.subheader("Pipeline Configuration")
    col1, col2 = st.columns(2)
    with col1:
        group_by = st.selectbox("Group By", ["family", "lv5"], index=0, key="etl_group_by")
    with col2:
        use_synthetic = st.checkbox("Use Synthetic Data", value=False, key="etl_use_synthetic")

    st.divider()

    # Run pipeline
    if st.button("BUILD ARTIFACTS", type="primary"):
        progress_bar = st.progress(0, text="Initializing pipeline...")
        status_container = st.empty()

        try:
            progress_bar.progress(10, text="Running canonical mappings...")
            from src.io.build_canonical_mappings import main as build_canonical_mappings
            build_canonical_mappings()

            progress_bar.progress(30, text="Building unit price history...")
            from src.modeling.unit_price_history_pipeline import main as build_unit_price_history
            build_unit_price_history()

            progress_bar.progress(50, text="Running unit price analysis...")
            from src.modeling.unit_price_well_analysis import main as build_unit_price_well
            build_unit_price_well()

            progress_bar.progress(60, text="Running macro analysis...")
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

            progress_bar.progress(95, text="Building operational assets...")
            from src.app.build_phase5_operational_assets import main as build_ops
            build_ops()

            progress_bar.progress(100, text="Pipeline complete!")
            st.session_state["artifacts_built"] = True

            status_container.success(
                "All modelling artifacts built successfully. "
                "Proceed to **WBS Tree** to validate or **Modelling** to estimate."
            )

        except Exception as exc:
            progress_bar.progress(100, text="Pipeline failed.")
            status_container.error(f"Pipeline error: {exc}")
            with st.expander("Full traceback"):
                st.code(traceback.format_exc())

    # Show existing artifacts
    if PROCESSED.exists():
        processed_files = sorted(PROCESSED.glob("*"))
        artifact_count = len([f for f in processed_files if f.is_file()])
        if artifact_count > 0:
            with st.expander(f"Existing processed artifacts ({artifact_count} files)"):
                for f in processed_files:
                    if f.is_file():
                        size_kb = f.stat().st_size / 1024
                        st.text(f"  {f.name}  ({size_kb:.1f} KB)")
