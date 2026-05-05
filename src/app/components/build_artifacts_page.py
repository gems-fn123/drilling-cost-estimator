"""Build Artifacts page – runs the ETL pipeline from dashboard workbook only."""

from __future__ import annotations

import csv
import importlib
import sys
import traceback
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
DASHBOARD_WORKBOOK_NAME = "20260422_Data for Dashboard.xlsx"
SYNTHETIC_CAMPAIGN_PATH = PROCESSED / "synthetic_campaign_placeholders.csv"
SYNTHETIC_LV5_PATH = PROCESSED / "synthetic_wbs_lv5_placeholders.csv"
MACRO_WEIGHTS_PATH = PROCESSED / "unit_price_macro_weights.csv"
MACRO_CLUSTER_WEIGHTS_PATH = PROCESSED / "unit_price_macro_cluster_weights.csv"


def _dashboard_workbook_path() -> Path:
    return RAW_DIR / DASHBOARD_WORKBOOK_NAME


def _load_fresh_module(module_name: str):
    was_loaded = module_name in sys.modules
    module = importlib.import_module(module_name)
    if was_loaded:
        module = importlib.reload(module)
    return module


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(value: str) -> float:
    try:
        return float(str(value or "0").replace(",", ""))
    except ValueError:
        return 0.0


def _top_rows(rows: list[dict[str, str]], *, limit: int = 5) -> list[dict[str, str]]:
    return sorted(
        rows,
        key=lambda row: (
            _as_float(row.get("forecast_weight", "0")),
            _as_float(row.get("abs_nominal_correlation", "0")),
        ),
        reverse=True,
    )[:limit]


def _render_synthetic_explainer() -> None:
    with st.expander("What the optional synthetic data is", expanded=False):
        st.markdown(
            "Synthetic rows are placeholder campaign and Lv.5 rows generated from nearest same-field historical templates. "
            "They are marked `include_for_training = no` and `include_for_validation = no`, so they stay outside the default refresh path. "
            "Keep the toggle off for normal estimator runs; turn it on only when you want gap-fill or sensitivity coverage while history is thin."
        )
        campaign_rows = _read_csv_rows(SYNTHETIC_CAMPAIGN_PATH)
        if campaign_rows:
            st.dataframe(
                [
                    {
                        "synthetic_campaign_id": row.get("synthetic_campaign_id", ""),
                        "field": row.get("field", ""),
                        "target_year": row.get("synthetic_target_year", ""),
                        "base_campaign": row.get("synthetic_base_campaign", ""),
                        "include_for_training": row.get("include_for_training", ""),
                    }
                    for row in campaign_rows
                ],
                width="stretch",
                hide_index=True,
            )
            st.caption(f"Synthetic Lv.5 rows generated: {len(_read_csv_rows(SYNTHETIC_LV5_PATH))}")
        else:
            st.info("Synthetic placeholder files will appear after the pipeline has been run once.")


def _render_macro_explainer() -> None:
    with st.expander("Historical cost family / Lv.5 Pearson correlation scores", expanded=False):
        st.markdown(
            "The macro build publishes Pearson-based screening scores for the historical cost families and WBS L4/L5 clusters. "
            "Operational weights are based on the pooled pricing-basis yearly series; field-specific and cluster rows are retained as diagnostic support."
        )

        pooled_rows = [
            {
                "pricing_basis": row.get("pricing_basis", ""),
                "factor": row.get("factor_display_name", ""),
                "pearson_r_nominal": row.get("pearson_r_nominal", ""),
                "forecast_weight": row.get("forecast_weight", ""),
                "direction": row.get("direction", ""),
                "observation_years": row.get("observation_years", ""),
            }
            for row in _top_rows(
                [row for row in _read_csv_rows(MACRO_WEIGHTS_PATH) if row.get("support_status") == "operational" and row.get("weight_eligible") == "yes"]
            )
        ]
        if pooled_rows:
            st.markdown("**Operational pooled weights**")
            st.dataframe(pooled_rows, width="stretch", hide_index=True)

        cluster_rows = [
            {
                "field": row.get("field", ""),
                "pricing_basis": row.get("pricing_basis", ""),
                "wbs_cluster": row.get("wbs_cluster", ""),
                "factor": row.get("factor_display_name", ""),
                "pearson_r_nominal": row.get("pearson_r_nominal", ""),
                "forecast_weight": row.get("forecast_weight", ""),
                "direction": row.get("direction", ""),
                "support_status": row.get("support_status", ""),
            }
            for row in _top_rows(
                [row for row in _read_csv_rows(MACRO_CLUSTER_WEIGHTS_PATH) if row.get("support_status") == "operational" and row.get("weight_eligible") == "yes"]
            )
        ]
        if cluster_rows:
            st.markdown("**WBS family / Lv.5 diagnostic scores**")
            st.dataframe(cluster_rows, width="stretch", hide_index=True)

        st.caption(
            "These scores are audit support, not a live scaling rule. The estimator currently consumes the pooled operational weights only."
        )


def render_build_artifacts_page() -> None:
    st.markdown("# BUILD ESTIMATOR ARTIFACTS")
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

    _render_synthetic_explainer()
    _render_macro_explainer()

    st.divider()

    if st.button("BUILD ARTIFACTS", type="primary"):
        progress_bar = st.progress(0, text="Initializing pipeline...")
        status_container = st.empty()

        try:
            progress_bar.progress(15, text="Building canonical mappings...")
            build_canonical_mappings = _load_fresh_module("src.io.build_canonical_mappings").main

            build_canonical_mappings()

            progress_bar.progress(30, text="Building unit price history...")
            build_unit_price_history = _load_fresh_module("src.modeling.unit_price_history_pipeline").main

            build_unit_price_history()

            progress_bar.progress(45, text="Running unit price analysis...")
            build_unit_price_well = _load_fresh_module("src.modeling.unit_price_well_analysis").main

            build_unit_price_well()

            progress_bar.progress(58, text="Running macro analysis...")
            build_macro = _load_fresh_module("src.modeling.unit_price_macro_analysis").main

            build_macro()

            progress_bar.progress(70, text="Building WBS tree...")
            build_wbs_tree_artifacts = _load_fresh_module("src.modeling.wbs_tree_diagram").build_wbs_tree_artifacts

            build_wbs_tree_artifacts()

            progress_bar.progress(80, text="Running phase 4 preflight...")
            run_phase4 = _load_fresh_module("src.modeling.phase4_preflight_and_baseline").run_phase4

            run_phase4(group_by=group_by, use_synthetic=use_synthetic, synthetic_policy="training")

            progress_bar.progress(90, text="Building validation artifacts...")
            build_validation_artifacts = _load_fresh_module("src.modeling.phase5_estimation_core").build_validation_artifacts

            build_validation_artifacts(refresh_pipeline=False)

            progress_bar.progress(96, text="Building operational assets...")
            build_ops = _load_fresh_module("src.app.build_phase5_operational_assets").main

            build_ops()

            progress_bar.progress(100, text="Pipeline complete")
            st.session_state["artifacts_built"] = True
            status_container.success("All estimator artifacts refreshed from dashboard workbook. Proceed to **WBS Tree** or **Estimator**.")

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
