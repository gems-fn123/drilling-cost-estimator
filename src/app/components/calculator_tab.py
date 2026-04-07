from __future__ import annotations

import json

import streamlit as st


def render_calculator_results(result: dict) -> None:
    st.subheader("Per-Well Results")
    for row in result["well_outputs"]:
        st.markdown(
            f"- **{row['well_label']}**: "
            f"{row['estimated_cost_mmusd']:.2f} MM.USD | "
            f"±{row['uncertainty_pct']:.1f}% ({row['uncertainty_label']}) | "
            f"{row['estimated_days']:.1f} DAYS"
        )

    summary = result["campaign_summary"]
    st.markdown("---")
    st.subheader("TOTAL CAMPAIGN COST")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total (MM.USD)", f"{summary['total_campaign_cost_mmusd']:.2f}")
    c2.metric("Well-tied (USD)", f"{summary['well_component_usd']:,.0f}")
    c3.metric("Hybrid (USD)", f"{summary['hybrid_component_usd']:,.0f}")
    c4.metric("Campaign-tied (USD)", f"{summary['campaign_tied_component_usd']:,.0f}")

    st.caption(f"Reconciliation status: {summary['reconciliation_status']}")

    for warning in result.get("warnings", []):
        if warning:
            st.warning(warning)

    st.download_button(
        "Download Summary JSON",
        data=json.dumps(summary, indent=2),
        file_name="app_estimate_summary.json",
        mime="application/json",
    )
