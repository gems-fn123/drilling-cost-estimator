from __future__ import annotations

from statistics import mean, median
from typing import List

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from src.app.components.echarts_utils import (
    build_distribution_boxplot_options,
    build_stacked_bar_chart_options,
)
from src.modeling.phase5_estimation_core import RATE_FACTOR
from src.modeling.unit_price_macro_analysis import FACTOR_LABELS, MACRO_REFERENCE_PATH, MACRO_WEIGHTS_PATH
from src.modeling.unit_price_well_analysis import SERVICE_TIME_BANDS

REFERENCE_FACTORS = [
    "brent_usd_bbl",
    "indonesia_cpi_index",
    "indonesia_inflation_pct",
    "steel_commodity_proxy_usd_ton",
]
REFERENCE_BASIS = ["active_day_rate", "depth_rate", "per_well_job"]
BASIS_LABELS = {
    "active_day_rate": "Active day rate",
    "depth_rate": "Depth rate",
    "campaign_scope_benchmark": "Campaign",
    "per_well_job": "Per-well job",
}
LABEL_TO_BASIS = {label: basis for basis, label in BASIS_LABELS.items()}
FACTOR_NAME_BY_LABEL = {label: name for name, label in FACTOR_LABELS.items()}


def _load_service_band_rows() -> list[dict[str, str]]:
    if not SERVICE_TIME_BANDS.exists():
        return []
    return pd.read_csv(SERVICE_TIME_BANDS).fillna("").to_dict(orient="records")


def _load_macro_reference_defaults() -> pd.DataFrame:
    if not MACRO_REFERENCE_PATH.exists():
        return pd.DataFrame()

    reference_frame = pd.read_csv(MACRO_REFERENCE_PATH).fillna("")
    reference_2026 = reference_frame[reference_frame["year"] == 2026]
    if reference_2026.empty:
        reference_2026 = reference_frame.tail(1)
    if reference_2026.empty:
        return pd.DataFrame()

    reference_row = reference_2026.iloc[0].to_dict()
    weight_lookup: dict[tuple[str, str], float] = {}
    if MACRO_WEIGHTS_PATH.exists():
        weight_frame = pd.read_csv(MACRO_WEIGHTS_PATH).fillna("")
        for _, row in weight_frame.iterrows():
            if row.get("scope_type") != "pooled_pricing_basis" or row.get("field") != "ALL_FIELDS":
                continue
            if row.get("support_status") != "operational" or row.get("weight_eligible") != "yes":
                continue
            try:
                weight_lookup[(str(row.get("pricing_basis", "")), str(row.get("factor_name", "")))] = float(row.get("forecast_weight", 0.0))
            except (TypeError, ValueError):
                weight_lookup[(str(row.get("pricing_basis", "")), str(row.get("factor_name", "")))] = 0.0

    rows: list[dict[str, object]] = []
    for pricing_basis in REFERENCE_BASIS:
        for factor_name in REFERENCE_FACTORS:
            suggested_weight = weight_lookup.get((pricing_basis, factor_name), 0.0)
            if suggested_weight <= 0.0 and factor_name != "indonesia_inflation_pct":
                suggested_weight = 1.0 / 3.0
            rows.append(
                {
                    "pricing_basis": BASIS_LABELS[pricing_basis],
                    "factor": FACTOR_LABELS[factor_name],
                    "source_year": 2026,
                    "use_reference": factor_name != "indonesia_inflation_pct",
                    "reference_value": float(reference_row.get(factor_name, 0.0) or 0.0),
                    "suggested_weight": float(suggested_weight),
                }
            )

    return pd.DataFrame(rows)


def _load_well_profile_frame() -> pd.DataFrame:
    from src.modeling.unit_price_well_analysis import UNIT_PRICE_WELL_PROFILE

    if not UNIT_PRICE_WELL_PROFILE.exists():
        return pd.DataFrame()
    frame = pd.read_csv(UNIT_PRICE_WELL_PROFILE).fillna("")
    for column in ["actual_depth_ft", "pace_days_per_1000ft", "active_operational_days", "actual_days"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


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


def _render_historical_well_dashboard() -> None:
    profile_frame = _load_well_profile_frame()
    if profile_frame.empty:
        st.info("Historical well profile will appear after the estimator support outputs are built.")
        return

    if "exclude_from_estimator_pool" in profile_frame.columns:
        available = profile_frame[profile_frame["exclude_from_estimator_pool"].astype(str).str.lower() != "yes"].copy()
    else:
        available = profile_frame.copy()
    if available.empty:
        available = profile_frame.copy()

    available["campaign_year"] = pd.to_numeric(available["campaign_year"], errors="coerce")
    available = available.sort_values(["field", "campaign_year", "well_canonical"])

    summary = available.groupby("field", dropna=False).agg(
        available_wells=("well_canonical", pd.Series.nunique),
        campaigns=("campaign_canonical", pd.Series.nunique),
    ).reset_index()
    summary = summary.fillna(0.0).sort_values("field")

    field_labels = summary["field"].astype(str).tolist()
    year_values = [
        int(year)
        for year in sorted(available["campaign_year"].dropna().astype(int).unique().tolist())
    ]
    palette = ["#0f766e", "#2563eb", "#7c3aed", "#ea580c", "#dc2626", "#16a34a"]
    well_stack = []
    for idx, year in enumerate(year_values):
        year_counts = []
        for field in field_labels:
            year_counts.append(
                int(
                    available[
                        (available["field"] == field)
                        & (available["campaign_year"].fillna(0).astype(int) == year)
                    ]["well_canonical"].nunique()
                )
            )
        well_stack.append({"name": str(year), "data": year_counts, "color": palette[idx % len(palette)]})

    depth_groups = []
    pace_groups = []
    for field in field_labels:
        field_rows = available[available["field"] == field]
        depth_values = field_rows["actual_depth_ft"].dropna().astype(float).tolist()
        pace_values = field_rows["pace_days_per_1000ft"].dropna().astype(float).tolist()
        if depth_values:
            depth_groups.append({"label": field, "values": depth_values})
        if pace_values:
            pace_groups.append({"label": field, "values": pace_values})

    st.markdown("**Historical well dashboard**")
    total_wells = int(available["well_canonical"].nunique())
    total_campaigns = int(available["campaign_canonical"].nunique())
    total_fields = int(available["field"].nunique())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fields loaded", total_fields)
    c2.metric("Available wells", total_wells)
    c3.metric("Campaigns covered", total_campaigns)
    c4.metric("Median depth", _format_depth(float(available["actual_depth_ft"].median()) if available["actual_depth_ft"].notna().any() else 0.0))

    chart_cols = st.columns(3)
    with chart_cols[0]:
        st_echarts(
            build_stacked_bar_chart_options(
                "Available wells by field stacked by campaign year",
                field_labels,
                well_stack,
                unit="wells",
                horizontal=True,
                integer_labels=True,
                show_labels=True,
            ),
            height="340px",
            key="historical_well_counts_by_field_year",
        )
    with chart_cols[1]:
        st_echarts(
            build_distribution_boxplot_options(
                "Depth distribution by field",
                depth_groups,
                subtitle="Aggregate distribution view with min / median / max in the tooltip",
                unit="ft",
                fill_color="#0f766e",
                stroke_color="#0f766e",
            ),
            height="340px",
            key="historical_depth_distribution_by_field",
        )
    with chart_cols[2]:
        st_echarts(
            build_distribution_boxplot_options(
                "Service speed by field",
                pace_groups,
                subtitle="Aggregate distribution view with min / median / max in the tooltip",
                unit="days / 1000 ft",
                fill_color="#7c3aed",
                stroke_color="#7c3aed",
            ),
            height="340px",
            key="historical_service_pace_distribution_by_field",
        )

    st.caption(
        "The left chart shows how the available well pool is distributed across field and campaign year. "
        "The distribution charts surface sample count plus min, Q1, median, Q3, and max without opening the audit tables."
    )


def _render_macro_reference_sidebar() -> list[dict]:
    reference_defaults = _load_macro_reference_defaults()
    if reference_defaults.empty:
        st.sidebar.info("Macro reference data will appear after the historical Pearson artifacts are built.")
        return []

    with st.sidebar.expander("What the forecast factors cover", expanded=False):
        st.markdown(
            "**Active day rate** covers the day-rate-linked running cost of drilling activity: rig time, crew time, active services, and other work that scales with time on well."
        )
        st.markdown(
            "**Depth rate** covers the depth-linked part of the estimate: cost that grows with feet drilled, including depth-sensitive services and materials."
        )
        st.markdown(
            "**Campaign** covers shared campaign overhead that is not assigned to one well, such as mobilization, pad setup, logistics, and supervision."
        )

    with st.sidebar.expander("Macro reference data (2026 baseline)", expanded=False):
        st.caption(
            "Edit the 2026 baseline values and suggested weights below. Turn off a row to exclude that factor from the external adjustment. Inflation stays visible for audit context, but it remains diagnostic-only in the current weighting scheme."
        )
        edited = st.sidebar.data_editor(
            reference_defaults,
            hide_index=True,
            num_rows="fixed",
            disabled=["pricing_basis", "factor", "source_year"],
            key="macro_reference_editor",
        )
        if hasattr(edited, "to_dict"):
            rows = edited.to_dict(orient="records")
        else:
            rows = list(edited)

        normalized_rows: list[dict] = []
        for row in rows:
            factor_name = FACTOR_NAME_BY_LABEL.get(str(row.get("factor", "")).strip(), "")
            pricing_basis = LABEL_TO_BASIS.get(str(row.get("pricing_basis", "")).strip(), "")
            if not factor_name:
                continue
            if not pricing_basis:
                continue
            normalized_rows.append({**row, "pricing_basis": pricing_basis, "factor_name": factor_name})
        return normalized_rows


def render_campaign_panel() -> dict:
    st.sidebar.header("Campaign Inputs")
    year = st.sidebar.number_input("Year", min_value=2018, max_value=2035, value=2026, step=1)
    field = st.sidebar.selectbox("Field", ["SLK", "DRJ", "WW"], index=0)
    no_pads = st.sidebar.number_input("No. Pads", min_value=1, max_value=5, value=2, step=1)
    no_wells = st.sidebar.number_input("No. Wells", min_value=1, max_value=20, value=3, step=1)
    no_pad_expansion = st.sidebar.number_input("No. Pad Expansion", min_value=0, max_value=int(no_pads), value=0, step=1)

    macro_reference_settings = _render_macro_reference_sidebar()

    return {
        "year": int(year),
        "field": field,
        "no_pads": int(no_pads),
        "no_wells": int(no_wells),
        "no_pad_expansion": int(no_pad_expansion),
        "macro_reference_settings": macro_reference_settings,
    }


def render_well_inputs(no_wells: int, no_pads: int, field: str | None = None) -> List[dict]:
    _render_historical_well_dashboard()

    with st.expander("Service pace guide", expanded=False):
        _render_service_pace_explainer(field)

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
        st.markdown("**Current scenario input snapshot**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Wells", len(rows))
        c2.metric("Min depth", _format_depth(min(depths)))
        c3.metric("Median depth", _format_depth(median(depths)))
        c4.metric("Mean depth", _format_depth(mean(depths)))
        st.caption(
            f"Max depth: {_format_depth(max(depths))} | Pace mix: Fast {pace_counts['Fast']}, Standard {pace_counts['Standard']}, Careful {pace_counts['Careful']}"
        )

    return rows
