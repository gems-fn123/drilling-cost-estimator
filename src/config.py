"""Central path and constant definitions for the drilling-cost-estimator package."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REFERENCE_DIR = ROOT / "data" / "reference"
REPORTS = ROOT / "reports"

DASHBOARD_WORKBOOK = "20260422_Data for Dashboard.xlsx"

FIELD_MAP = {"DRJ": "DARAJAT", "SLK": "SALAK", "WW": "WAYANG_WINDU"}
VALID_FIELDS = frozenset({"DARAJAT", "SALAK", "WAYANG_WINDU"})
VALID_FIELDS_ESTIMATOR = frozenset({"DARAJAT", "SALAK"})

CAMPAIGN_LABEL_TO_CODE: dict[str, str] = {
    "DRJ 2022": "E530-30101-D225301",
    "DRJ 2023": "E530-30101-D235301",
    "SLK 2025": "E540-30101-D245401",
    "DARAJAT CAMPAIGN 2019": "E530-30101-D19001",
    "SALAK CAMPAIGN 2021": "E540-30101-D20001",
    "DRJ - 2019": "E530-30101-D19001",
    "DRJ - 2022": "E530-30101-D225301",
    "DRJ - 2024": "E530-30101-D235301",
    "SLK - 2021": "E540-30101-D20001",
    "SLK - 2025": "E540-30101-D245401",
    "WW - 2018": "E500-2-0-8501-185003",
    "WW - 2021": "E500-30101-D205011",
    "WAYANG WINDU CAMPAIGN 2018/2019": "E500-2-0-8501-185003",
    "WAYANG WINDU CAMPAIGN 2020/2021": "E500-30101-D205011",
}
