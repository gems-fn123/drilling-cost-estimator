from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENRICHED = ROOT / "data" / "processed" / "npt_event_enriched.csv"
SUMMARY = ROOT / "data" / "processed" / "npt_contribution_summary.csv"
PENALTY = ROOT / "data" / "processed" / "npt_penalty_reference.csv"
REPORT = ROOT / "reports" / "unit_price_npt_contribution.md"


class TestUnitPriceNptAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "-m", "src.modeling.unit_price_well_analysis"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "-m", "src.modeling.unit_price_npt_analysis"], cwd=ROOT, check=True)

    def test_enriched_events_are_written(self) -> None:
        with ENRICHED.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {
            "field",
            "campaign_canonical",
            "well_base_canonical",
            "analysis_well_key",
            "event_major_category",
            "event_detail",
            "event_duration_days",
            "mapping_status",
            "exclude_from_estimator_pool",
        }
        self.assertTrue(rows)
        self.assertTrue(required.issubset(rows[0].keys()))

    def test_summary_has_supported_field_rows(self) -> None:
        with SUMMARY.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {
            "field",
            "group_level",
            "event_major_category",
            "total_npt_days",
            "share_of_field_npt_days",
            "category_to_total_npt_r2",
            "support_status",
        }
        self.assertTrue(required.issubset(rows[0].keys()))
        supported_fields = {row["field"] for row in rows if row["support_status"] == "supported"}
        self.assertTrue({"DARAJAT", "SALAK"}.issubset(supported_fields))

    def test_penalty_reference_covers_all_three_fields(self) -> None:
        with PENALTY.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {
            "field",
            "event_major_category",
            "penalty_cost_p50_usd",
            "penalty_pct_of_median_direct_well_cost",
            "support_status",
        }
        self.assertTrue(required.issubset(rows[0].keys()))
        covered_fields = {row["field"] for row in rows}
        self.assertEqual(covered_fields, {"DARAJAT", "SALAK", "WAYANG_WINDU"})
        ww_rows = [row for row in rows if row["field"] == "WAYANG_WINDU" and row["support_status"] == "supported"]
        self.assertTrue(ww_rows)

    def test_report_is_written(self) -> None:
        self.assertTrue(REPORT.exists())
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("Top Major Contributors", text)
        self.assertIn("WAYANG_WINDU", text)


if __name__ == "__main__":
    unittest.main()
