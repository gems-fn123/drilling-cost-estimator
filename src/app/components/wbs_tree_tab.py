from __future__ import annotations

import html
import json

import streamlit as st

from src.modeling.wbs_tree_diagram import WBS_TREE_COMBINED_JSON, load_wbs_tree_payload


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


def _tree_node_html(node: dict, *, depth: int = 0) -> str:
        title = html.escape(str(node.get("node_label") or node.get("wbs_id") or "UNSPECIFIED"))
        sum_part = _compact_usd(float(node.get("sum_usd", 0.0)))
        median_part = _compact_usd(float(node.get("median_usd", 0.0)))
        spread_part = _compact_usd(float(node.get("spread_usd", 0.0)))
        sample_rows = int(node.get("sample_row_count", 0) or 0)
        campaigns = int(node.get("campaign_count", 0) or 0)
        source_rows = int(node.get("source_row_count", 0) or 0)
        source_workbooks = ", ".join(html.escape(str(item)) for item in (node.get("source_workbooks") or [])[:3])
        child_nodes = node.get("children", []) or []
        open_attr = " open" if depth <= 1 else ""

        meta_bits = [
                f"<span class='node-chip'>rows {sample_rows}</span>",
                f"<span class='node-chip'>campaigns {campaigns}</span>",
                f"<span class='node-chip'>sum {sum_part}</span>",
                f"<span class='node-chip'>median {median_part}</span>",
                f"<span class='node-chip'>spr {spread_part}</span>",
        ]

        meta_text = ""
        if source_rows or source_workbooks:
                meta_text = "<div class='node-meta'>"
                if source_rows:
                        meta_text += f"source rows: {source_rows}"
                if source_workbooks:
                        if source_rows:
                                meta_text += " | "
                        meta_text += f"sources: {source_workbooks}"
                meta_text += "</div>"

        chips_html = "".join(meta_bits)

        if child_nodes:
                children_html = "".join(_tree_node_html(child, depth=depth + 1) for child in child_nodes)
                return (
                        f"<details class='tree-node'{open_attr}>"
                        f"<summary><span class='node-title'>{title}</span><span class='node-summary'>{chips_html}</span></summary>"
                        f"{meta_text}"
                        f"<div class='node-children'>{children_html}</div>"
                        f"</details>"
                )

        return (
                "<div class='tree-leaf'>"
                f"<div class='leaf-summary'><span class='node-title'>{title}</span><span class='node-summary'>{chips_html}</span></div>"
                f"{meta_text}"
                "</div>"
        )


def _render_tree_panel(node: dict, *, field: str, source_contract: dict) -> str:
        generated_at = html.escape(str(source_contract.get("generated_at_utc", "n/a")), quote=True)
        dataset = html.escape(str(source_contract.get("dataset", "n/a")), quote=True)
        required_sheet = html.escape(str(source_contract.get("source_sheet_required", "n/a")), quote=True)
        hierarchy = html.escape(str(source_contract.get("hierarchy_required", "n/a")), quote=True)
        body = _tree_node_html(node)
        return f"""
<style>
    :root {{ color-scheme: light; }}
    .page-shell {{
        max-width: 1460px;
        margin: 0 auto;
        padding: 6px 2px 2px 2px;
        font-family: Inter, "Segoe UI", Arial, sans-serif;
        color: #0f172a;
    }}
    .hero {{
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 12px 18px;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 14px 16px;
        background: rgba(255, 255, 255, 0.95);
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
        margin-bottom: 14px;
    }}
    .eyebrow {{
        color: #0f766e;
        font-size: 11px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 6px;
        font-weight: 700;
    }}
    .hero h2 {{
        margin: 0;
        font-size: 24px;
        line-height: 1.1;
        letter-spacing: -0.03em;
    }}
    .subtitle {{
        margin: 8px 0 0 0;
        color: #475569;
        font-size: 13px;
        max-width: 72ch;
    }}
    .hero-meta {{
        display: grid;
        grid-template-columns: repeat(2, minmax(160px, 1fr));
        gap: 10px;
        align-content: start;
    }}
    .meta-card {{
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        background: #f8fafc;
        padding: 10px 12px;
        min-width: 160px;
    }}
    .meta-label {{
        color: #64748b;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
        font-weight: 700;
    }}
    .meta-value {{
        font-size: 13px;
        color: #0f172a;
        line-height: 1.35;
    }}
    #trees {{ display: grid; gap: 14px; }}
    .field-card {{
        border: 1px solid #dbe4f0;
        border-radius: 18px;
        padding: 14px;
        background: rgba(255, 255, 255, 0.96);
        box-shadow: 0 8px 30px rgba(15, 23, 42, 0.05);
    }}
    .field-header {{
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 8px 14px;
        align-items: baseline;
        margin-bottom: 12px;
    }}
    .field-header h3 {{ margin: 0; font-size: 19px; letter-spacing: -0.02em; }}
    .field-summary {{ margin: 6px 0 0 0; color: #475569; font-size: 13px; }}
    .field-note {{
        color: #0f766e;
        font-size: 12px;
        padding: 8px 10px;
        border-radius: 999px;
        background: #ecfeff;
        border: 1px solid #a5f3fc;
        white-space: nowrap;
    }}
    .tree-shell {{
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        background: #ffffff;
        padding: 10px;
    }}
    details.tree-node, .tree-leaf {{
        margin: 0 0 10px 0;
        border-left: 2px solid #dbeafe;
        padding-left: 12px;
    }}
    details.tree-node > summary {{
        list-style: none;
        cursor: pointer;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
        border: 1px solid #dbeafe;
        border-radius: 14px;
        padding: 10px 12px;
        background: linear-gradient(180deg, #f8fbff 0%, #eff6ff 100%);
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
    }}
    details.tree-node > summary::-webkit-details-marker {{ display: none; }}
    details.tree-node > summary::marker {{ content: ""; }}
    details.tree-node[open] > summary {{
        background: linear-gradient(180deg, #f0f9ff 0%, #e0f2fe 100%);
    }}
    .tree-leaf {{
        border-left-style: dashed;
        padding: 10px 0 0 12px;
    }}
    .leaf-summary {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 10px 12px;
        background: #fcfdff;
    }}
    .node-title {{
        font-weight: 700;
        font-size: 13px;
        color: #0f172a;
    }}
    .node-summary {{
        display: inline-flex;
        flex-wrap: wrap;
        gap: 6px;
    }}
    .node-chip {{
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        background: #e0f2fe;
        color: #075985;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 700;
        white-space: nowrap;
    }}
    .node-meta {{
        margin: 8px 0 0 10px;
        color: #64748b;
        font-size: 11px;
        line-height: 1.4;
    }}
    .node-children {{
        margin: 10px 0 0 12px;
        padding-left: 12px;
        border-left: 1px solid #dbeafe;
    }}
    @media (max-width: 720px) {{
        .hero-meta {{ grid-template-columns: 1fr; }}
        .field-note {{ white-space: normal; }}
    }}
</style>
<div class="page-shell">
    <div class="hero">
        <div>
            <div class="eyebrow">WBS Tree</div>
            <h2>Expandable cost lineage</h2>
            <p class="subtitle">Dashboard Structured.Cost rows, split by field. Use the selectors above to focus a branch, then expand nodes to inspect the L1 → L5 path.</p>
        </div>
        <div class="hero-meta">
            <div class="meta-card">
                <div class="meta-label">Generated at UTC</div>
                <div class="meta-value">{generated_at}</div>
            </div>
            <div class="meta-card">
                <div class="meta-label">Dataset</div>
                <div class="meta-value">{dataset}</div>
            </div>
            <div class="meta-card">
                <div class="meta-label">Required sheet</div>
                <div class="meta-value">{required_sheet}</div>
            </div>
            <div class="meta-card">
                <div class="meta-label">Hierarchy contract</div>
                <div class="meta-value">{hierarchy}</div>
            </div>
        </div>
    </div>
    <div class="field-card">
        <div class="field-header">
            <div>
                <h3>{html.escape(field)}</h3>
                <p class="field-summary">Selected branch shown as native HTML details so the tree stays visible without browser scripts.</p>
            </div>
            <div class="field-note">sum = descendants; spr = P90 - P10</div>
        </div>
        <div class="tree-shell">{body}</div>
    </div>
</div>
"""


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

    focused_payload = {
        "generated_at_utc": payload.get("generated_at_utc"),
        "source_contract": source_contract,
        "fields": {selected_field: focus_root},
    }
    st.html(_render_tree_panel(focus_root, field=selected_field, source_contract=source_contract), width="stretch")

    st.download_button(
        "Download WBS Tree JSON",
        data=json.dumps(payload, indent=2),
        file_name="wbs_tree_interactive.json",
        mime="application/json",
    )