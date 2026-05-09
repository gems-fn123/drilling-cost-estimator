from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "processed" / "wbs_lv5_master.csv"
CLASSIFICATION = ROOT / "data" / "processed" / "wbs_lv5_classification.csv"
DRIVER_REFERENCE = ROOT / "data" / "processed" / "wbs_lv5_driver_reference.csv"
REVIEW = ROOT / "data" / "processed" / "wbs_lv5_review_queue.csv"
SUMMARY = ROOT / "data" / "processed" / "wbs_lv5_cost_summary_by_classification.csv"
FIELD_SUMMARY = ROOT / "data" / "processed" / "wbs_lv5_cost_summary_by_field_and_classification.csv"
HYBRID_RECOMMEND = ROOT / "data" / "processed" / "wbs_lv5_hybrid_tag_recommendation.csv"
CURATED_POLICY = ROOT / "data" / "processed" / "wbs_lv5_curated_policy.csv"

MATERIAL_REVIEW_THRESHOLD = 500000.0


class TestWbsLv5Classification(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "-m", "src.io.build_canonical_mappings"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "-m", "src.cleaning.build_wbs_lv5_classification"], cwd=ROOT, check=True)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def assert_family_class(self, driver_rows: list[dict[str, str]], family: str, estimation_class: str) -> None:
        rows = [r for r in driver_rows if r["wbs_family_tag"] == family]
        self.assertTrue(rows, f"Expected family tag {family} to exist in driver reference")
        self.assertTrue(all(r["estimation_class"] == estimation_class for r in rows), f"Expected family {family} -> {estimation_class}")

    def assert_label_pattern_class(self, driver_rows: list[dict[str, str]], pattern: str, estimation_class: str) -> None:
        rows = [r for r in driver_rows if pattern.lower() in r["example_wbs_label"].lower()]
        self.assertTrue(rows, f"Expected label pattern {pattern} to exist in driver reference")
        self.assertTrue(all(r["estimation_class"] == estimation_class for r in rows), f"Expected label pattern {pattern} -> {estimation_class}")

    def test_outputs_generated(self) -> None:
        for path in [MASTER, CLASSIFICATION, DRIVER_REFERENCE, REVIEW, SUMMARY, FIELD_SUMMARY, HYBRID_RECOMMEND, CURATED_POLICY]:
            self.assertTrue(path.exists(), f"Missing expected output: {path}")

    def test_required_columns_exist(self) -> None:
        master_cols = set(self.read_csv(MASTER)[0].keys())
        classification_cols = set(self.read_csv(CLASSIFICATION)[0].keys())
        driver_cols = set(self.read_csv(DRIVER_REFERENCE)[0].keys())
        review_cols = set(self.read_csv(REVIEW)[0].keys())

        self.assertTrue({
            "source_file", "source_sheet", "source_row_id", "field", "campaign_raw", "campaign_code",
            "campaign_canonical", "campaign_scope", "campaign_mapping_basis", "wbs_code_raw", "wbs_lvl1",
            "wbs_lvl2", "wbs_lvl3", "wbs_lvl4", "wbs_lvl5", "wbs_label_raw", "cost_actual",
            "mapping_status_campaign", "mapping_status_well", "tag_well_or_pad", "tag_lvl5",
        }.issubset(master_cols))

        self.assertTrue({
            "classification_key", "field", "wbs_code_lv5", "wbs_lvl2", "wbs_lvl3", "wbs_lvl4", "wbs_lvl5",
            "wbs_family_tag", "example_wbs_label", "classification", "driver_family", "classification_confidence",
            "classification_rule_id", "classification_rule_text", "well_estimation_use", "campaign_estimation_use",
            "review_status", "review_notes", "material_review_flag", "supporting_row_count", "supporting_cost_total",
        }.issubset(classification_cols))

        self.assertTrue({
            "classification_key", "field", "wbs_code_lv5", "wbs_lvl5", "wbs_family_tag", "example_wbs_label",
            "supporting_cost_total", "estimation_class", "driver_family", "well_estimation_use",
            "campaign_estimation_use", "approval_status", "approval_basis", "approval_notes",
        }.issubset(driver_cols))

        self.assertTrue({
            "classification_key", "field", "wbs_lvl5", "wbs_family_tag", "reason_for_review",
            "approval_status", "observed_patterns", "supporting_row_count", "supporting_cost_total",
            "proposed_classification", "driver_family",
        }.issubset(review_cols))

    def test_classification_and_driver_enums(self) -> None:
        classification_rows = self.read_csv(CLASSIFICATION)
        driver_rows = self.read_csv(DRIVER_REFERENCE)
        self.assertTrue(classification_rows)
        self.assertTrue(driver_rows)
        self.assertTrue(all(r["classification"] in {"well_tied", "campaign_tied", "hybrid", "unresolved"} for r in classification_rows))
        self.assertTrue(all(r["classification_confidence"] in {"high", "medium", "low"} for r in classification_rows))
        self.assertTrue(all(r["review_status"] in {"approved_auto", "approved_policy", "approved_keyword", "needs_review"} for r in classification_rows))
        self.assertTrue(all(r["estimation_class"] in {"well_tied", "campaign_tied", "hybrid"} for r in driver_rows))
        self.assertTrue(all(r["approval_status"] in {"approved_auto", "approved_policy", "approved_keyword", "needs_review"} for r in driver_rows))

    def test_unique_classification_key(self) -> None:
        classification_rows = self.read_csv(CLASSIFICATION)
        driver_rows = self.read_csv(DRIVER_REFERENCE)
        classification_keys = [r["classification_key"] for r in classification_rows]
        driver_keys = [r["classification_key"] for r in driver_rows]
        self.assertEqual(len(classification_keys), len(set(classification_keys)))
        self.assertEqual(sorted(classification_keys), sorted(driver_keys))

    def test_in_scope_campaign_mapping_hard_gate(self) -> None:
        rows = self.read_csv(MASTER)
        in_scope_rows = [r for r in rows if r["campaign_raw"] in {"DRJ 2022", "DRJ 2023", "SLK 2025"}]
        self.assertTrue(in_scope_rows)
        self.assertTrue(all(r["mapping_status_campaign"] == "mapped" for r in in_scope_rows))
        self.assertTrue(all(r["campaign_scope"] == "in_scope" for r in in_scope_rows))

    def test_summary_reconciles_master(self) -> None:
        master_total = sum(float(r["cost_actual"]) for r in self.read_csv(MASTER))
        summary_total = sum(float(r["cost_total"]) for r in self.read_csv(SUMMARY))
        self.assertAlmostEqual(master_total, summary_total, places=4)

    def test_review_queue_logic(self) -> None:
        classification = self.read_csv(CLASSIFICATION)
        review = self.read_csv(REVIEW)
        expected = sorted(
            [
                r["classification_key"]
                for r in classification
                if r["classification"] == "unresolved" or float(r["supporting_cost_total"]) >= MATERIAL_REVIEW_THRESHOLD
            ]
        )
        actual = sorted([r["classification_key"] for r in review])
        self.assertEqual(expected, actual)

    def test_hybrid_reference_coverage(self) -> None:
        classification = self.read_csv(CLASSIFICATION)
        hybrid_expected = sorted([r["classification_key"] for r in classification if r["classification"] == "hybrid"])
        hybrid_rows = self.read_csv(HYBRID_RECOMMEND)
        hybrid_actual = sorted([r["classification_key"] for r in hybrid_rows])
        self.assertEqual(hybrid_expected, hybrid_actual)
        self.assertTrue(all(r["suggested_tag"] == "campaign" for r in hybrid_rows))
        self.assertTrue(all("default_for_shared_or_unknown_scope" not in r["suggestion_basis"] for r in hybrid_rows))

    def test_semantic_exemplars(self) -> None:
        driver_rows = self.read_csv(DRIVER_REFERENCE)
        self.assert_family_class(driver_rows, "Contract Rig", "well_tied")
        self.assert_family_class(driver_rows, "Mud Logging Service", "well_tied")
        self.assert_family_class(driver_rows, "Casing Installation", "well_tied")
        self.assert_family_class(driver_rows, "Security", "campaign_tied")
        self.assert_family_class(driver_rows, "Permitting", "campaign_tied")
        self.assert_family_class(driver_rows, "Drilling Facilities Support", "campaign_tied")
        self.assert_family_class(driver_rows, "Drilling Operation Water Support", "campaign_tied")
        self.assert_family_class(driver_rows, "Construction", "hybrid")
        self.assert_family_class(driver_rows, "Rig Move", "hybrid")
        self.assert_family_class(driver_rows, "Rig Skid", "hybrid")
        self.assert_label_pattern_class(driver_rows, "Tie In-Inst,HookUp&Pre-Comm", "hybrid")
        self.assert_label_pattern_class(driver_rows, "Tie In - Inst,HookUp&Pre-Comm", "hybrid")


if __name__ == "__main__":
    unittest.main()
