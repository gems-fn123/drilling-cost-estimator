from __future__ import annotations

import csv
import io
import json

import streamlit as st


def render_detail_tab(result: dict) -> None:
    st.subheader("DETAIL WBS ESTIMATOR (PRIMARY AUDIT VIEW)")
    detail_rows = result["detail_wbs"]
    all_lv5 = all((row.get("l5_id") or "").strip() for row in detail_rows)
    if all_lv5:
        st.success("Audit check: estimation rows are Lv.5-only (all rows carry `l5_id`).")
    else:
        st.error("Audit check failed: non-Lv.5 row detected in detail output.")

    st.caption(
        "Method: field-specific family analog with anchor-year Lv.5 row distribution; `uncertainty_pct` "
        "is empirical spread ((P90-P10)/median*100) over grouped historical peers."
    )

    with st.expander("Estimator method and output schema", expanded=False):
        st.markdown(
            "- Method: direct unit-price benchmark with anchor-year cost-family distribution and campaign-scope analogs.\n"
            "- Active uncertainty: empirical spread from field-specific grouped historical peers.\n"
            "- The summary contract keeps totals, reconciliation, and anchor-year metadata together.\n"
            "- The detail contract keeps row-grain lineage, WBS family tags, source wells, and support explanations."
        )
        st.dataframe(
            [
                {"output": "campaign_summary", "contains": "Totals, reconciliation status, anchor year, L2 breakdown, matrix note."},
                {"output": "detail_wbs", "contains": "One row per L5 estimate with lineage, uncertainty, and support text."},
                {"output": "audit_rows", "contains": "Export-ready row contract with audit_key and source_row_ids."},
                {"output": "run_manifest", "contains": "Runtime toggles, formulas, and artifact provenance."},
            ],
            width="stretch",
            hide_index=True,
        )

    enriched_rows = []
    for row in detail_rows:
        unc_pct = float(row.get("uncertainty_pct", 0.0))
        if unc_pct <= 25:
            unc_band = "low_spread"
        elif unc_pct <= 75:
            unc_band = "moderate_spread"
        else:
            unc_band = "high_spread"
        enriched_rows.append(
            {
                "well_label": row.get("well_label", ""),
                "component_scope": row.get("component_scope", ""),
                "classification": row.get("classification", ""),
                "l2_id": row.get("l2_id", ""),
                "l3_id": row.get("l3_id", ""),
                "l4_id": row.get("l4_id", ""),
                "l5_id": row.get("l5_id", ""),
                "l5_desc": row.get("l5_desc", ""),
                "wbs_family_tag": row.get("wbs_family_tag", ""),
                "estimate_usd": row.get("estimate_usd", 0.0),
                "estimate_formatted": f"{float(row.get('estimate_usd', 0.0))/1_000_000.0:.2f} mm USD",
                "uncertainty_pct": round(unc_pct, 2),
                "uncertainty_band": unc_band,
                "uncertainty_type": row.get("uncertainty_type", ""),
                "estimation_method": row.get("estimation_method", ""),
                "driver_family": row.get("driver_family", ""),
                "source_row_count": row.get("source_row_count", 0),
                "source_field_campaign_years": row.get("source_field_campaign_years", ""),
                "source_wells": row.get("source_wells", ""),
                "support_explanation": row.get("support_explanation", ""),
            }
        )

    st.dataframe(enriched_rows, width="stretch", hide_index=True)

    total = sum(r["estimate_usd"] for r in detail_rows)
    st.caption(f"Detail row sum USD: {total:,.2f}")

    with st.expander("Audit Preview"):
        st.dataframe(result["audit_rows"], width="stretch", hide_index=True)

    audit_buffer = io.StringIO()
    if result["audit_rows"]:
        writer = csv.DictWriter(audit_buffer, fieldnames=list(result["audit_rows"][0].keys()))
        writer.writeheader()
        writer.writerows(result["audit_rows"])

    st.download_button("Download Audit CSV", data=audit_buffer.getvalue(), file_name="app_estimate_audit.csv", mime="text/csv")
    st.download_button(
        "Download Run Manifest",
        data=json.dumps(result.get("run_manifest", {}), indent=2),
        file_name="app_run_manifest_preview.json",
        mime="application/json",
    )
