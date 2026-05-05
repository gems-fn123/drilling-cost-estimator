"""Upload page for dashboard-only estimator refresh."""

from __future__ import annotations

import shutil
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
UPLOAD_DIR = ROOT / "data" / "uploads"
RAW_DIR = ROOT / "data" / "raw"

DASHBOARD_WORKBOOK_NAME = "20260422_Data for Dashboard.xlsx"
SUPPORTED_EXTENSIONS = {".xlsx"}


def _ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def _save_uploaded_file(uploaded_file) -> Path:
    _ensure_dirs()
    dest = UPLOAD_DIR / uploaded_file.name
    dest.write_bytes(uploaded_file.getvalue())
    return dest


def _read_sheets_for_validation(file_path: Path) -> dict[str, list[list[str]]] | None:
    try:
        import openpyxl

        wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
        sheets_data: dict[str, list[list[str]]] = {}
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= 50:
                    break
                rows.append([str(cell).strip() if cell is not None else "" for cell in row])
            sheets_data[sheet_name] = rows
        wb.close()
        return sheets_data
    except Exception:
        return None


def _preview_excel_sheet(file_path: Path, sheet_name: str) -> None:
    try:
        import openpyxl

        wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
        if sheet_name not in wb.sheetnames:
            wb.close()
            return

        ws = wb[sheet_name]
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= 6:
                break
            rows.append([str(cell) if cell is not None else "" for cell in row])
        wb.close()

        if rows:
            st.markdown(f"**{sheet_name}** — Preview (first {len(rows)} rows)")
            st.dataframe(rows, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.warning(f"Could not preview `{sheet_name}`: {exc}")


def _copy_to_raw_dashboard(file_path: Path) -> Path:
    _ensure_dirs()
    for existing in RAW_DIR.glob("*"):
        if existing.is_file() and existing.suffix.lower() in SUPPORTED_EXTENSIONS:
            existing.unlink()
    dest = RAW_DIR / DASHBOARD_WORKBOOK_NAME
    shutil.copy2(file_path, dest)
    return dest


def render_upload_page() -> None:
    st.markdown("# DATA UPLOAD")
    st.markdown(
        "Upload the dashboard workbook used by the estimator refresh pipeline. "
        "Only one file is required: **20260422_Data for Dashboard.xlsx** (or same schema with a different filename)."
    )

    _ensure_dirs()
    existing_dashboard = RAW_DIR / DASHBOARD_WORKBOOK_NAME
    if existing_dashboard.exists():
        size_kb = existing_dashboard.stat().st_size / 1024
        st.info(f"Current raw workbook: `{existing_dashboard.name}` ({size_kb:.1f} KB)")

    st.divider()

    uploaded_file = st.file_uploader(
        "Upload dashboard workbook (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=False,
        key="dashboard_workbook_uploader",
        help="This upload replaces the existing raw workbook used by the estimator pipeline.",
    )

    if not uploaded_file:
        st.info("Upload one dashboard workbook to begin.")
        return

    staged_path = _save_uploaded_file(uploaded_file)

    from src.app.components.data_validation import validate_excel_file

    sheets_data = _read_sheets_for_validation(staged_path)
    if sheets_data is None:
        st.error("Could not read workbook. Please upload a valid, unencrypted .xlsx file.")
        return

    validation = validate_excel_file(staged_path, sheets_data)

    if validation.pipeline_ready:
        st.success(f"Workbook validated: **{validation.file_name}**")
    else:
        st.error("Workbook did not pass required dashboard contract checks.")

    for warning in validation.warnings:
        st.warning(warning)

    with st.expander("Validation details", expanded=not validation.pipeline_ready):
        for sr in validation.sheet_results:
            if sr.headers_valid:
                st.markdown(f"  ✓ `{sr.sheet_name}` — {sr.row_count} rows")
            elif sr.found:
                st.markdown(f"  ✗ `{sr.sheet_name}` — Missing headers: {', '.join(sr.missing_headers)}")
            else:
                st.markdown(f"  — `{sr.sheet_name}` — Sheet not found")

    st.divider()
    st.subheader("Preview")
    for sheet_name in ["Structured.Cost", "General.Camp.Data", "NPT.Data", "Check.Total"]:
        _preview_excel_sheet(staged_path, sheet_name)

    st.divider()

    if st.button("CONFIRM & LOAD DATA", type="primary", disabled=not validation.pipeline_ready):
        raw_path = _copy_to_raw_dashboard(staged_path)
        st.session_state["upload_confirmed"] = True
        st.session_state["validation_results"] = [validation]
        st.success(
            f"Loaded dashboard workbook as `{raw_path.name}`. "
            "Proceed to **Build Artifacts** to refresh estimator datasets."
        )
