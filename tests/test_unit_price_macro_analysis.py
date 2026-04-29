from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MACRO_REFERENCE = ROOT / "data" / "reference" / "macro_series_2019_2026.csv"
MACRO_FACTORS = ROOT / "data" / "processed" / "unit_price_macro_factors.csv"
MACRO_WEIGHTS = ROOT / "data" / "processed" / "unit_price_macro_weights.csv"
MACRO_CLUSTER_WEIGHTS = ROOT / "data" / "processed" / "unit_price_macro_cluster_weights.csv"
MACRO_REPORT = ROOT / "reports" / "unit_price_macro_correlation.md"


class TestUnitPriceMacroAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "src/modeling/unit_price_history_pipeline.py"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "src/modeling/unit_price_macro_analysis.py"], cwd=ROOT, check=True)

    def test_macro_reference_contains_required_columns(self) -> None:
        with MACRO_REFERENCE.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {
            "year",
            "brent_usd_bbl",
            "indonesia_cpi_index",
            "indonesia_inflation_pct",
            "steel_commodity_proxy_usd_ton",
            "steel_proxy_name",
            "source_note",
        }
        self.assertEqual(len(rows), 8)
        self.assertTrue(required.issubset(rows[0].keys()))

    def test_macro_factors_include_yearly_unit_price_and_macro_inputs(self) -> None:
        with MACRO_FACTORS.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {
            "scope_type",
            "field",
            "pricing_basis",
            "year",
            "annual_unit_price_usd",
            "brent_usd_bbl",
            "indonesia_cpi_index",
            "steel_commodity_proxy_usd_ton",
            "has_unit_price_history",
        }
        self.assertTrue(required.issubset(rows[0].keys()))
        self.assertIn("pooled_pricing_basis", {row["scope_type"] for row in rows})
        self.assertIn("field_pricing_basis", {row["scope_type"] for row in rows})

    def test_macro_weights_produce_operational_pooled_rows(self) -> None:
        with MACRO_WEIGHTS.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {
            "scope_type",
            "field",
            "pricing_basis",
            "factor_name",
            "pearson_r_nominal",
            "forecast_weight",
            "direction",
            "support_status",
            "weight_basis",
        }
        self.assertTrue(required.issubset(rows[0].keys()))

        operational = [
            row
            for row in rows
            if row["scope_type"] == "pooled_pricing_basis"
            and row["field"] == "ALL_FIELDS"
            and row["pricing_basis"] == "active_day_rate"
            and row["factor_name"] in {"brent_usd_bbl", "indonesia_cpi_index", "steel_commodity_proxy_usd_ton"}
        ]
        self.assertEqual(len(operational), 3)
        self.assertTrue(all(row["support_status"] == "operational" for row in operational))
        self.assertTrue(all(row["weight_basis"] == "nominal_abs_pearson" for row in operational))
        self.assertAlmostEqual(sum(float(row["forecast_weight"]) for row in operational), 1.0, places=5)

    def test_macro_weights_keep_inflation_rate_as_diagnostic_factor(self) -> None:
        with MACRO_WEIGHTS.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        inflation_rows = [row for row in rows if row["factor_name"] == "indonesia_inflation_pct"]
        self.assertTrue(inflation_rows)
        self.assertTrue(all(row["weight_eligible"] == "no" for row in inflation_rows))

    def test_macro_cluster_layer_is_written(self) -> None:
        with MACRO_CLUSTER_WEIGHTS.open(encoding="utf-8", newline="") as handle:
            weight_rows = list(csv.DictReader(handle))

        required_weight = {
            "scope_type",
            "field",
            "pricing_basis",
            "wbs_cluster",
            "factor_name",
            "field_coverage_count",
            "field_count_floor",
            "field_count_peak",
            "support_status",
        }
        self.assertTrue(required_weight.issubset(weight_rows[0].keys()))

        cluster_keys = {row["wbs_cluster"] for row in weight_rows if row["scope_type"] == "pooled_wbs_cluster"}
        self.assertIn("material ll | casing", cluster_keys)
        self.assertIn("services | contract rig", cluster_keys)

        operational_cluster_rows = [
            row
            for row in weight_rows
            if row["scope_type"] == "pooled_wbs_cluster"
            and row["support_status"] == "operational"
            and row["weight_eligible"] == "yes"
        ]
        self.assertTrue(operational_cluster_rows)
        self.assertTrue(all(row["balance_method"] == "equal_field_mean" for row in operational_cluster_rows))
        self.assertTrue(all(int(row["field_coverage_count"]) >= 2 for row in operational_cluster_rows))
        self.assertTrue(all(int(row["observation_year_count"]) >= 4 for row in operational_cluster_rows))

    def test_macro_report_is_written(self) -> None:
        self.assertTrue(MACRO_REPORT.exists())
        text = MACRO_REPORT.read_text(encoding="utf-8")
        self.assertIn("Recommended Operational Weights", text)
        self.assertIn("Source Package", text)
        self.assertIn("Clustered WBS Depth Layer", text)


if __name__ == "__main__":
    unittest.main()
