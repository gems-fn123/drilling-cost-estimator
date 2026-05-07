"""Build Artifacts page – runs the ETL pipeline from dashboard workbook only."""

from __future__ import annotations

import csv
import importlib
import sys
import traceback
from pathlib import Path

import streamlit as st
from streamlit_echarts import st_echarts

from src.app.components.echarts_utils import (
    build_dual_axis_line_chart_options,
    build_heatmap_chart_options,
)

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
DASHBOARD_WORKBOOK_NAME = "20260422_Data for Dashboard.xlsx"
SYNTHETIC_CAMPAIGN_PATH = PROCESSED / "synthetic_campaign_placeholders.csv"
SYNTHETIC_LV5_PATH = PROCESSED / "synthetic_wbs_lv5_placeholders.csv"
MACRO_WEIGHTS_PATH = PROCESSED / "unit_price_macro_weights.csv"
MACRO_CLUSTER_WEIGHTS_PATH = PROCESSED / "unit_price_macro_cluster_weights.csv"

PRICING_BASIS_LABELS = {
    "active_day_rate": "Active day rate",
    "depth_rate": "Depth rate",
    "campaign_scope_benchmark": "Campaign",
    "per_well_job": "Per-well job",
}
PRICING_BASIS_SHORT_LABELS = {
    "active_day_rate": "Day",
    "depth_rate": "Depth",
    "campaign_scope_benchmark": "Campaign",
    "per_well_job": "Job",
}
PRICING_BASIS_UNITS = {
    "active_day_rate": "USD/day",
    "depth_rate": "USD/ft",
    "campaign_scope_benchmark": "USD/campaign",
    "per_well_job": "USD/well",
}


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


def _build_heatmap_points(rows: list[dict[str, str]], x_labels: list[str], y_labels: list[str]) -> list[list[float]]:
    x_index = {label: idx for idx, label in enumerate(x_labels)}
    y_index = {label: idx for idx, label in enumerate(y_labels)}
    points: list[list[float]] = []
    for row in rows:
        x_label = row.get("factor_display_name", row.get("factor_name", ""))
        y_label = row.get("heatmap_row_label", "")
        if x_label not in x_index or y_label not in y_index:
            continue
        points.append([x_index[x_label], y_index[y_label], _as_float(row.get("pearson_r_nominal", "0"))])
    return points


def _unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _pricing_basis_label(value: str) -> str:
    return PRICING_BASIS_LABELS.get(value, str(value or "").replace("_", " ").title())


def _pricing_basis_unit(value: str) -> str:
    return PRICING_BASIS_UNITS.get(value, "USD")


def _pricing_basis_short_label(value: str) -> str:
    return PRICING_BASIS_SHORT_LABELS.get(value, _pricing_basis_label(value))


def _short_cluster_label(value: str, *, max_words: int = 4) -> str:
    words = [word for word in str(value or "").replace("_", " ").split() if word]
    if not words:
        return ""
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[-max_words:])


def _top_cluster_combo_rows(rows: list[dict[str, str]], *, limit: int = 8) -> list[dict[str, str]]:
    combo_best: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        combo_key = (str(row.get("pricing_basis", "")).strip(), str(row.get("wbs_cluster", "")).strip())
        if not combo_key[0] or not combo_key[1]:
            continue
        current = combo_best.get(combo_key)
        score = (
            _as_float(row.get("forecast_weight", "0")),
            _as_float(row.get("abs_nominal_correlation", "0")),
        )
        if current is None:
            combo_best[combo_key] = row
            continue
        current_score = (
            _as_float(current.get("forecast_weight", "0")),
            _as_float(current.get("abs_nominal_correlation", "0")),
        )
        if score > current_score:
            combo_best[combo_key] = row

    ranked = sorted(
        combo_best.values(),
        key=lambda row: (
            _as_float(row.get("forecast_weight", "0")),
            _as_float(row.get("abs_nominal_correlation", "0")),
        ),
        reverse=True,
    )
    return ranked[:limit]


def _pooled_pricing_history_by_year(history_rows: list[dict[str, str]], macro_mod, pricing_basis: str) -> dict[int, float]:
    active_exclusions = macro_mod.load_active_exclusions()
    unit_buckets: dict[tuple, dict[str, float]] = {}
    for row in history_rows:
        if str(row.get("pricing_basis", "")).strip() != pricing_basis:
            continue

        year = int(row.get("campaign_year") or 0)
        if year <= 0:
            continue

        cost = _as_float(row.get("actual_cost_usd", "0"))
        field = str(row.get("field", "")).strip()
        campaign = str(row.get("campaign_canonical", "")).strip()

        if pricing_basis == "campaign_scope_benchmark":
            quantity = 1.0
            unit_key = (campaign, pricing_basis, year)
        else:
            well = str(row.get("well_canonical", "")).strip()
            if not well:
                continue
            if (field, macro_mod.normalize_exclusion_well(well)) in active_exclusions:
                continue
            if pricing_basis == "active_day_rate":
                quantity = _as_float(row.get("active_operational_days", "0"))
            elif pricing_basis == "depth_rate":
                quantity = _as_float(row.get("actual_depth_ft", "0"))
            elif pricing_basis == "per_well_job":
                quantity = 1.0
            else:
                continue
            unit_key = (field, campaign, pricing_basis, well, year)

        if quantity <= 0.0:
            continue

        unit_bucket = unit_buckets.setdefault(unit_key, {"cost": 0.0, "quantity": quantity})
        unit_bucket["cost"] += cost
        unit_bucket["quantity"] = quantity

    year_totals: dict[int, dict[str, float]] = {}
    for unit_key, unit_bucket in unit_buckets.items():
        year = int(unit_key[-1])
        bucket = year_totals.setdefault(year, {"cost": 0.0, "quantity": 0.0})
        bucket["cost"] += unit_bucket["cost"]
        bucket["quantity"] += unit_bucket["quantity"]

    return {
        year: totals["cost"] / totals["quantity"]
        for year, totals in sorted(year_totals.items())
        if totals["quantity"] > 0.0
    }


def _pooled_cluster_history_by_year(history_rows: list[dict[str, str]], macro_mod, pricing_basis: str, wbs_cluster: str) -> dict[int, float]:
    active_exclusions = macro_mod.load_active_exclusions()
    cluster_map = macro_mod._build_fuzzy_l4_cluster_map(history_rows)
    field_buckets: dict[tuple, dict[str, float]] = {}

    for row in history_rows:
        if str(row.get("pricing_basis", "")).strip() != pricing_basis:
            continue

        year = int(row.get("campaign_year") or 0)
        if year <= 0:
            continue

        cluster_key = macro_mod.build_wbs_cluster_key(
            row.get("level_4", ""),
            row.get("level_5", ""),
            cluster_map=cluster_map,
        )
        if cluster_key != wbs_cluster:
            continue

        field = str(row.get("field", "")).strip()
        cost = _as_float(row.get("actual_cost_usd", "0"))

        if pricing_basis == "campaign_scope_benchmark":
            quantity = 1.0
        else:
            well = str(row.get("well_canonical", "")).strip()
            if not well:
                continue
            if (field, macro_mod.normalize_exclusion_well(well)) in active_exclusions:
                continue
            if pricing_basis == "active_day_rate":
                quantity = _as_float(row.get("active_operational_days", "0"))
            elif pricing_basis == "depth_rate":
                quantity = _as_float(row.get("actual_depth_ft", "0"))
            elif pricing_basis == "per_well_job":
                quantity = 1.0
            else:
                continue

        if quantity <= 0.0:
            continue

        field_key = (field, year)
        bucket = field_buckets.setdefault(field_key, {"cost": 0.0, "quantity": 0.0})
        bucket["cost"] += cost
        bucket["quantity"] += quantity

    yearly_field_values: dict[int, list[float]] = {}
    for (field, year), bucket in field_buckets.items():
        if bucket["quantity"] <= 0.0:
            continue
        yearly_field_values.setdefault(year, []).append(bucket["cost"] / bucket["quantity"])

    return {
        year: sum(values) / len(values)
        for year, values in sorted(yearly_field_values.items())
        if values
    }


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


def _render_operational_history_charts(macro_mod, operational_specs: list[dict[str, str]], history_rows: list[dict[str, str]], macro_rows: list[dict[str, str]]) -> None:
    macro_lookup = {
        int(row["year"]): {factor: _as_float(row.get(factor, "0")) for factor in macro_mod.ALL_FACTORS}
        for row in macro_rows
        if str(row.get("year", "")).strip()
    }
    if not operational_specs:
        return

    st.markdown("**Yearly historical series behind the pooled Pearson scores**")
    st.caption(
        "Each row below shows the yearly cost basis history against its candidate macro factor. Pearson remains the screening score, while the chart keeps the early campaign years visible."
    )

    for idx, spec in enumerate(operational_specs):
        pricing_basis = spec.get("pricing_basis", "")
        factor_name = spec.get("factor_name", "")
        factor_display_name = spec.get("factor_display_name", factor_name)
        history_series = _pooled_pricing_history_by_year(history_rows, macro_mod, pricing_basis)
        years = sorted(history_series)
        if not years:
            continue

        categories = [str(year) for year in years]
        left_values = [history_series.get(year) for year in years]
        right_values = [macro_lookup.get(year, {}).get(factor_name) or None for year in years]
        subtitle = (
            ""
        )
        annotation = (
            f"R^2 {spec.get('pearson_r_nominal', 'n/a')} | "
            f"{spec.get('observation_years', 'n/a')}"
        )

        st_echarts(
            build_dual_axis_line_chart_options(
                f"{_pricing_basis_label(pricing_basis)} vs {factor_display_name}",
                categories,
                f"{_pricing_basis_label(pricing_basis)} history",
                left_values,
                factor_display_name,
                right_values,
                subtitle=subtitle,
                annotation=annotation,
                left_unit=_pricing_basis_unit(pricing_basis),
                right_unit="factor level",
            ),
            height="360px",
            key=f"build_artifacts_operational_history_{idx}",
        )


def _render_cluster_history_charts(macro_mod, cluster_specs: list[dict[str, str]], history_rows: list[dict[str, str]], macro_rows: list[dict[str, str]]) -> None:
    macro_lookup = {
        int(row["year"]): {factor: _as_float(row.get(factor, "0")) for factor in macro_mod.ALL_FACTORS}
        for row in macro_rows
        if str(row.get("year", "")).strip()
    }
    if not cluster_specs:
        return

    st.markdown("**Yearly historical series behind the Lv.4 cluster Pearson scores**")
    st.caption(
        "These rows use the field-balanced cluster history, so description drift across campaigns stays in one auditable bucket while the yearly coverage remains readable."
    )

    for idx, spec in enumerate(cluster_specs):
        pricing_basis = spec.get("pricing_basis", "")
        factor_name = spec.get("factor_name", "")
        factor_display_name = spec.get("factor_display_name", factor_name)
        cluster_name = spec.get("wbs_cluster", "")
        short_cluster = _short_cluster_label(cluster_name)
        history_series = _pooled_cluster_history_by_year(history_rows, macro_mod, pricing_basis, cluster_name)
        years = sorted(history_series)
        if not years:
            continue

        categories = [str(year) for year in years]
        left_values = [history_series.get(year) for year in years]
        right_values = [macro_lookup.get(year, {}).get(factor_name) or None for year in years]
        subtitle = (
            ""
        )
        annotation = (
            f"R^2 {spec.get('pearson_r_nominal', 'n/a')} | "
            f"{spec.get('observation_years', 'n/a')}"
        )

        st_echarts(
            build_dual_axis_line_chart_options(
                f"{_pricing_basis_label(pricing_basis)} · {short_cluster} vs {factor_display_name}",
                categories,
                f"{short_cluster} history",
                left_values,
                factor_display_name,
                right_values,
                subtitle=subtitle,
                annotation=annotation,
                left_unit=_pricing_basis_unit(pricing_basis),
                right_unit="factor level",
                left_color="#7c3aed",
                right_color="#ea580c",
            ),
            height="360px",
            key=f"build_artifacts_cluster_history_{idx}",
        )


def _render_macro_explainer() -> None:
    with st.expander("Historical Pearson correlations", expanded=False):
        st.markdown(
            "The macro build publishes Pearson-based screening scores for the historical cost factors and the fuzzy-matched Level 4 WBS clusters. "
            "The heatmaps summarize the latest scores first, and the yearly views below show the underlying cost history one chart per row."
        )

        operational_source_rows = [
            row
            for row in _read_csv_rows(MACRO_WEIGHTS_PATH)
            if row.get("scope_type") == "pooled_pricing_basis"
            and row.get("field") == "ALL_FIELDS"
            and row.get("support_status") == "operational"
            and row.get("weight_eligible") == "yes"
        ]
        cluster_source_rows = [
            row
            for row in _read_csv_rows(MACRO_CLUSTER_WEIGHTS_PATH)
            if row.get("scope_type") == "pooled_wbs_cluster"
            and row.get("field") == "ALL_FIELDS"
            and row.get("support_status") == "operational"
            and row.get("weight_eligible") == "yes"
        ]

        if not operational_source_rows and not cluster_source_rows:
            st.info("Correlation outputs will appear after the build artifacts are refreshed.")
            return

        factor_labels = _unique_in_order(
            [row.get("factor_display_name", row.get("factor_name", "")) for row in operational_source_rows or cluster_source_rows]
        )
        basis_labels = _unique_in_order([_pricing_basis_label(row.get("pricing_basis", "")) for row in operational_source_rows])

        operational_heatmap_rows = [
            {
                **row,
                "heatmap_row_label": _pricing_basis_label(row.get("pricing_basis", "")),
            }
            for row in operational_source_rows
        ]
        operational_points = _build_heatmap_points(operational_heatmap_rows, factor_labels, basis_labels)

        selected_cluster_combos = _top_cluster_combo_rows(cluster_source_rows, limit=8)
        selected_cluster_combo_keys = {
            (str(row.get("pricing_basis", "")).strip(), str(row.get("wbs_cluster", "")).strip())
            for row in selected_cluster_combos
        }
        selected_cluster_rows = [
            {
                **row,
                "heatmap_row_label": f"{_short_cluster_label(row.get('wbs_cluster', ''))} · {_pricing_basis_short_label(row.get('pricing_basis', ''))}",
            }
            for row in cluster_source_rows
            if (str(row.get("pricing_basis", "")).strip(), str(row.get("wbs_cluster", "")).strip()) in selected_cluster_combo_keys
        ]
        selected_cluster_labels = _unique_in_order([row["heatmap_row_label"] for row in selected_cluster_rows])
        cluster_points = _build_heatmap_points(selected_cluster_rows, factor_labels, selected_cluster_labels)

        if operational_points:
            st_echarts(
                build_heatmap_chart_options(
                    "Pooled Pearson heatmap",
                    factor_labels,
                    basis_labels,
                    operational_points,
                ),
                height="360px",
                key="build_artifacts_operational_heatmap",
            )
        else:
            st.info("Pooled Pearson heatmap points will appear after the macro weights artifact is built.")

        if cluster_points:
            st_echarts(
                build_heatmap_chart_options(
                    "Lv.4 cluster Pearson heatmap",
                    factor_labels,
                    selected_cluster_labels,
                    cluster_points,
                ),
                height="420px",
                key="build_artifacts_cluster_heatmap",
            )
        else:
            st.info("Cluster Pearson heatmap points will appear after the clustered WBS artifact is built.")

        st.caption(
            "The cluster layer groups rows by fuzzy-matched Level 4 descriptions, so structure drift across campaigns stays in the same correlation bucket."
        )

        macro_mod = _load_fresh_module("src.modeling.unit_price_macro_analysis")
        history_rows = macro_mod.read_csv(macro_mod.UNIT_PRICE_HISTORY_MART)
        macro_rows = macro_mod.read_csv(macro_mod.MACRO_REFERENCE_PATH)

        operational_specs = [
            {
                "pricing_basis": row.get("pricing_basis", ""),
                "factor_name": row.get("factor_name", ""),
                "factor_display_name": row.get("factor_display_name", row.get("factor_name", "")),
                "pearson_r_nominal": row.get("pearson_r_nominal", ""),
                "observation_years": row.get("observation_years", ""),
            }
            for row in _top_rows(operational_source_rows, limit=4)
        ]
        cluster_specs = [
            {
                "pricing_basis": row.get("pricing_basis", ""),
                "wbs_cluster": row.get("wbs_cluster", ""),
                "factor_name": row.get("factor_name", ""),
                "factor_display_name": row.get("factor_display_name", row.get("factor_name", "")),
                "pearson_r_nominal": row.get("pearson_r_nominal", ""),
                "observation_years": row.get("observation_years", ""),
            }
            for row in _top_cluster_combo_rows(cluster_source_rows, limit=4)
        ]

        _render_operational_history_charts(macro_mod, operational_specs, history_rows, macro_rows)
        _render_cluster_history_charts(macro_mod, cluster_specs, history_rows, macro_rows)

        st.caption(
            "Pearson remains a screening score. These yearly charts are there to keep the underlying overlap years, including thin early history, visually inspectable."
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
