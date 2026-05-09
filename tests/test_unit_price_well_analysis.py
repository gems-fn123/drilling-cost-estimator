from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "data" / "processed" / "unit_price_history_context.csv"
WELL_PROFILE = ROOT / "data" / "processed" / "unit_price_well_profile.csv"
BENCHMARK = ROOT / "data" / "processed" / "unit_price_benchmark.csv"
SERVICE_BANDS = ROOT / "data" / "processed" / "service_time_band_reference.csv"
REPORT = ROOT / "reports" / "unit_price_well_analysis.md"


class TestUnitPriceWellAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "-m", "src.modeling.unit_price_history_pipeline"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "-m", "src.modeling.unit_price_well_analysis"], cwd=ROOT, check=True)

    def test_well_context_contains_active_operational_days(self) -> None:
        with CONTEXT.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(rows)
        self.assertIn("active_operational_days", rows[0])

    def test_well_profile_has_standard_assumption_and_rate_fields(self) -> None:
        with WELL_PROFILE.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {
            "field",
            "campaign_canonical",
            "well_canonical",
            "estimator_well_type",
            "active_operational_days",
            "service_time_band",
            "active_day_rate_usd_per_day",
            "depth_rate_usd_per_ft",
            "total_direct_well_cost_usd",
        }
        self.assertTrue(required.issubset(rows[0].keys()))
        self.assertTrue(all(row["estimator_well_type"] == "Standard-J" for row in rows))

    def test_service_bands_are_generated_for_all_fields(self) -> None:
        with SERVICE_BANDS.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual({row["field"] for row in rows}, {"DARAJAT", "SALAK", "WAYANG_WINDU"})
        self.assertTrue(all(row["fast_rule"] and row["careful_rule"] for row in rows))

    def test_benchmarks_cover_active_day_and_depth_rates(self) -> None:
        with BENCHMARK.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        pairs = {(row["field"], row["pricing_basis"]) for row in rows}
        for field in {"DARAJAT", "SALAK", "WAYANG_WINDU"}:
            self.assertIn((field, "active_day_rate"), pairs)
            self.assertIn((field, "depth_rate"), pairs)
            self.assertIn((field, "total_direct_well_cost"), pairs)

    def test_report_is_written(self) -> None:
        self.assertTrue(REPORT.exists())
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("Service-Time Bands", text)
        self.assertIn("Direct Well Cost Mix", text)


if __name__ == "__main__":
    unittest.main()
