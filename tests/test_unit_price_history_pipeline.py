from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_MAP = ROOT / "data" / "processed" / "canonical_campaign_mapping.csv"
WELL_MASTER = ROOT / "data" / "processed" / "well_master.csv"
SCOPE_REPORT = ROOT / "reports" / "unit_price_scope_coverage.md"
HISTORY_MART = ROOT / "data" / "processed" / "unit_price_history_mart.csv"


class TestUnitPriceHistoryScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "src/io/build_canonical_mappings.py"], cwd=ROOT, check=True)

    def test_campaign_mapping_contains_all_requested_campaigns(self) -> None:
        with CAMPAIGN_MAP.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        ids = {row["campaign_id"] for row in rows}
        self.assertTrue(
            {
                "DARAJAT_2019",
                "DARAJAT_2022",
                "DARAJAT_2023_2024",
                "SALAK_2021",
                "SALAK_2025_2026",
                "WAYANG_WINDU_2018",
                "WAYANG_WINDU_2021",
            }.issubset(ids)
        )

    def test_all_requested_campaigns_are_estimator_in_scope(self) -> None:
        with CAMPAIGN_MAP.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        by_id = {row["campaign_id"]: row for row in rows}
        for campaign_id in [
            "DARAJAT_2019",
            "DARAJAT_2022",
            "DARAJAT_2023_2024",
            "SALAK_2021",
            "SALAK_2025_2026",
            "WAYANG_WINDU_2018",
            "WAYANG_WINDU_2021",
        ]:
            self.assertEqual(by_id[campaign_id]["include_for_estimator"], "yes")

    def test_well_master_contains_dashboard_scoped_wells(self) -> None:
        with WELL_MASTER.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        keys = {(row["campaign_id"], row["well_canonical"]) for row in rows}
        expected = {
            ("DARAJAT_2019", "DRJ-44"),
            ("DARAJAT_2019", "DRJ-48"),
            ("SALAK_2021", "AWI 16-8"),
            ("WAYANG_WINDU_2018", "MBA-6"),
            ("WAYANG_WINDU_2021", "MBI-1"),
        }
        self.assertTrue(expected.issubset(keys))

    def test_scope_report_is_written(self) -> None:
        self.assertTrue(SCOPE_REPORT.exists())
        text = SCOPE_REPORT.read_text(encoding="utf-8")
        self.assertIn("WAYANG_WINDU_2018", text)
        self.assertIn("WAYANG_WINDU_2021", text)

class TestUnitPriceHistoryMart(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "src/io/build_canonical_mappings.py"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "src/modeling/unit_price_history_pipeline.py"], cwd=ROOT, check=True)

    def test_unit_price_history_mart_has_three_fields(self) -> None:
        with HISTORY_MART.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        fields = {row["field"] for row in rows}
        self.assertEqual(fields, {"DARAJAT", "SALAK", "WAYANG_WINDU"})

    def test_history_mart_preserves_workbook_lineage(self) -> None:
        with HISTORY_MART.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {"source_workbook", "source_sheet", "source_row_key", "pricing_basis", "unit_price_basis"}
        self.assertTrue(required.issubset(rows[0].keys()))
        self.assertEqual(rows[0]["source_workbook"], "20260422_Data for Dashboard.xlsx")

    def test_history_mart_contains_active_day_and_depth_pricing_rows(self) -> None:
        with HISTORY_MART.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        pricing_bases = {row["pricing_basis"] for row in rows}
        self.assertIn("active_day_rate", pricing_bases)
        self.assertIn("depth_rate", pricing_bases)
        self.assertIn("campaign_scope_benchmark", pricing_bases)


if __name__ == "__main__":
    unittest.main()
