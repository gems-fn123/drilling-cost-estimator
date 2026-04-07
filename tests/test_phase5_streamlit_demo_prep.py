from __future__ import annotations

from pathlib import Path
import unittest

from src.app.phase5_streamlit_demo import APP_DATASET, KPI_DATASET, filter_field, load_data


class TestPhase5StreamlitDemoPrep(unittest.TestCase):
    def test_input_contract_files_exist(self) -> None:
        for path in [APP_DATASET, KPI_DATASET]:
            self.assertTrue(Path(path).exists(), f"Missing required app prep dataset: {path}")

    def test_filter_field_keeps_field_specificity(self) -> None:
        app_rows, kpi_rows = load_data()
        darajat_app, darajat_kpi = filter_field(app_rows, kpi_rows, "DARAJAT")
        salak_app, salak_kpi = filter_field(app_rows, kpi_rows, "SALAK")

        self.assertTrue(all(r["field"] == "DARAJAT" for r in darajat_app))
        self.assertTrue(all(r["field"] == "SALAK" for r in salak_app))
        self.assertEqual(darajat_kpi[0]["field"], "DARAJAT")
        self.assertEqual(salak_kpi[0]["field"], "SALAK")

    def test_required_demo_columns_present(self) -> None:
        app_rows, _ = load_data()
        required = {
            "field",
            "group_key",
            "classification",
            "driver_family",
            "sample_size",
            "cost_p10",
            "cost_median",
            "cost_p90",
            "confidence_tier",
            "estimator_readiness",
        }
        self.assertTrue(required.issubset(set(app_rows[0].keys())))


if __name__ == "__main__":
    unittest.main()
