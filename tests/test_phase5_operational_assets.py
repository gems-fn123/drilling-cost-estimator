from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP_DATASET = ROOT / "data" / "processed" / "phase5_app_dataset.csv"
MONITORING = ROOT / "data" / "processed" / "phase5_monitoring_kpis.csv"
MANIFEST = ROOT / "data" / "processed" / "phase5_operational_manifest.json"
APP_REPORT = ROOT / "reports" / "phase5_app_integration_prerequisites.md"
MONITORING_REPORT = ROOT / "reports" / "phase5_monitoring_skeleton.md"
RUNBOOK = ROOT / "docs" / "refresh_runbook.md"


class TestPhase5OperationalAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(["python", "src/modeling/phase4_preflight_and_baseline.py", "--group-by", "family"], cwd=ROOT, check=True)
        subprocess.run(["python", "src/app/build_phase5_operational_assets.py"], cwd=ROOT, check=True)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def test_phase5_artifacts_exist(self) -> None:
        for path in [APP_DATASET, MONITORING, MANIFEST, APP_REPORT, MONITORING_REPORT, RUNBOOK]:
            self.assertTrue(path.exists(), f"Missing Phase 5 artifact: {path}")

    def test_app_dataset_contract(self) -> None:
        rows = self.read_csv(APP_DATASET)
        self.assertTrue(rows)
        required = {
            "field",
            "group_key",
            "classification",
            "driver_family",
            "sample_size",
            "cost_median",
            "cost_p10",
            "cost_p90",
            "confidence_tier",
            "estimator_readiness",
        }
        self.assertTrue(required.issubset(rows[0].keys()))
        self.assertTrue(all(r["field"] in {"DARAJAT", "SALAK"} for r in rows))

    def test_monitoring_kpi_contract(self) -> None:
        rows = self.read_csv(MONITORING)
        self.assertEqual(sorted(r["field"] for r in rows), ["DARAJAT", "SALAK"])
        self.assertTrue(all(float(r["kpi_ready_share_pct"]) >= 0 for r in rows))
        self.assertTrue(all(int(r["kpi_hard_gate_failures"]) == 0 for r in rows))

    def test_manifest_and_reports_reference_phase5(self) -> None:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(payload["phase"], "phase5")
        self.assertIn("data/processed/phase5_app_dataset.csv", payload["outputs"])

        app_text = APP_REPORT.read_text(encoding="utf-8")
        monitor_text = MONITORING_REPORT.read_text(encoding="utf-8")
        runbook_text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("Phase 5 App Integration Prerequisites", app_text)
        self.assertIn("Phase 5 Monitoring Skeleton", monitor_text)
        self.assertIn("Phase 5 Refresh Runbook", runbook_text)


if __name__ == "__main__":
    unittest.main()
