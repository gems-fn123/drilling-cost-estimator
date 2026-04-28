from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.modeling.streamlined_etl_pipeline import PIPELINE_MANIFEST_PATH, run_pipeline_endpoint, run_streamlined_etl
from src.modeling.wbs_tree_diagram import WBS_TREE_COMBINED_JSON, WBS_TREE_HTML, build_wbs_tree_from_excel_sheet

ROOT = Path(__file__).resolve().parents[1]


class TestStreamlinedEtlPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        run_streamlined_etl()

    def test_manifest_exists_and_tracks_artifacts(self) -> None:
        self.assertTrue(PIPELINE_MANIFEST_PATH.exists())
        payload = json.loads(PIPELINE_MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(payload["pipeline"], "streamlined_etl_v1")
        self.assertIn("validation_summary", payload)
        self.assertIn("wbs_tree_summary", payload)

        by_path = {row["path"]: row for row in payload["artifacts"]}
        self.assertIn("data/processed/historical_cost_mart.csv", by_path)
        self.assertIn("data/processed/baseline_estimates_darajat.csv", by_path)
        self.assertIn("data/processed/baseline_estimates_salak.csv", by_path)
        self.assertIn("data/processed/unit_price_well_profile.csv", by_path)
        self.assertIn("data/processed/unit_price_benchmark.csv", by_path)
        self.assertIn("data/processed/service_time_band_reference.csv", by_path)
        self.assertIn("data/processed/unit_price_macro_weights.csv", by_path)
        self.assertIn("data/processed/npt_penalty_reference.csv", by_path)
        self.assertIn("data/processed/wbs_tree_interactive.json", by_path)
        self.assertIn("reports/wbs_tree_interactive.html", by_path)
        self.assertTrue(by_path["data/processed/historical_cost_mart.csv"]["exists"])

    def test_wbs_tree_artifacts_are_field_separated(self) -> None:
        self.assertTrue(WBS_TREE_COMBINED_JSON.exists())
        self.assertTrue(WBS_TREE_HTML.exists())

        payload = json.loads(WBS_TREE_COMBINED_JSON.read_text(encoding="utf-8"))
        self.assertIn("source_contract", payload)
        self.assertEqual(payload["source_contract"]["source_sheet_required"], "Data.Summary")
        self.assertEqual(sorted(payload["fields"].keys()), ["DARAJAT", "SALAK"])

        darajat_tree = payload["fields"]["DARAJAT"]
        salak_tree = payload["fields"]["SALAK"]

        self.assertGreater(darajat_tree["sample_row_count"], 0)
        self.assertGreater(salak_tree["sample_row_count"], 0)
        self.assertEqual(darajat_tree["field"], "DARAJAT")
        self.assertEqual(salak_tree["field"], "SALAK")
        self.assertTrue(darajat_tree["children"])
        self.assertTrue(salak_tree["children"])

    def test_wbs_tree_from_excel_sheet_contract(self) -> None:
        payload = build_wbs_tree_from_excel_sheet(ROOT / "data" / "raw" / "20260327_WBS_Data.xlsx", sheet_name="Data.Summary")
        self.assertEqual(payload["source_contract"]["source_sheet_required"], "Data.Summary")
        self.assertEqual(sorted(payload["fields"].keys()), ["DARAJAT", "SALAK"])
        self.assertGreater(payload["fields"]["DARAJAT"]["sample_row_count"], 0)
        self.assertGreater(payload["fields"]["SALAK"]["sample_row_count"], 0)

    def test_endpoint_payload_keeps_current_shape(self) -> None:
        campaign_input = {
            "year": 2026,
            "field": "SLK",
            "no_pads": 2,
            "no_wells": 2,
            "no_pad_expansion": 1,
            "use_external_forecast": True,
            "use_synthetic_data": False,
        }
        well_rows = [
            {
                "well_label": "Well-1",
                "pad_label": "Pad-1",
                "depth_ft": 7000,
                "leg_type": "Standard-J",
                "drill_rate_mode": "Standard",
            },
            {
                "well_label": "Well-2",
                "pad_label": "Pad-2",
                "depth_ft": 8000,
                "leg_type": "Multilateral",
                "drill_rate_mode": "Careful",
            },
        ]

        payload = run_pipeline_endpoint(campaign_input, well_rows, refresh_pipeline=False)

        required = {
            "campaign_input",
            "well_outputs",
            "campaign_summary",
            "detail_wbs",
            "audit_rows",
            "run_manifest",
            "warnings",
            "pipeline_manifest_path",
        }
        self.assertTrue(required.issubset(payload.keys()))
        self.assertEqual(payload["campaign_summary"]["reconciliation_status"], "PASS")
        self.assertEqual(payload["campaign_summary"]["field"], "SALAK")


if __name__ == "__main__":
    unittest.main()
