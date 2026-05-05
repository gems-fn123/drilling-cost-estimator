"""Data contract validation for uploaded files.

Dashboard-only contract:
- expects 20260422_Data for Dashboard.xlsx shape
- no fallback to legacy multi-workbook inputs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

DASHBOARD_WORKBOOK_CONTRACT = [
    (
        "Structured.Cost",
        ["Asset", "Campaign", "Level 2", "Level 3", "Level 4", "Level 5", "Well", "Actual Cost USD"],
        "Primary Level-5 cost data",
    ),
    (
        "General.Camp.Data",
        ["Asset", "Campaign", "WBS CODE", "Well Name Actual", "Well Name SAP", "Well Name Alt 1", "Well Name Alt 2"],
        "Campaign and well metadata",
    ),
]

OPTIONAL_DASHBOARD_SHEETS = [
    ("DashBoard.Tab.Template", ["Asset", "Campaign", "Well"], "Template alias support"),
    ("Check.Total", ["Row Labels", "Sum of Actual Cost USD"], "Campaign total reconciliation"),
    ("NPT.Data", ["Well Name", "Event Reference No.", "Unsch Maj Cat", "Unscheduled Detail", "Dur (Net) (hr)"], "NPT context"),
]

MINIMUM_REQUIRED_SHEETS = ["Structured.Cost", "General.Camp.Data"]


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
    detected_type: str = ""
    pipeline_ready: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def valid_sheet_count(self) -> int:
        return sum(1 for s in self.sheet_results if s.headers_valid)

    @property
    def total_sheets_checked(self) -> int:
        return len(self.sheet_results)


def _normalize_header(text: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "", (text or "").strip().lower())


def _find_header_row(rows: list[list[str]], required_headers: list[str], max_scan: int = 50) -> tuple[int, list[str]]:
    normalized_required = [_normalize_header(h) for h in required_headers]

    for i, row in enumerate(rows[:max_scan]):
        normalized_row = [_normalize_header(c) for c in row]
        if all(req in normalized_row for req in normalized_required):
            return i, [c.strip() for c in row if c.strip()]

    return -1, []


def _validate_sheet(
    *,
    available_sheets: set[str],
    sheets_data: dict[str, list[list[str]]],
    sheet_name: str,
    required_headers: list[str],
    description: str,
) -> SheetValidationResult:
    if sheet_name not in available_sheets:
        return SheetValidationResult(
            sheet_name=sheet_name,
            found=False,
            required_headers=required_headers,
            missing_headers=required_headers,
            description=description,
        )

    rows = sheets_data[sheet_name]
    header_idx, found_headers = _find_header_row(rows, required_headers)
    normalized_required = {_normalize_header(h) for h in required_headers}
    normalized_found = {_normalize_header(h) for h in found_headers}

    missing = [h for h in required_headers if _normalize_header(h) not in normalized_found]
    extra = [h for h in found_headers if _normalize_header(h) not in normalized_required]
    row_count = len(rows) - (header_idx + 1) if header_idx >= 0 else 0

    return SheetValidationResult(
        sheet_name=sheet_name,
        found=True,
        required_headers=required_headers,
        found_headers=found_headers,
        missing_headers=missing if header_idx >= 0 else required_headers,
        extra_headers=extra,
        description=description,
        row_count=row_count,
    )


def validate_excel_file(file_path: Path, sheets_data: dict[str, list[list[str]]]) -> FileValidationResult:
    result = FileValidationResult(
        file_name=file_path.name,
        file_path=file_path,
        readable=True,
        detected_type="dashboard",
    )

    available_sheets = set(sheets_data.keys())

    for sheet_name, required_headers, description in DASHBOARD_WORKBOOK_CONTRACT:
        result.sheet_results.append(
            _validate_sheet(
                available_sheets=available_sheets,
                sheets_data=sheets_data,
                sheet_name=sheet_name,
                required_headers=required_headers,
                description=description,
            )
        )

    for sheet_name, required_headers, description in OPTIONAL_DASHBOARD_SHEETS:
        result.sheet_results.append(
            _validate_sheet(
                available_sheets=available_sheets,
                sheets_data=sheets_data,
                sheet_name=sheet_name,
                required_headers=required_headers,
                description=description,
            )
        )

    result.pipeline_ready = all(
        any(s.sheet_name == required and s.headers_valid for s in result.sheet_results)
        for required in MINIMUM_REQUIRED_SHEETS
    )

    if not result.pipeline_ready:
        result.detected_type = "unknown"
        result.warnings.append(
            "Workbook does not match the required dashboard contract. "
            "Required sheets: Structured.Cost and General.Camp.Data."
        )

    missing_optional = [
        s.sheet_name
        for s in result.sheet_results
        if not s.headers_valid and s.sheet_name not in MINIMUM_REQUIRED_SHEETS
    ]
    if result.pipeline_ready and missing_optional:
        result.warnings.append(
            f"Optional sheets missing or incomplete: {', '.join(missing_optional)}. "
            "Pipeline can run, but some derived context/reconciliation artifacts may be limited."
        )

    return result


def validate_csv_file(file_path: Path) -> FileValidationResult:
    import csv

    result = FileValidationResult(
        file_name=file_path.name,
        file_path=file_path,
        readable=False,
        detected_type="unsupported",
        pipeline_ready=False,
    )

    try:
        with file_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                result.error_message = "CSV file is empty (no header row found)."
                return result
    except Exception as exc:
        result.error_message = f"Could not read CSV: {exc}"
        return result

    result.readable = True
    result.warnings.append(
        "CSV uploads are accepted for inspection only. Estimator refresh requires the dashboard workbook (.xlsx)."
    )
    return result
