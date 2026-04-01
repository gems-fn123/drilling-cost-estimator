from __future__ import annotations

import csv
import subprocess
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "processed" / "wbs_lv5_master.csv"
CLASSIFICATION = ROOT / "data" / "processed" / "wbs_lv5_classification.csv"
REVIEW = ROOT / "data" / "processed" / "wbs_lv5_review_queue.csv"
SUMMARY = ROOT / "data" / "processed" / "wbs_lv5_cost_summary_by_classification.csv"
HYBRID_RECOMMEND = ROOT / "data" / "processed" / "wbs_lv5_hybrid_tag_recommendation.csv"


class TestWbsLv5Classification(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(["python", "src/cleaning/build_wbs_lv5_classification.py"], cwd=ROOT, check=True)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open() as fh:
            return list(csv.DictReader(fh))

    def test_outputs_generated(self) -> None:
        for path in [MASTER, CLASSIFICATION, REVIEW, SUMMARY, HYBRID_RECOMMEND]:
            self.assertTrue(path.exists(), f"Missing expected output: {path}")

    def test_required_columns_exist(self) -> None:
        master_cols = set(self.read_csv(MASTER)[0].keys())
        classification_cols = set(self.read_csv(CLASSIFICATION)[0].keys())
        review_cols = set(self.read_csv(REVIEW)[0].keys())

        self.assertTrue({
            "source_file", "source_sheet", "source_row_id", "field", "campaign_raw", "campaign_canonical",
            "well_raw", "well_canonical", "wbs_code_raw", "wbs_lvl1", "wbs_lvl2", "wbs_lvl3", "wbs_lvl4",
            "wbs_lvl5", "wbs_label_raw", "cost_actual", "currency", "event_code_raw", "event_code_desc",
            "mapping_status_campaign", "mapping_status_well",
        }.issubset(master_cols))

        self.assertTrue({
            "classification_key", "field", "wbs_code_lv5", "wbs_lvl2", "wbs_lvl3", "wbs_lvl4", "wbs_lvl5",
            "classification", "classification_confidence", "classification_rule_id", "classification_rule_text",
            "recommended_allocation_basis", "include_for_modeling_initial", "review_status", "review_notes",
            "supporting_row_count", "supporting_cost_total",
        }.issubset(classification_cols))

        self.assertTrue({
            "classification_key", "field", "wbs_lvl5", "reason_for_review", "observed_patterns",
            "supporting_row_count", "supporting_cost_total", "suggested_default_classification",
        }.issubset(review_cols))

    def test_classification_enums(self) -> None:
        rows = self.read_csv(CLASSIFICATION)
        self.assertTrue(rows)
        self.assertTrue(all(r["classification"] in {"well_tied", "campaign_tied", "hybrid"} for r in rows))
        self.assertTrue(all(r["classification_confidence"] in {"high", "medium", "low"} for r in rows))
        self.assertTrue(all(r["review_status"] in {"approved_auto", "needs_review", "blocked_missing_context"} for r in rows))

    def test_unique_classification_key(self) -> None:
        rows = self.read_csv(CLASSIFICATION)
        keys = [r["classification_key"] for r in rows]
        self.assertEqual(len(keys), len(set(keys)))

    def test_summary_reconciles_master(self) -> None:
        master_total = sum(float(r["cost_actual"]) for r in self.read_csv(MASTER))
        summary_total = sum(float(r["cost_total"]) for r in self.read_csv(SUMMARY))
        self.assertAlmostEqual(master_total, summary_total, places=4)

    def test_review_queue_logic(self) -> None:
        classification = self.read_csv(CLASSIFICATION)
        review = self.read_csv(REVIEW)
        expected = sorted([r["classification_key"] for r in classification if r["review_status"] != "approved_auto"])
        actual = sorted([r["classification_key"] for r in review])
        self.assertEqual(expected, actual)

    def test_hybrid_recommendation_coverage(self) -> None:
        classification = self.read_csv(CLASSIFICATION)
        hybrid_expected = sorted([r["classification_key"] for r in classification if r["classification"] == "hybrid"])
        hybrid_rows = self.read_csv(HYBRID_RECOMMEND)
        hybrid_actual = sorted([r["classification_key"] for r in hybrid_rows])
        self.assertEqual(hybrid_expected, hybrid_actual)
        self.assertTrue(all(r["suggested_tag"] in {"well", "pad", "campaign"} for r in hybrid_rows))


if __name__ == "__main__":
    unittest.main()
