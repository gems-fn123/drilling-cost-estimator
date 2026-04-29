from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.modeling.wbs_tree_diagram import WBS_TREE_COMBINED_JSON, load_wbs_tree_payload, render_wbs_tree_html


def _compact_usd(value: float) -> str:
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 1_000_000_000:
        return f"{sign}{abs_value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"{sign}{abs_value / 1_000:.2f}K"
    return f"{sign}{abs_value:,.0f}"


def _short_text(value: str, limit: int = 28) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _split_node_label(node: dict) -> tuple[str, str]:
    raw = (node.get("node_label") or "").strip()
    if " - " in raw:
        node_id, desc = raw.split(" - ", 1)
        return node_id.strip(), desc.strip()
    if raw:
        return raw, ""
    return (node.get("wbs_id") or "UNSPECIFIED").strip(), ""


def _focus_option_label(node: dict) -> str:
    node_id, desc = _split_node_label(node)
    sum_part = _compact_usd(float(node.get("sum_usd", 0.0)))
    if desc and desc.lower() != node_id.lower():
        return f"{node_id} - {_short_text(desc)} | {sum_part}"
    return f"{node_id} | {sum_part}"


def render_wbs_tree_tab() -> None:
    st.subheader("WBS TREE")
    st.caption("Precomputed WBS tree from processed artifacts.")

    if not WBS_TREE_COMBINED_JSON.exists():
        st.error("WBS tree artifact not found. Run the pipeline to generate it.")
        return

    if st.button("Reload tree from disk"):
        st.session_state.pop("wbs_tree_payload", None)

    if "wbs_tree_payload" not in st.session_state:
        st.session_state["wbs_tree_payload"] = load_wbs_tree_payload()

    payload = st.session_state.get("wbs_tree_payload")
    if not payload:
        st.error("WBS tree payload could not be loaded.")
        return

    source_contract = payload.get("source_contract", {})
    st.caption(
        f"Src: {source_contract.get('dataset', 'n/a')} | "
        f"Sheet: {source_contract.get('source_sheet_required', 'n/a')} | "
        f"H: {source_contract.get('hierarchy_required', 'n/a')}"
    )

    field_options = sorted(payload.get("fields", {}).keys())
    if not field_options:
        st.info("No field tree available in payload.")
        return

    selected_field = st.selectbox("Field", options=field_options, key="wbs_field_selector")
    selected_field_tree = payload["fields"][selected_field]

    # Campaign tier selector is intentionally direct descendants only.
    campaign_nodes = selected_field_tree.get("children", [])
    campaign_option_keys = ["__all__"] + [f"campaign_{idx}" for idx in range(len(campaign_nodes))]
    campaign_option_map: dict[str, dict | None] = {"__all__": None}
    for idx, node in enumerate(campaign_nodes):
        campaign_option_map[f"campaign_{idx}"] = node

    selected_campaign_key = st.selectbox(
        "Campaign tier",
        options=campaign_option_keys,
        format_func=lambda key: "All campaign tiers" if key == "__all__" else _focus_option_label(campaign_option_map[key] or {}),
        key="wbs_campaign_selector",
    )
    selected_campaign_node = campaign_option_map[selected_campaign_key]

    focus_root = selected_field_tree if selected_campaign_node is None else selected_campaign_node

    if selected_campaign_node is not None:
        # Progressive cascade: each selector only shows direct children of the current node.
        current_node = selected_campaign_node
        for depth in range(1, 8):
            direct_children = current_node.get("children", [])
            if not direct_children:
                break

            option_keys = ["__stop__"] + [f"child_{idx}" for idx in range(len(direct_children))]
            option_map: dict[str, dict] = {f"child_{idx}": node for idx, node in enumerate(direct_children)}
            child_level = int(direct_children[0].get("level", int(current_node.get("level", 0)) + 1))
            selector_key = (
                f"wbs_focus_selector_{selected_field}_{selected_campaign_key}_"
                f"{depth}_{str(current_node.get('wbs_id', ''))}"
            )

            selected_step_key = st.selectbox(
                f"Cascade node (WBS L{child_level})",
                options=option_keys,
                format_func=lambda key, node=current_node, mapping=option_map: (
                    f"{_focus_option_label(node)} (stop here)" if key == "__stop__" else _focus_option_label(mapping[key])
                ),
                index=1,
                key=selector_key,
            )

            if selected_step_key == "__stop__":
                break

            current_node = option_map[selected_step_key]

        focus_root = current_node

    st.caption("sum = descendants; spr = P90 - P10.")
    focused_payload = {
        "generated_at_utc": payload.get("generated_at_utc"),
        "source_contract": source_contract,
        "fields": {selected_field: focus_root},
    }
    components.html(render_wbs_tree_html(focused_payload), height=1200, scrolling=True)

    st.download_button(
        "Download WBS Tree JSON",
        data=json.dumps(payload, indent=2),
        file_name="wbs_tree_interactive.json",
        mime="application/json",
    )