from __future__ import annotations

import json
import subprocess
from pathlib import Path
import unittest

from src.modeling.phase5_estimation_core import (
    APP_AUDIT,
    APP_RUN_MANIFEST,
    APP_SUMMARY,
    CONFIDENCE_BANDS,
    METHOD_REGISTRY,
    estimate_campaign,
)

ROOT = Path(__file__).resolve().parents[1]
VAL_DARAJAT = ROOT / "reports" / "validation_darajat.md"
VAL_SALAK = ROOT / "reports" / "validation_salak.md"


class TestPhase5EstimatorEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(["python", "src/modeling/build_phase5_validation_artifacts.py"], cwd=ROOT, check=True)
        campaign_input = {
            "year": 2026,
            "field": "SLK",
            "no_pads": 2,
            "no_wells": 2,
            "no_pad_expansion": 1,
            "use_external_forecast": True,
            "use_synthetic_data": True,
        }
        wells = [
            {"well_label": "Well-1", "pad_label": "Pad-1", "depth_ft": 7000, "leg_type": "Standard-J", "drill_rate_mode": "Standard"},
            {"well_label": "Well-2", "pad_label": "Pad-2", "depth_ft": 8000, "leg_type": "Multilateral", "drill_rate_mode": "Careful"},
        ]
        estimate_campaign(campaign_input, wells)

    def test_validation_artifacts_exist(self) -> None:
        for path in [CONFIDENCE_BANDS, METHOD_REGISTRY, VAL_DARAJAT, VAL_SALAK]:
            self.assertTrue(Path(path).exists(), f"Missing validation artifact: {path}")

    def test_campaign_estimate_and_reconciliation(self) -> None:
        campaign_input = {
            "year": 2026,
            "field": "SLK",
            "no_pads": 2,
            "no_wells": 2,
            "no_pad_expansion": 1,
            "use_external_forecast": True,
            "use_synthetic_data": True,
        }
        wells = [
            {"well_label": "Well-1", "pad_label": "Pad-1", "depth_ft": 7000, "leg_type": "Standard-J", "drill_rate_mode": "Standard"},
            {"well_label": "Well-2", "pad_label": "Pad-2", "depth_ft": 8000, "leg_type": "Multilateral", "drill_rate_mode": "Careful"},
        ]
        result = estimate_campaign(campaign_input, wells)
        summary = result["campaign_summary"]
        self.assertEqual(summary["reconciliation_status"], "PASS")
        self.assertGreater(summary["total_campaign_cost_usd"], 0)
        detail_sum = sum(r["estimate_usd"] for r in result["detail_wbs"])
        self.assertAlmostEqual(detail_sum, summary["total_campaign_cost_usd"], places=2)
        self.assertIn("wbs_family_fractions", result)
        self.assertIn("driver_attribution", result)
        self.assertIn("component_share_breakdown", result)
        self.assertTrue(result["wbs_family_fractions"]["classification"])
        self.assertTrue(result["component_share_breakdown"])

    def test_audit_outputs_exist_and_have_reconciliation(self) -> None:
        for path in [APP_RUN_MANIFEST, APP_AUDIT, APP_SUMMARY]:
            self.assertTrue(Path(path).exists(), f"Missing audit output: {path}")

        manifest = json.loads(Path(APP_RUN_MANIFEST).read_text(encoding="utf-8"))
        summary = json.loads(Path(APP_SUMMARY).read_text(encoding="utf-8"))
        self.assertEqual(manifest["reconciliation"]["status"], "PASS")
        self.assertEqual(summary["reconciliation_status"], "PASS")
        self.assertIn("wbs_family_fractions", summary)
        self.assertIn("driver_attribution", summary)
        self.assertIn("component_share_breakdown", summary)


if __name__ == "__main__":
    unittest.main()
