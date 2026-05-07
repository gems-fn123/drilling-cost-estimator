from __future__ import annotations

import re
import json

import streamlit as st


ERROR_COLUMN = "Error (MMUSD) / MAPE (%)"
FORMULA_LABELS = {
    "active_day_rate": "Active day rate",
    "depth_rate": "Depth rate",
    "campaign_scope_benchmark": "Campaign",
    "per_well_job": "Per-well job",
}


def _parse_benchmark_error_pair(text: object) -> tuple[float | None, float | None]:
    match = re.search(r"([0-9.]+)\s*/\s*([0-9.]+)%", str(text or ""))
    if not match:
        return None, None
    try:
        return float(match.group(1)), float(match.group(2))
    except ValueError:
        return None, None


def _fallback_benchmark_display(summary: dict) -> str:
    category_rows = summary.get("category_matrix", []) or []
    weighted_error = 0.0
    weighted_mape = 0.0
    total_weight = 0.0
    for row in category_rows:
        row_total = 0.0
        for key, value in row.items():
            if key in {"Cost Category", ERROR_COLUMN}:
                continue
            try:
                row_total += float(value or 0.0)
            except (TypeError, ValueError):
                continue
        error_mmusd, mape_pct = _parse_benchmark_error_pair(row.get(ERROR_COLUMN))
        if error_mmusd is None or mape_pct is None or row_total <= 0.0:
            continue
        weighted_error += error_mmusd * row_total
        weighted_mape += mape_pct * row_total
        total_weight += row_total

    if total_weight <= 0.0:
        return "n/a"
    return f"{weighted_error / total_weight:.2f} MM.USD / {weighted_mape / total_weight:.1f}%"


def render_calculator_results(result: dict) -> None:
    summary = result["campaign_summary"]

    st.subheader("TOTAL CAMPAIGN ESTIMATE")
    with st.container(border=True):
        total_col, benchmark_col = st.columns([1.25, 1])
        with total_col:
            st.metric("Total (MM.USD)", f"{summary['total_campaign_cost_mmusd']:.2f}")
        with benchmark_col:
            st.metric("APE (MM.USD) / MAPE (%)", summary.get("ape_mape_display", _fallback_benchmark_display(summary)))

    st.caption("Row-level audit detail and lineage live on the Audit page.")

    with st.expander("Per-well estimate", expanded=False):
        st.dataframe(
            [
                {
                    "well_label": r["well_label"],
                    "estimated_cost_mmusd": round(r["estimated_cost_mmusd"], 3),
                    "estimated_days": round(r["estimated_days"], 1),
                    "uncertainty_pct": round(r["uncertainty_pct"], 2),
                }
                for r in result["well_outputs"]
            ],
            width="stretch",
            hide_index=True,
        )

    st.subheader("Cost Category Matrix")
    st.caption("Matrix cells are displayed in MMUSD. Shared `campaign_tied` / `hybrid` rows stay shared in the detail audit and are allocated to wells here for presentation only.")
    st.dataframe(summary.get("category_matrix", []), width="stretch", hide_index=True)
    if summary.get("category_matrix_note"):
        st.caption(summary["category_matrix_note"])

    for warning in result.get("warnings", []):
        if warning:
            st.warning(warning)

    st.download_button(
        "Download Summary JSON",
        data=json.dumps(summary, indent=2),
        file_name="app_estimate_summary.json",
        mime="application/json",
    )

    formula = result.get("run_manifest", {}).get("external_adjustment_formula", "")
    if formula:
        display_formula = formula
        for raw_label, pretty_label in FORMULA_LABELS.items():
            display_formula = display_formula.replace(raw_label, pretty_label)
        with st.expander("Forecast formula", expanded=False):
            st.markdown("The estimator applies the external forecast adjustment below when the toggle is enabled.")
            st.code(display_formula, language="text")
