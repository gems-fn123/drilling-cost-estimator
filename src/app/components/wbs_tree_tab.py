from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.modeling.wbs_tree_diagram import (
    WBS_TREE_COMBINED_JSON,
    build_wbs_tree_from_excel_sheet,
    load_wbs_tree_payload,
    render_wbs_tree_html,
)


def _normalize_input_path(value: str) -> str:
    text = (value or "").strip().strip('"').strip("'")
    if not text:
        return ""
    return os.path.expandvars(os.path.expanduser(text))


def _excel_files_in_folder(folder: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.xlsx", "*.xlsm", "*.xls"):
        files.extend(folder.glob(pattern))
    return sorted((path for path in files if path.is_file()), key=lambda p: p.name.lower())


def _resolve_local_source_path(excel_path: str, selected_folder_name: str, folder_files: list[Path]) -> Path | None:
    resolved_excel = _normalize_input_path(excel_path)
    if resolved_excel:
        candidate = Path(resolved_excel)
        if candidate.is_dir():
            return candidate / selected_folder_name if selected_folder_name else None
        return candidate

    if selected_folder_name and folder_files:
        return next((path for path in folder_files if path.name == selected_folder_name), None)
    return None


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


def _render_tree_node(node: dict) -> None:
    label = (
        f"{node.get('node_label', '')} | sum={node.get('sum_usd', 0):,.2f} | "
        f"spr={node.get('spread_usd', 0):,.2f} | r={node.get('sample_row_count', 0)}"
    )

    expanded = node.get("level", 0) <= 1
    with st.expander(label, expanded=expanded):
        st.caption(
            f"c={node.get('campaign_count', 0)} | "
            f"src={node.get('source_row_count', 0)} | "
            f"p10={node.get('p10_usd', 0):,.2f} | p90={node.get('p90_usd', 0):,.2f}"
        )

        sample_ids = node.get("source_row_ids_sample", [])
        if sample_ids:
            st.caption(f"source_row_ids(sample): {', '.join(sample_ids[:8])}")

        for child in node.get("children", []):
            _render_tree_node(child)


def _render_field_tree(field: str, tree: dict) -> None:
    st.markdown(
        f"### {field} | r={tree.get('sample_row_count', 0)} | "
        f"sum={tree.get('sum_usd', 0):,.2f} | spr={tree.get('spread_usd', 0):,.2f}"
    )
    _render_tree_node(tree)


def render_wbs_tree_tab() -> None:
    st.subheader("WBS TREE")
    st.caption("Load Excel and open the tree.")

    col_folder, col_path, col_sheet = st.columns([2, 2, 1])
    with col_folder:
        folder_path = st.text_input("Local windows folder path", value="", placeholder="e.g. F:\\Data\\Drilling")
    with col_path:
        excel_path = st.text_input("Excel file path", value="", placeholder="e.g. F:\\path\\20260327_WBS_Data.xlsx")
    with col_sheet:
        sheet_name = st.text_input("Sheet name", value="Data.Summary")

    resolved_folder = _normalize_input_path(folder_path)
    folder_files: list[Path] = []
    selected_folder_name = ""
    if resolved_folder:
        folder_obj = Path(resolved_folder)
        if folder_obj.exists() and folder_obj.is_dir():
            folder_files = _excel_files_in_folder(folder_obj)
            if folder_files:
                selected_folder_name = st.selectbox(
                    "Excel file from local folder",
                    options=["", *[path.name for path in folder_files]],
                    index=0,
                )
            else:
                st.info("No .xlsx/.xlsm/.xls files found in the provided folder.")
        else:
            st.warning("Local windows folder path does not exist or is not a directory.")

            uploaded = st.file_uploader("Or upload Excel file (.xlsx/.xlsm/.xls)", type=["xlsx", "xlsm", "xls"])

    load_btn = st.button("Load Excel", type="primary")

    if load_btn:
        temp_path: Path | None = None
        try:
            source_path = _resolve_local_source_path(excel_path, selected_folder_name, folder_files)

            # Prefer explicit local-path input. Upload is fallback only when no local source is resolved.
            if source_path is None and uploaded is not None:
                upload_suffix = Path(getattr(uploaded, "name", "uploaded.xlsx")).suffix.lower()
                if upload_suffix not in {".xlsx", ".xlsm", ".xls"}:
                    upload_suffix = ".xlsx"
                with tempfile.NamedTemporaryFile(delete=False, suffix=upload_suffix) as tmp:
                    tmp.write(uploaded.getvalue())
                    temp_path = Path(tmp.name)
                source_path = temp_path

            if source_path is None:
                raise ValueError("Provide Excel file path, local folder + selected file, or upload a file.")

            if not source_path.exists():
                raise FileNotFoundError(f"Excel file not found: {source_path}")

            if source_path.suffix.lower() not in {".xlsx", ".xlsm", ".xls"}:
                raise ValueError("Only .xlsx/.xlsm/.xls files are supported by this loader.")

            payload = build_wbs_tree_from_excel_sheet(source_path, sheet_name=sheet_name.strip() or "Data.Summary")
            st.session_state["wbs_tree_payload"] = payload
            st.success("Excel sheet loaded and WBS tree generated.")
        except Exception as exc:
            st.error(f"Excel load failed: {exc}")
        finally:
            if temp_path is not None and temp_path.exists():
                os.remove(temp_path)

    if "wbs_tree_payload" not in st.session_state and WBS_TREE_COMBINED_JSON.exists():
        try:
            st.session_state["wbs_tree_payload"] = load_wbs_tree_payload()
        except Exception:
            pass

    payload = st.session_state.get("wbs_tree_payload")
    if not payload:
        st.info("No tree loaded yet. Use Load Excel.")
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