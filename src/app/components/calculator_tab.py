from __future__ import annotations

import json

import streamlit as st


def render_calculator_results(result: dict) -> None:
    summary = result["campaign_summary"]

    st.subheader("TOTAL CAMPAIGN ESTIMATE")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total (MM.USD)", f"{summary['total_campaign_cost_mmusd']:.2f}")
    c2.metric("Well-linked (USD)", f"{summary['well_component_usd']:,.0f}")
    c3.metric("Hybrid (USD)", f"{summary['hybrid_component_usd']:,.0f}")
    c4.metric("Campaign-tied (USD)", f"{summary['campaign_tied_component_usd']:,.0f}")

    st.caption(f"Reconciliation status: {summary['reconciliation_status']}")
    st.caption(f"Estimator method: {summary.get('estimation_methodology', 'n/a')}")
    st.caption(f"Uncertainty definition: {summary.get('uncertainty_definition', 'n/a')}")

    st.subheader("Per-Well Estimate")
    st.dataframe(
        [
            {
                "well_label": r["well_label"],
                "estimated_cost_mmusd": round(r["estimated_cost_mmusd"], 3),
                "estimated_days": round(r["estimated_days"], 1),
                "uncertainty_pct": round(r["uncertainty_pct"], 2),
                "method": r["method_label"],
                "top_wbs_contributors": " | ".join(r.get("top_wbs_contributors", [])),
            }
            for r in result["well_outputs"]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Cost Category Matrix")
    st.caption("Matrix cells are displayed in MMUSD. Shared `campaign_tied` / `hybrid` rows stay shared in the detail audit and are allocated to wells here for presentation only.")
    st.dataframe(summary.get("category_matrix", []), use_container_width=True, hide_index=True)
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
