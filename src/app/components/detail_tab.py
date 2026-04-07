from __future__ import annotations

import csv
import io
import json

import streamlit as st


def render_detail_tab(result: dict) -> None:
    st.subheader("DETAIL WBS ESTIMATOR (PRIMARY AUDIT VIEW)")
    detail_rows = result["detail_wbs"]
    st.dataframe(detail_rows, use_container_width=True, hide_index=True)

    total = sum(r["estimate_usd"] for r in detail_rows)
    st.caption(f"Detail row sum USD: {total:,.2f}")

    with st.expander("Audit Preview"):
        st.dataframe(result["audit_rows"], use_container_width=True, hide_index=True)

    audit_buffer = io.StringIO()
    if result["audit_rows"]:
        writer = csv.DictWriter(audit_buffer, fieldnames=list(result["audit_rows"][0].keys()))
        writer.writeheader()
        writer.writerows(result["audit_rows"])

    st.download_button("Download Audit CSV", data=audit_buffer.getvalue(), file_name="app_estimate_audit.csv", mime="text/csv")
    st.download_button(
        "Download Run Manifest",
        data=json.dumps({"field": result["campaign_input"]["field_canonical"], "year": result["campaign_input"]["campaign_start_year"], "rows": len(result["audit_rows"])}, indent=2),
        file_name="app_run_manifest_preview.json",
        mime="application/json",
    )
