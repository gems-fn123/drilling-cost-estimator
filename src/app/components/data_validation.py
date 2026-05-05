"""Data contract validation for uploaded files.

Checks that uploaded files contain the expected sheets and column headers
required by the ETL pipeline before proceeding to artifact building.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Expected data contracts for the pipeline
# Each entry: (sheet_name, required_headers, description)
DASHBOARD_WORKBOOK_CONTRACT = [
    (
        "Structured.Cost",
        ["Asset", "Campaign", "Level 2", "Level 3", "Level 4", "Level 5", "Well", "Actual Cost USD"],
        "Primary cost data at WBS Level 5 granularity",
    ),
    (
        "General.Camp.Data",
        ["Asset", "Campaign", "WBS CODE", "Well Name Actual", "Well Name SAP", "Well Name Alt 1", "Well Name Alt 2"],
        "Campaign & well metadata with depth/duration context",
    ),
    (
        "DashBoard.Tab.Template",
        ["Asset", "Campaign", "Well"],
        "Dashboard template with well-to-campaign assignments",
    ),
    (
        "Check.Total",
        ["Row Labels", "Sum of Actual Cost USD"],
        "Actual cost totals by campaign for reconciliation",
    ),
]

PRIMARY_WORKBOOK_CONTRACT = [
    (
        "Data.Summary",
        ["Campaign", "Well Name"],
        "Campaign-level summary with well assignments",
    ),
    (
        "WellView.Data",
        ["Drilling Campaign", "Well Name SAP"],
        "WellView operational data source",
    ),
]

# Minimum requirements: at least one workbook must pass validation
MINIMUM_VIABLE_CONTRACTS = {
    "dashboard": {
        "required_sheets": ["Structured.Cost", "General.Camp.Data"],
        "description": "Dashboard-driven unit price pipeline (primary path)",
    },
    "primary": {
        "required_sheets": ["Data.Summary"],
        "description": "Legacy WBS data pipeline (fallback path)",
    },
}


@dataclass
class SheetValidationResult:
    sheet_name: str
    found: bool
    required_headers: list[str]
    found_headers: list[str] = field(default_factory=list)
    missing_headers: list[str] = field(default_factory=list)
    extra_headers: list[str] = field(default_factory=list)
    description: str = ""
    row_count: int = 0

    @property
    def headers_valid(self) -> bool:
        return self.found and len(self.missing_headers) == 0


@dataclass
class FileValidationResult:
    file_name: str
    file_path: Path
    readable: bool
    error_message: str = ""
    sheet_results: list[SheetValidationResult] = field(default_factory=list)
    detected_type: str = ""  # "dashboard", "primary", or "unknown"
    pipeline_ready: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def valid_sheet_count(self) -> int:
        return sum(1 for s in self.sheet_results if s.headers_valid)

    @property
    def total_sheets_checked(self) -> int:
        return len(self.sheet_results)


def _normalize_header(text: str) -> str:
    """Normalize a header string for fuzzy matching."""
    import re
    return re.sub(r"[^a-z0-9]+", "", (text or "").strip().lower())


def _find_header_row(rows: list[list[str]], required_headers: list[str], max_scan: int = 50) -> tuple[int, list[str]]:
    """Find the row index containing the required headers and return found headers."""
    normalized_required = [_normalize_header(h) for h in required_headers]

    for i, row in enumerate(rows[:max_scan]):
        normalized_row = [_normalize_header(c) for c in row]
        if all(req in normalized_row for req in normalized_required):
            # Return the actual header values from this row
            return i, [c.strip() for c in row if c.strip()]

    return -1, []


def validate_excel_file(file_path: Path, sheets_data: dict[str, list[list[str]]]) -> FileValidationResult:
    """Validate an Excel file against known data contracts."""
    result = FileValidationResult(
        file_name=file_path.name,
        file_path=file_path,
        readable=True,
    )

    available_sheets = set(sheets_data.keys())

    # Try dashboard workbook contract
    dashboard_matches = 0
    for sheet_name, required_headers, description in DASHBOARD_WORKBOOK_CONTRACT:
        if sheet_name in available_sheets:
            rows = sheets_data[sheet_name]
            header_idx, found_headers = _find_header_row(rows, required_headers)

            normalized_required = {_normalize_header(h) for h in required_headers}
            normalized_found = {_normalize_header(h) for h in found_headers}

            missing = [h for h in required_headers if _normalize_header(h) not in normalized_found]
            extra = [h for h in found_headers if _normalize_header(h) not in normalized_required]
            row_count = len(rows) - (header_idx + 1) if header_idx >= 0 else 0

            sheet_result = SheetValidationResult(
                sheet_name=sheet_name,
                found=True,
                required_headers=required_headers,
                found_headers=found_headers,
                missing_headers=missing if header_idx >= 0 else required_headers,
                extra_headers=extra,
                description=description,
                row_count=row_count,
            )
            result.sheet_results.append(sheet_result)
            if sheet_result.headers_valid:
                dashboard_matches += 1
        else:
            result.sheet_results.append(SheetValidationResult(
                sheet_name=sheet_name,
                found=False,
                required_headers=required_headers,
                missing_headers=required_headers,
                description=description,
            ))

    # Try primary workbook contract
    primary_matches = 0
    for sheet_name, required_headers, description in PRIMARY_WORKBOOK_CONTRACT:
        if sheet_name in available_sheets:
            rows = sheets_data[sheet_name]
            header_idx, found_headers = _find_header_row(rows, required_headers)

            normalized_required = {_normalize_header(h) for h in required_headers}
            normalized_found = {_normalize_header(h) for h in found_headers}

            missing = [h for h in required_headers if _normalize_header(h) not in normalized_found]
            row_count = len(rows) - (header_idx + 1) if header_idx >= 0 else 0

            sheet_result = SheetValidationResult(
                sheet_name=sheet_name,
                found=True,
                required_headers=required_headers,
                found_headers=found_headers,
                missing_headers=missing if header_idx >= 0 else required_headers,
                description=description,
                row_count=row_count,
            )
            result.sheet_results.append(sheet_result)
            if sheet_result.headers_valid:
                primary_matches += 1
        else:
            result.sheet_results.append(SheetValidationResult(
                sheet_name=sheet_name,
                found=False,
                required_headers=required_headers,
                missing_headers=required_headers,
                description=description,
            ))

    # Determine file type and pipeline readiness
    dashboard_min = MINIMUM_VIABLE_CONTRACTS["dashboard"]["required_sheets"]
    primary_min = MINIMUM_VIABLE_CONTRACTS["primary"]["required_sheets"]

    dashboard_ready = all(
        any(s.sheet_name == name and s.headers_valid for s in result.sheet_results)
        for name in dashboard_min
    )
    primary_ready = all(
        any(s.sheet_name == name and s.headers_valid for s in result.sheet_results)
        for name in primary_min
    )

    if dashboard_ready:
        result.detected_type = "dashboard"
        result.pipeline_ready = True
    elif primary_ready:
        result.detected_type = "primary"
        result.pipeline_ready = True
    else:
        result.detected_type = "unknown"
        result.pipeline_ready = False
        result.warnings.append(
            "File does not match any known data contract. "
            "Expected either a Dashboard workbook (with Structured.Cost + General.Camp.Data sheets) "
            "or a Primary WBS workbook (with Data.Summary sheet)."
        )

    # Add warnings for partially matching files
    if result.detected_type == "dashboard" and dashboard_matches < len(DASHBOARD_WORKBOOK_CONTRACT):
        missing_optional = [
            s.sheet_name for s in result.sheet_results
            if not s.headers_valid and s.sheet_name not in dashboard_min
        ]
        if missing_optional:
            result.warnings.append(
                f"Optional sheets missing or incomplete: {', '.join(missing_optional)}. "
                "Pipeline will still run but some features (e.g., reconciliation totals) may be limited."
            )

    return result


def validate_csv_file(file_path: Path) -> FileValidationResult:
    """Validate a CSV file – check it's readable and has content."""
    import csv

    result = FileValidationResult(
        file_name=file_path.name,
        file_path=file_path,
        readable=False,
        detected_type="csv_supplement",
    )

    try:
        with file_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                result.error_message = "CSV file is empty (no header row found)."
                return result

            row_count = sum(1 for _ in reader)

        result.readable = True
        result.pipeline_ready = True
        result.sheet_results.append(SheetValidationResult(
            sheet_name="(single table)",
            found=True,
            required_headers=[],
            found_headers=[h.strip() for h in headers if h.strip()],
            description="CSV data table",
            row_count=row_count,
        ))
    except Exception as exc:
        result.error_message = f"Could not read CSV: {exc}"

    return result
