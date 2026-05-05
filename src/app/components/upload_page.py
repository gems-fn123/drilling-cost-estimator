"""Upload page – landing page for uploading raw data files."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
UPLOAD_DIR = ROOT / "data" / "uploads"
RAW_DIR = ROOT / "data" / "raw"

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
ZIP_MAGIC = b"PK\x03\x04"
OLE_MAGIC = b"\xD0\xCF\x11\xE0"


def _ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def _save_uploaded_file(uploaded_file) -> Path:
    """Save an uploaded file to the uploads directory."""
    _ensure_dirs()
    dest = UPLOAD_DIR / uploaded_file.name
    dest.write_bytes(uploaded_file.getvalue())
    return dest


def _decrypt_ole_to_temp(file_path: Path) -> Optional[Path]:
    """Attempt to decrypt an OLE2-encrypted xlsx file using msoffcrypto-tool."""
    try:
        import io
        import msoffcrypto

        with file_path.open("rb") as f:
            office_file = msoffcrypto.OfficeFile(f)
            office_file.load_key(password="VelvetSweatshop")  # Default Excel encryption password
            decrypted = io.BytesIO()
            office_file.decrypt(decrypted)

        decrypted_path = file_path.parent / f"_decrypted_{file_path.name}"
        decrypted_path.write_bytes(decrypted.getvalue())
        return decrypted_path
    except Exception:
        # Try with empty password
        try:
            import io
            import msoffcrypto

            with file_path.open("rb") as f:
                office_file = msoffcrypto.OfficeFile(f)
                office_file.load_key(password="")
                decrypted = io.BytesIO()
                office_file.decrypt(decrypted)

            decrypted_path = file_path.parent / f"_decrypted_{file_path.name}"
            decrypted_path.write_bytes(decrypted.getvalue())
            return decrypted_path
        except Exception:
            return None


def _get_sheet_names(file_path: Path) -> list[str]:
    """Read sheet names from an Excel file, handling encrypted files."""
    try:
        # Check file format
        with file_path.open("rb") as f:
            magic = f.read(8)

        actual_path = file_path

        if magic[:4] == OLE_MAGIC:
            # Attempt decryption for password-protected files
            decrypted = _decrypt_ole_to_temp(file_path)
            if decrypted:
                actual_path = decrypted
            else:
                # Check if it's DRM/IRM encrypted (unrecoverable without Windows)
                try:
                    import olefile
                    ole = olefile.OleFileIO(str(file_path))
                    entries = ole.listdir()
                    ole.close()
                    is_drm = any("DRM" in "/".join(e).upper() for e in entries)
                    if is_drm:
                        st.warning(
                            f"File `{file_path.name}` is DRM/IRM encrypted and cannot be read on this platform. "
                            "Please upload an unencrypted version of this file."
                        )
                        return []
                except Exception:
                    pass
                # Try openpyxl directly as last resort
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
                    names = wb.sheetnames
                    wb.close()
                    return names
                except Exception:
                    st.warning(
                        f"File `{file_path.name}` could not be read. "
                        "It may be encrypted or in an unsupported format."
                    )
                    return []

        # Read with openpyxl for modern xlsx
        import openpyxl
        wb = openpyxl.load_workbook(str(actual_path), read_only=True, data_only=True)
        names = wb.sheetnames
        wb.close()

        # Clean up decrypted temp file
        if actual_path != file_path and actual_path.exists():
            actual_path.unlink()

        return names
    except Exception as exc:
        # Fallback: try xlrd for .xls files
        if file_path.suffix.lower() == ".xls":
            try:
                import xlrd
                wb = xlrd.open_workbook(str(file_path))
                return [s.name for s in wb.sheets()]
            except Exception:
                pass
        st.error(f"Could not read sheets from {file_path.name}: {exc}")
        return []


def _copy_to_raw(file_path: Path) -> Path:
    """Copy a confirmed file to the raw data directory."""
    dest = RAW_DIR / file_path.name
    shutil.copy2(file_path, dest)
    return dest


def _read_sheets_for_validation(file_path: Path) -> Optional[dict[str, list[list[str]]]]:
    """Read all sheets from an Excel file for validation. Returns None if unreadable."""
    try:
        with file_path.open("rb") as f:
            magic = f.read(4)

        actual_path = file_path

        if magic == OLE_MAGIC:
            decrypted = _decrypt_ole_to_temp(file_path)
            if decrypted:
                actual_path = decrypted
            else:
                return None  # DRM encrypted, can't validate

        # Read with openpyxl
        import openpyxl
        wb = openpyxl.load_workbook(str(actual_path), read_only=True, data_only=True)
        sheets_data: dict[str, list[list[str]]] = {}
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= 50:  # Only read first 50 rows for header detection
                    break
                rows.append([str(cell).strip() if cell is not None else "" for cell in row])
            sheets_data[sheet_name] = rows
        wb.close()

        if actual_path != file_path and actual_path.exists():
            actual_path.unlink()

        return sheets_data
    except Exception:
        return None


def _unreadable_validation_result(entry: dict):
    """Create a validation result for an unreadable file."""
    from src.app.components.data_validation import FileValidationResult
    return FileValidationResult(
        file_name=entry["name"],
        file_path=entry["path"],
        readable=False,
        error_message=(
            f"File `{entry['name']}` could not be read for validation. "
            "It may be DRM-encrypted or in an unsupported format. "
            "Please upload an unencrypted .xlsx file."
        ),
        detected_type="unreadable",
        pipeline_ready=False,
    )


def render_upload_page() -> None:
    st.markdown("# DATA UPLOAD")
    st.markdown(
        "Upload your raw drilling campaign data files below. "
        "Supported formats: **xlsx**, **xls**, **csv**."
    )

    # Show currently loaded files
    _ensure_dirs()
    existing_raw = sorted(RAW_DIR.glob("*"))
    existing_raw_files = [f for f in existing_raw if f.suffix.lower() in SUPPORTED_EXTENSIONS]

    if existing_raw_files:
        with st.expander(f"Currently loaded raw files ({len(existing_raw_files)})", expanded=False):
            for f in existing_raw_files:
                size_kb = f.stat().st_size / 1024
                st.text(f"  {f.name}  ({size_kb:.1f} KB)")

    st.divider()

    # File uploader
    uploaded_files = st.file_uploader(
        "Upload raw data files",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        key="raw_data_uploader",
        help="Upload one or more Excel or CSV files containing drilling campaign data.",
    )

    if not uploaded_files:
        st.info("Upload one or more files to begin.")
        return

    # Process each uploaded file
    staged_files: list[dict] = []

    for uploaded_file in uploaded_files:
        file_path = _save_uploaded_file(uploaded_file)
        file_ext = file_path.suffix.lower()

        file_entry: dict = {
            "name": uploaded_file.name,
            "path": file_path,
            "extension": file_ext,
            "selected_sheet": None,
            "sheets": [],
        }

        if file_ext in {".xlsx", ".xls"}:
            sheets = _get_sheet_names(file_path)
            file_entry["sheets"] = sheets
        else:
            file_entry["sheets"] = []

        staged_files.append(file_entry)

    # Sheet selection UI
    st.subheader("Sheet Selection")
    st.caption("For Excel files with multiple sheets, select the sheet to use for each file.")

    selections_valid = True
    for idx, entry in enumerate(staged_files):
        if entry["extension"] == ".csv":
            st.markdown(f"**{entry['name']}** — CSV (single table)")
            continue

        sheets = entry["sheets"]
        if not sheets:
            st.warning(f"**{entry['name']}** — No sheets found or file unreadable.")
            selections_valid = False
            continue

        if len(sheets) == 1:
            entry["selected_sheet"] = sheets[0]
            st.markdown(f"**{entry['name']}** — Sheet: `{sheets[0]}` (only sheet)")
        else:
            selected = st.selectbox(
                f"Select sheet for **{entry['name']}**",
                options=sheets,
                key=f"sheet_select_{idx}_{entry['name']}",
            )
            entry["selected_sheet"] = selected

    # Store staged files in session state
    st.session_state["staged_files"] = staged_files

    st.divider()

    # Data contract validation
    st.subheader("Data Validation")
    st.caption("Checking uploaded files against expected data contracts...")

    from src.app.components.data_validation import validate_csv_file, validate_excel_file

    validation_results = []
    all_pipeline_ready = True

    for entry in staged_files:
        if entry["extension"] == ".csv":
            vr = validate_csv_file(entry["path"])
        else:
            # Read file sheets for validation
            sheets_data = _read_sheets_for_validation(entry["path"])
            if sheets_data is not None:
                vr = validate_excel_file(entry["path"], sheets_data)
            else:
                vr = _unreadable_validation_result(entry)
        validation_results.append(vr)
        if not vr.pipeline_ready:
            all_pipeline_ready = False

    # Display validation results
    for vr in validation_results:
        if vr.pipeline_ready:
            status_icon = "\u2705"
            detected_label = f"({vr.detected_type})" if vr.detected_type else ""
            st.markdown(f"{status_icon} **{vr.file_name}** — Pipeline ready {detected_label}")
        else:
            status_icon = "\u274C"
            st.markdown(f"{status_icon} **{vr.file_name}** — Not recognized")

        # Show sheet-level details in expander
        if vr.sheet_results:
            with st.expander(f"Validation details for {vr.file_name}", expanded=not vr.pipeline_ready):
                for sr in vr.sheet_results:
                    if sr.headers_valid:
                        st.markdown(f"  \u2713 `{sr.sheet_name}` — {sr.row_count} rows | {sr.description}")
                    elif sr.found:
                        st.markdown(f"  \u2717 `{sr.sheet_name}` — Missing headers: {', '.join(sr.missing_headers)}")
                    else:
                        st.markdown(f"  \u2014 `{sr.sheet_name}` — Sheet not found")

        for warning in vr.warnings:
            st.warning(warning)

        if vr.error_message:
            st.error(vr.error_message)

    st.divider()

    # Preview section
    st.subheader("Preview")
    for entry in staged_files:
        if entry["extension"] == ".csv":
            _preview_csv(entry["path"])
        elif entry["selected_sheet"]:
            _preview_excel_sheet(entry["path"], entry["selected_sheet"])

    st.divider()

    # Confirm and load button
    if not all_pipeline_ready:
        st.warning(
            "Some files did not pass validation. You can still load them, "
            "but the pipeline may fail or produce incomplete results."
        )

    if st.button("CONFIRM & LOAD DATA", type="primary", disabled=not selections_valid):
        with st.spinner("Copying files to raw data directory..."):
            for entry in staged_files:
                _copy_to_raw(entry["path"])

        st.session_state["upload_confirmed"] = True
        st.session_state["upload_sheet_selections"] = {
            entry["name"]: entry["selected_sheet"] for entry in staged_files
        }
        st.session_state["validation_results"] = validation_results
        st.success(
            f"Loaded {len(staged_files)} file(s) into raw data directory. "
            "Proceed to **Build Artifacts** to generate modelling inputs."
        )


def _preview_csv(file_path: Path) -> None:
    """Show first few rows of a CSV file."""
    import csv as csv_mod

    try:
        with file_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv_mod.reader(f)
            rows = [next(reader) for _ in range(min(6, 100))]
        if rows:
            st.markdown(f"**{file_path.name}** — Preview (first {len(rows)} rows):")
            st.dataframe(rows, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.warning(f"Could not preview {file_path.name}: {exc}")


def _preview_excel_sheet(file_path: Path, sheet_name: str) -> None:
    """Show first few rows of an Excel sheet."""
    try:
        # Check if file needs decryption
        with file_path.open("rb") as f:
            magic = f.read(4)

        actual_path = file_path
        if magic == OLE_MAGIC:
            decrypted = _decrypt_ole_to_temp(file_path)
            if decrypted:
                actual_path = decrypted

        import openpyxl
        wb = openpyxl.load_workbook(str(actual_path), read_only=True, data_only=True)
        if sheet_name not in wb.sheetnames:
            st.warning(f"Sheet `{sheet_name}` not found in {file_path.name}.")
            wb.close()
            return
        ws = wb[sheet_name]
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= 6:
                break
            rows.append([str(cell) if cell is not None else "" for cell in row])
        wb.close()

        # Clean up temp
        if actual_path != file_path and actual_path.exists():
            actual_path.unlink()

        if rows:
            st.markdown(f"**{file_path.name}** → `{sheet_name}` — Preview (first {len(rows)} rows):")
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info(f"Sheet `{sheet_name}` in {file_path.name} appears empty.")
    except Exception as exc:
        st.warning(f"Could not preview {file_path.name} → {sheet_name}: {exc}")
