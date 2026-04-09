from __future__ import annotations

import json

import streamlit as st


def _render_fraction_block(title: str, rows: list[dict], label_col: str) -> None:
    st.markdown(f"**{title}**")
    if not rows:
        st.caption("No rows available.")
        return
    st.dataframe(
        [
            {
                label_col: row.get(label_col, "unknown"),
                "share_pct": round(float(row.get("share_fraction", 0.0)) * 100.0, 2),
                "estimate_usd": round(float(row.get("estimate_usd", 0.0)), 2),
                "source_tag": row.get("source_tag", ""),
                "source_rows": int(row.get("source_row_count", 0) or 0),
            }
            for row in rows
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.bar_chart(
        data={
            row.get(label_col, "unknown"): float(row.get("share_fraction", 0.0)) * 100.0
            for row in rows
        }
    )


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

    st.markdown("---")
    st.subheader("Component / Driver Breakdown")
    fractions = result.get("wbs_family_fractions", {})
    c1, c2 = st.columns(2)
    with c1:
        _render_fraction_block("By L2 ID", fractions.get("l2_id", []), "l2_id")
        _render_fraction_block("By Classification", fractions.get("classification", []), "classification")
    with c2:
        _render_fraction_block("By Driver Family", fractions.get("driver_family", []), "driver_family")
        _render_fraction_block(
            "By Component Scope",
            result.get("component_share_breakdown", []),
            "component_scope",
        )

    st.markdown("**Per-Well Direct Driver Attribution**")
    driver_rows = result.get("driver_attribution", {}).get("rows", [])
    st.caption(
        "Source filter: classification=well_tied, well_estimation_use=direct_well_linked "
        f"| rows={len(driver_rows)}"
    )
    st.dataframe(
        [
            {
                "well_label": row.get("well_label", ""),
                "driver_family": row.get("driver_family", "unknown"),
                "direct_fraction_pct": round(float(row.get("direct_fraction_of_well", 0.0)) * 100.0, 2),
                "direct_estimate_usd": round(float(row.get("direct_estimate_usd", 0.0)), 2),
                "source_tag": row.get("source_tag", ""),
                "source_rows": int(row.get("source_row_count", 0) or 0),
            }
            for row in driver_rows
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download Summary JSON",
        data=json.dumps(summary, indent=2),
        file_name="app_estimate_summary.json",
        mime="application/json",
    )
