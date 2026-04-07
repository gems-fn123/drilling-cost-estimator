from __future__ import annotations

import csv
import subprocess
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "data" / "processed" / "dashboard_x_summary_metrics.csv"
WELL_PATH = ROOT / "data" / "processed" / "dashboard_x_cost_by_well.csv"
L3_PATH = ROOT / "data" / "processed" / "dashboard_x_l3_breakdown.csv"
REPORT_PATH = ROOT / "reports" / "dashboard_x_snapshot_report.md"


class TestDashboardSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(["python", "src/cleaning/wbs_lv5_driver_alignment.py"], cwd=ROOT, check=True)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_dashboard_snapshot_artifacts_exist(self) -> None:
        for path in [SUMMARY_PATH, WELL_PATH, L3_PATH, REPORT_PATH]:
            self.assertTrue(path.exists(), f"Missing dashboard snapshot artifact: {path}")

    def test_dashboard_snapshot_row_contract(self) -> None:
        summary_rows = self.read_csv(SUMMARY_PATH)
        well_rows = self.read_csv(WELL_PATH)
        l3_rows = self.read_csv(L3_PATH)

        self.assertEqual(len(summary_rows), 8)
        self.assertGreaterEqual(len(well_rows), 8)
        self.assertGreaterEqual(len(l3_rows), 10)

        self.assertTrue(all(row["source_sheet"] == "Dashboard_x" for row in summary_rows))
        self.assertTrue(all(row["source_sheet"] == "Dashboard_x" for row in well_rows))
        self.assertTrue(all(row["source_sheet"] == "Dashboard_x" for row in l3_rows))

        self.assertTrue(all(row["source_row_id"] for row in summary_rows))
        self.assertTrue(all(row["source_row_id"] for row in well_rows))
        self.assertTrue(all(row["source_row_id"] for row in l3_rows))

        self.assertEqual(summary_rows[0]["field"], "SALAK")


if __name__ == "__main__":
    unittest.main()