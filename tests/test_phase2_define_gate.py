from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WELL_MASTER = ROOT / "data" / "processed" / "well_master.csv"
CAMPAIGN_MASTER = ROOT / "data" / "processed" / "canonical_campaign_mapping.csv"
LV5_MASTER = ROOT / "data" / "processed" / "wbs_lv5_master.csv"
LV5_CLASSIFICATION = ROOT / "data" / "processed" / "wbs_lv5_classification.csv"
FEATURE_FAMILIES = ROOT / "docs" / "feature_families.md"
QUALITY_REPORT = ROOT / "reports" / "phase2_define_quality_thresholds.md"


class TestPhase2DefineGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "-m", "src.io.build_canonical_mappings"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "-m", "src.cleaning.build_wbs_lv5_classification"], cwd=ROOT, check=True)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def test_gate_artifacts_exist(self) -> None:
        for path in [FEATURE_FAMILIES, QUALITY_REPORT, WELL_MASTER, CAMPAIGN_MASTER, LV5_MASTER, LV5_CLASSIFICATION]:
            self.assertTrue(path.exists(), f"Missing expected Phase 2 gate artifact: {path}")

    def test_well_master_contract_columns(self) -> None:
        rows = self.read_csv(WELL_MASTER)
        self.assertTrue(rows)
        required = {
            "well_id",
            "well_name",
            "well_canonical",
            "well_aliases",
            "field",
            "campaign_code",
            "campaign_id",
            "status",
            "region",
            "operator",
            "include_for_estimator",
            "include_for_well_training",
            "training_note",
        }
        self.assertTrue(required.issubset(rows[0].keys()))

        for row in rows:
            aliases = json.loads(row["well_aliases"])
            self.assertIsInstance(aliases, list)
            self.assertIn(row["well_name"], aliases)
            self.assertEqual(row["well_id"], row["well_canonical"])
            self.assertEqual(row["status"], "in_scope_estimator")

    def test_campaign_master_contract_columns(self) -> None:
        rows = self.read_csv(CAMPAIGN_MASTER)
        self.assertTrue(rows)
        required = {
            "campaign_code",
            "campaign_id",
            "campaign_name",
            "campaign_name_raw",
            "field",
            "campaign_wbs_code",
            "estimator_scope",
            "include_for_estimator",
            "start_date",
            "end_date",
            "actual_cost_total",
            "source_file",
            "source_sheet",
        }
        self.assertTrue(required.issubset(rows[0].keys()))

        campaign_codes = [row["campaign_code"] for row in rows]
        self.assertEqual(len(campaign_codes), len(set(campaign_codes)))

        in_scope_rows = [row for row in rows if row["estimator_scope"] == "in_scope"]
        self.assertTrue(in_scope_rows)
        self.assertTrue(all(row["field"] in {"DARAJAT", "SALAK", "WAYANG_WINDU"} for row in in_scope_rows))
        self.assertTrue(all(row["campaign_wbs_code"] == row["campaign_code"] for row in in_scope_rows))

    def test_phase2_quality_metrics_hold(self) -> None:
        master_rows = self.read_csv(LV5_MASTER)
        classification_rows = self.read_csv(LV5_CLASSIFICATION)

        hierarchy_blank = sum(
            1
            for row in master_rows
            if any(not row[col].strip() for col in ["wbs_lvl1", "wbs_lvl2", "wbs_lvl3", "wbs_lvl4", "wbs_lvl5"])
        )
        campaign_blank = sum(1 for row in master_rows if not row["campaign_code"].strip() or not row["campaign_canonical"].strip())
        classification_keys = [row["classification_key"] for row in classification_rows]
        well_master_keys = [
            (row["well_id"], row["campaign_code"])
            for row in self.read_csv(WELL_MASTER)
            if row["well_id"].strip() and row["campaign_code"].strip()
        ]

        self.assertEqual(hierarchy_blank, 0)
        self.assertEqual(campaign_blank, 0)
        self.assertEqual(len(classification_keys), len(set(classification_keys)))
        self.assertEqual(len(well_master_keys), len(set(well_master_keys)))

    def test_quality_report_and_feature_doc_capture_limitations(self) -> None:
        quality_text = QUALITY_REPORT.read_text(encoding="utf-8")
        feature_text = FEATURE_FAMILIES.read_text(encoding="utf-8")

        self.assertIn("Gate recommendation: **READY FOR PHASE 3 DESIGN**", quality_text)
        self.assertIn("KNOWN LIMITATION", quality_text)
        self.assertIn("Current Grain Limitation", quality_text)
        self.assertIn("well attribution", quality_text.lower())
        self.assertIn("event-code", quality_text.lower())

        for token in ["depth", "section", "operation_type", "npt_unscheduled_event", "campaign_context"]:
            self.assertIn(token, feature_text)


if __name__ == "__main__":
    unittest.main()
