from __future__ import annotations

import re
import json
from typing import Any

import streamlit as st


ERROR_COLUMN = "Error (MMUSD) / MAPE (%)"
FORMULA_LABELS = {
    "active_day_rate": "Active day rate",
    "depth_rate": "Depth rate",
    "campaign_scope_benchmark": "Campaign",
    "per_well_job": "Per-well job",
}

_FACTOR_RATIO_RE = re.compile(
    r"([\d.]+)\*\(([^/]+)/([^)]+)\)"
)


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


def _parse_formula_parts(formula_segment: str) -> list[dict[str, Any]]:
    """Extract weight/target/base triples from one basis formula segment."""
    parts = []
    for match in _FACTOR_RATIO_RE.finditer(formula_segment):
        weight_str, target_str, base_str = match.group(1), match.group(2), match.group(3)
        try:
            weight = float(weight_str)
            # target looks like "brent_usd_bbl_2026" or "override_brent_usd_bbl"
            # base looks like "brent_usd_bbl_2022"
            parts.append({"weight": weight, "target": target_str.strip(), "base": base_str.strip()})
        except ValueError:
            continue
    return parts


def _formula_multiplier(basis_formula: str) -> float | None:
    """Numerically evaluate the formula segment to get the total multiplier."""
    # Each part: weight * (target_value / base_value)
    # We can't easily extract numeric values from the label strings, so compute from parts
    # Format: "0.333*(target_2026/base_2022) + ..." — but we need actual numbers
    # Since the formula is already encoded as labels, try to compute from regex match on the raw formula
    try:
        total = sum(p["weight"] for p in _parse_formula_parts(basis_formula))
        if total <= 0:
            return None
        # We can't evaluate ratios from label strings — return None to skip numeric display
        return None
    except Exception:
        return None


def _render_forecast_formula(result: dict) -> None:
    manifest = result.get("run_manifest", {})
    formula = manifest.get("external_adjustment_formula", "")
    pad_scope = manifest.get("pad_scope", {})
    ext_applied = manifest.get("runtime_toggles", {}).get("external_forecast_applied", False)

    st.divider()
    st.subheader("Forecast Adjustment & Scope")

    # Macro escalation formula
    col_macro, col_pad = st.columns([2, 1])
    with col_macro:
        st.markdown("**Macro escalation formula**")
        if not formula:
            st.caption("No forecast formula — external adjustment was not applied.")
        elif not ext_applied:
            st.caption("External forecast adjustment was requested but not applied (missing macro data). Historical-only mode.")
        else:
            display_formula = formula
            for raw_label, pretty_label in FORMULA_LABELS.items():
                display_formula = display_formula.replace(raw_label, pretty_label)

            # Split by basis and display each segment
            segments = display_formula.split("; ")
            for segment in segments:
                if ":" not in segment:
                    continue
                basis_label, expr = segment.split(":", 1)
                st.markdown(f"*{basis_label.strip()}*")
                st.code(f"factor = {expr.strip()}", language="text")

    with col_pad:
        st.markdown("**Pad scope add-on**")
        pad_job_size = pad_scope.get("pad_job_size", "Standard")
        add_on = pad_scope.get("pad_add_on_mmusd", 0.0) or 0.0
        new_frac = pad_scope.get("new_cellar_fraction", 1.0) or 1.0
        new_count = pad_scope.get("new_cellar_count", 0)
        existing_count = pad_scope.get("existing_cellar_count", 0)
        st.metric("Pad type", pad_job_size)
        if add_on > 0:
            st.metric("Major uplift", f"+{add_on:.3f} MM.USD")
        else:
            st.caption("Standard pad — no uplift above historical template baseline.")
        st.caption(
            f"Cellars: {new_count} new / {existing_count} existing "
            f"(fraction applied: {new_frac:.0%})"
        )


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

    _render_forecast_formula(result)
