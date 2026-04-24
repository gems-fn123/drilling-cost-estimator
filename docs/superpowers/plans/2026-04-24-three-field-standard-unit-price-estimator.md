# Three-Field Standard-Well Unit-Price Estimator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a seven-campaign, three-field unit-price analysis and forecasting pipeline that uses standard-only well assumptions, quantifies NPT contributors, and produces auditable forecast weights from Pearson correlations against oil, inflation, and steel yearly series.

**Architecture:** Add a new dashboard-workbook-driven unit-price pipeline alongside the legacy `Data.Summary` pipeline. Reuse existing workbook parsing and processed/report conventions, but keep the new history layer separate from the legacy code-level WBS mart so WW and legacy campaigns can enter with clear source-row lineage. Keep the current endpoint contract working while moving its forecast logic to read the new macro-weight outputs and treating all estimated wells as `Standard-J`.

**Tech Stack:** Python stdlib, CSV/JSON processed artifacts, XML/XLSX workbook parsing, `unittest`, existing CLI entrypoints in `src/modeling/`.

---

## File Structure

**Create:**

- `src/modeling/unit_price_history_pipeline.py`
- `src/modeling/unit_price_macro_analysis.py`
- `src/modeling/unit_price_well_analysis.py`
- `src/modeling/unit_price_npt_analysis.py`
- `tests/test_unit_price_history_pipeline.py`
- `tests/test_unit_price_macro_analysis.py`
- `tests/test_unit_price_well_analysis.py`
- `tests/test_unit_price_npt_analysis.py`
- `data/reference/macro_series_2019_2026.csv`
- `reports/unit_price_scope_coverage.md`
- `reports/unit_price_macro_correlation.md`
- `reports/unit_price_well_analysis.md`
- `reports/unit_price_npt_contribution.md`

**Modify:**

- `src/io/build_canonical_mappings.py`
- `src/cleaning/wbs_lv5_driver_alignment.py`
- `src/modeling/streamlined_etl_pipeline.py`
- `src/modeling/phase5_estimation_core.py`
- `src/app/components/input_panel.py`
- `docs/refresh_runbook.md`
- `docs/assumptions_register.md`
- `tests/test_streamlined_etl_pipeline.py`
- `tests/test_phase5_estimator_engine.py`

## Task 1: Expand Canonical Scope to All Seven Campaigns

**Files:**

- Create: `tests/test_unit_price_history_pipeline.py`
- Modify: `src/io/build_canonical_mappings.py`
- Modify: `docs/assumptions_register.md`
- Report: `reports/unit_price_scope_coverage.md`

- [ ] **Step 1: Write the failing scope and mapping tests**

```python
from pathlib import Path
import csv
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_MAP = ROOT / "data" / "processed" / "canonical_campaign_mapping.csv"


class TestUnitPriceHistoryScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "src/io/build_canonical_mappings.py"], cwd=ROOT, check=True)

    def test_campaign_mapping_contains_all_requested_campaigns(self) -> None:
        rows = list(csv.DictReader(CAMPAIGN_MAP.open(encoding="utf-8", newline="")))
        ids = {row["campaign_id"] for row in rows}
        self.assertTrue(
            {
                "DARAJAT_2019",
                "DARAJAT_2022",
                "DARAJAT_2023_2024",
                "SALAK_2021",
                "SALAK_2025_2026",
                "WAYANG_WINDU_2018",
                "WAYANG_WINDU_2021",
            }.issubset(ids)
        )
```

- [ ] **Step 2: Run the scope test to verify it fails**

Run: `python -m unittest tests.test_unit_price_history_pipeline.TestUnitPriceHistoryScope.test_campaign_mapping_contains_all_requested_campaigns -v`

Expected: FAIL because WW campaigns are missing and the current mapping still treats only DARAJAT/SALAK in-scope.

- [ ] **Step 3: Extend canonical mappings and scope metadata**

```python
OFFICIAL_CAMPAIGNS = {
    "E530-30101-D225301": {"campaign_id": "DARAJAT_2022", "field": "DARAJAT", "scope": "in_scope"},
    "E530-30101-D235301": {"campaign_id": "DARAJAT_2023_2024", "field": "DARAJAT", "scope": "in_scope"},
    "E540-30101-D245401": {"campaign_id": "SALAK_2025_2026", "field": "SALAK", "scope": "in_scope"},
    "E530-30101-D19001": {"campaign_id": "DARAJAT_2019", "field": "DARAJAT", "scope": "in_scope"},
    "E540-30101-D20001": {"campaign_id": "SALAK_2021", "field": "SALAK", "scope": "in_scope"},
    "WW-2018": {"campaign_id": "WAYANG_WINDU_2018", "field": "WAYANG_WINDU", "scope": "in_scope"},
    "WW-2021": {"campaign_id": "WAYANG_WINDU_2021", "field": "WAYANG_WINDU", "scope": "in_scope"},
}
```

```python
CAMPAIGN_LABEL_TO_CODE.update(
    {
        "DRJ - 2019": "E530-30101-D19001",
        "DRJ - 2022": "E530-30101-D225301",
        "DRJ - 2024": "E530-30101-D235301",
        "SLK - 2021": "E540-30101-D20001",
        "SLK - 2025": "E540-30101-D245401",
        "WW - 2018": "WW-2018",
        "WW - 2021": "WW-2021",
    }
)
```

```markdown
| 2026-04-24 | Unit-price program scope | All seven dashboard campaigns, including `WW - 2018` and `WW - 2021`, are treated as active input scope for the new unit-price pipeline. | The unit-price program is workbook-driven and does not require code-level `Data.Summary` lineage for every campaign. | Active for `data-ingestion.2.0`. |
```

- [ ] **Step 4: Run the tests and generate the scope coverage report**

Run: `python src/io/build_canonical_mappings.py`

Run: `python -m unittest tests.test_unit_price_history_pipeline.TestUnitPriceHistoryScope -v`

Expected: PASS, and `reports/unit_price_scope_coverage.md` lists all seven campaigns with field membership and workbook lineage.

- [ ] **Step 5: Commit**

```bash
git add docs/assumptions_register.md src/io/build_canonical_mappings.py tests/test_unit_price_history_pipeline.py reports/unit_price_scope_coverage.md
git commit -m "feat: expand canonical scope to all dashboard campaigns"
```

## Task 2: Build a Seven-Campaign Unit-Price History Mart

**Files:**

- Create: `src/modeling/unit_price_history_pipeline.py`
- Create: `tests/test_unit_price_history_pipeline.py`
- Modify: `src/modeling/streamlined_etl_pipeline.py`

- [ ] **Step 1: Write the failing mart and lineage tests**

```python
HISTORY_MART = ROOT / "data" / "processed" / "unit_price_history_mart.csv"

    def test_unit_price_history_mart_has_three_fields(self) -> None:
        subprocess.run([sys.executable, "src/modeling/unit_price_history_pipeline.py"], cwd=ROOT, check=True)
        rows = list(csv.DictReader(HISTORY_MART.open(encoding="utf-8", newline="")))
        fields = {row["field"] for row in rows}
        self.assertEqual(fields, {"DARAJAT", "SALAK", "WAYANG_WINDU"})

    def test_history_mart_preserves_workbook_lineage(self) -> None:
        rows = list(csv.DictReader(HISTORY_MART.open(encoding="utf-8", newline="")))
        required = {"source_workbook", "source_sheet", "source_row_key", "pricing_basis", "unit_price_basis"}
        self.assertTrue(required.issubset(rows[0].keys()))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_unit_price_history_pipeline -v`

Expected: FAIL because `unit_price_history_mart.csv` and the new pipeline do not exist yet.

- [ ] **Step 3: Implement the history mart from the dashboard workbook**

```python
def build_unit_price_history_mart() -> list[dict]:
    structured_cost = load_structured_cost_rows()
    general_context = load_general_campaign_rows()
    campaign_lookup = load_campaign_lookup()

    mart_rows: list[dict] = []
    for row in structured_cost:
        field = normalize_field(row["Asset"])
        campaign_code = campaign_lookup[row["Campaign"]]["campaign_code"]
        mart_rows.append(
            {
                "field": field,
                "campaign_canonical": campaign_lookup[row["Campaign"]]["campaign_id"],
                "campaign_year": campaign_lookup[row["Campaign"]]["campaign_year"],
                "well_canonical": normalize_dashboard_well(row["Well"]),
                "pricing_basis": infer_pricing_basis(row),
                "unit_price_basis": infer_quantity_basis(row),
                "actual_cost_usd": f"{float(row['Actual Cost USD']):.6f}",
                "source_workbook": "20260422_Data for Dashboard.xlsx",
                "source_sheet": "Structured.Cost",
                "source_row_key": row["row_number"],
            }
        )
    return mart_rows
```

```python
def infer_pricing_basis(row: dict) -> str:
    level3 = row["Level 3"].strip().lower()
    level4 = row["Level 4"].strip().lower()
    if level3 == "well cost" and level4 == "services":
        return "active_day_rate"
    if level3 == "well cost" and "material" in level4:
        return "depth_rate"
    if level3 in {"tie-in", "rig mobilization", "rig move"}:
        return "campaign_scope_benchmark"
    return "per_well_job"
```

- [ ] **Step 4: Run the new mart pipeline and tests**

Run: `python src/modeling/unit_price_history_pipeline.py`

Run: `python -m unittest tests.test_unit_price_history_pipeline -v`

Expected: PASS, with `data/processed/unit_price_history_mart.csv` created and containing all three fields.

- [ ] **Step 5: Commit**

```bash
git add src/modeling/unit_price_history_pipeline.py src/modeling/streamlined_etl_pipeline.py tests/test_unit_price_history_pipeline.py
git commit -m "feat: add seven-campaign unit price history mart"
```

## Task 3: Add Yearly Macro Series and Pearson Correlation Weighting

**Files:**

- Create: `data/reference/macro_series_2019_2026.csv`
- Create: `src/modeling/unit_price_macro_analysis.py`
- Create: `tests/test_unit_price_macro_analysis.py`
- Report: `reports/unit_price_macro_correlation.md`

- [ ] **Step 1: Write the failing macro-analysis tests**

```python
MACRO_FACTORS = ROOT / "data" / "processed" / "unit_price_macro_factors.csv"
MACRO_WEIGHTS = ROOT / "data" / "processed" / "unit_price_macro_weights.csv"


class TestUnitPriceMacroAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "src/modeling/unit_price_macro_analysis.py"], cwd=ROOT, check=True)

    def test_macro_series_contains_required_columns(self) -> None:
        rows = list(csv.DictReader(MACRO_FACTORS.open(encoding="utf-8", newline="")))
        self.assertTrue({"year", "brent_usd_bbl", "cpi_index", "steel_hrc_usd_ton"}.issubset(rows[0].keys()))

    def test_macro_weights_are_built_from_pearson_results(self) -> None:
        rows = list(csv.DictReader(MACRO_WEIGHTS.open(encoding="utf-8", newline="")))
        self.assertTrue({"field", "pricing_basis", "factor_name", "pearson_r", "forecast_weight", "direction"}.issubset(rows[0].keys()))
```

- [ ] **Step 2: Run the macro-analysis tests to verify they fail**

Run: `python -m unittest tests.test_unit_price_macro_analysis -v`

Expected: FAIL because the macro data file and analysis module do not exist.

- [ ] **Step 3: Implement yearly macro inputs, Pearson analysis, and forecast weights**

```csv
year,brent_usd_bbl,cpi_index,steel_hrc_usd_ton,source_note
2019,64.3,255.7,603.0,curated_annual_average
2020,41.8,258.8,560.0,curated_annual_average
2021,70.7,271.0,1650.0,curated_annual_average
2022,100.9,292.7,935.0,curated_annual_average
2023,82.2,305.3,845.0,curated_annual_average
2024,80.0,314.0,815.0,curated_annual_average
2025,79.0,318.0,790.0,curated_proxy
2026,80.0,324.0,780.0,curated_proxy
```

```python
def build_forecast_weight_rows(series_rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for (field, pricing_basis), rows in group_series(series_rows).items():
        corr = {
            "brent_usd_bbl": pearson(unit_prices(rows), values(rows, "brent_usd_bbl")),
            "cpi_index": pearson(unit_prices(rows), values(rows, "cpi_index")),
            "steel_hrc_usd_ton": pearson(unit_prices(rows), values(rows, "steel_hrc_usd_ton")),
        }
        usable = {k: v for k, v in corr.items() if v is not None and abs(v) >= 0.30}
        denom = sum(abs(v) for v in usable.values()) or 1.0
        for factor_name, r in usable.items():
            out.append(
                {
                    "field": field,
                    "pricing_basis": pricing_basis,
                    "factor_name": factor_name,
                    "pearson_r": f"{r:.6f}",
                    "direction": "positive" if r >= 0 else "negative",
                    "forecast_weight": f"{abs(r) / denom:.6f}",
                    "series_basis": "as_is_nominal",
                }
            )
    return out
```

```markdown
Decision rule:
- Use overlapping observed unit-price years only for Pearson correlation.
- Use nominal annual series as the operational weighting basis.
- Compute discounted/NPV-style comparison only as a diagnostic appendix, not as the default forecast driver.
```

- [ ] **Step 4: Run the macro pipeline and tests**

Run: `python src/modeling/unit_price_macro_analysis.py`

Run: `python -m unittest tests.test_unit_price_macro_analysis -v`

Expected: PASS, with `unit_price_macro_weights.csv` and `reports/unit_price_macro_correlation.md` showing factor weights by field and pricing basis.

- [ ] **Step 5: Commit**

```bash
git add data/reference/macro_series_2019_2026.csv src/modeling/unit_price_macro_analysis.py tests/test_unit_price_macro_analysis.py reports/unit_price_macro_correlation.md
git commit -m "feat: add macro pearson weighting for unit price forecasts"
```

## Task 4: Build Standard-Only Well Unit-Price Analysis and Service-Time Bands

**Files:**

- Create: `src/modeling/unit_price_well_analysis.py`
- Create: `tests/test_unit_price_well_analysis.py`
- Modify: `src/cleaning/wbs_lv5_driver_alignment.py`
- Report: `reports/unit_price_well_analysis.md`

- [ ] **Step 1: Write the failing well-analysis tests**

```python
WELL_ANALYSIS = ROOT / "data" / "processed" / "unit_price_well_rates.csv"
SERVICE_BANDS = ROOT / "data" / "processed" / "service_time_band_reference.csv"
WELL_CONTEXT = ROOT / "data" / "processed" / "well_instance_context.csv"

    def test_well_context_contains_active_operational_days(self) -> None:
        rows = list(csv.DictReader(WELL_CONTEXT.open(encoding="utf-8", newline="")))
        self.assertIn("active_operational_days", rows[0])

    def test_service_time_bands_are_field_specific_and_standard_only(self) -> None:
        rows = list(csv.DictReader(SERVICE_BANDS.open(encoding="utf-8", newline="")))
        self.assertTrue({"field", "band_label", "pace_min_ft_per_day", "pace_max_ft_per_day"}.issubset(rows[0].keys()))
        self.assertNotIn("complexity_class", rows[0])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_unit_price_well_analysis -v`

Expected: FAIL because `active_operational_days` and the new band output do not exist.

- [ ] **Step 3: Add active-day feature engineering and field-specific pace bands**

```python
context_row["active_operational_days"] = f"{max(parse_float(context_row['actual_days']) - parse_float(context_row['npt_days']), 0.0):.6f}"
```

```python
def classify_service_band(rate_ft_per_day: float, p33: float, p67: float) -> str:
    if rate_ft_per_day <= p33:
        return "Careful"
    if rate_ft_per_day >= p67:
        return "Fast"
    return "Standard"
```

```python
def build_service_band_reference(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for field, field_rows in group_by_field(rows).items():
        pace_values = [float(r["actual_depth"]) / float(r["active_operational_days"]) for r in field_rows if float(r["active_operational_days"]) > 0 and float(r["actual_depth"]) > 0]
        p33 = percentile(pace_values, 0.33)
        p67 = percentile(pace_values, 0.67)
        out.extend(
            [
                {"field": field, "band_label": "Careful", "pace_min_ft_per_day": "0.000000", "pace_max_ft_per_day": f"{p33:.6f}"},
                {"field": field, "band_label": "Standard", "pace_min_ft_per_day": f"{p33:.6f}", "pace_max_ft_per_day": f"{p67:.6f}"},
                {"field": field, "band_label": "Fast", "pace_min_ft_per_day": f"{p67:.6f}", "pace_max_ft_per_day": ""},
            ]
        )
    return out
```

```markdown
Do not segment or forecast by well complexity.
All new estimated wells are treated as `Standard-J`.
Historical `deviation_type` remains source audit context only.
```

- [ ] **Step 4: Run the analysis and tests**

Run: `python src/cleaning/wbs_lv5_driver_alignment.py`

Run: `python src/modeling/unit_price_well_analysis.py`

Run: `python -m unittest tests.test_unit_price_well_analysis -v`

Expected: PASS, with `active_operational_days` in `well_instance_context.csv` and field-specific `Fast/Standard/Careful` pace ranges generated.

- [ ] **Step 5: Commit**

```bash
git add src/cleaning/wbs_lv5_driver_alignment.py src/modeling/unit_price_well_analysis.py tests/test_unit_price_well_analysis.py reports/unit_price_well_analysis.md
git commit -m "feat: add standard-only well unit price analysis"
```

## Task 5: Quantify NPT Contributors and Derive Penalty References

**Files:**

- Create: `src/modeling/unit_price_npt_analysis.py`
- Create: `tests/test_unit_price_npt_analysis.py`
- Report: `reports/unit_price_npt_contribution.md`

- [ ] **Step 1: Write the failing NPT-analysis tests**

```python
NPT_SUMMARY = ROOT / "data" / "processed" / "npt_contribution_summary.csv"
NPT_PENALTY = ROOT / "data" / "processed" / "npt_penalty_reference.csv"

    def test_npt_summary_has_major_and_detail_rollups(self) -> None:
        rows = list(csv.DictReader(NPT_SUMMARY.open(encoding="utf-8", newline="")))
        self.assertTrue({"field", "event_major_category", "event_detail", "npt_days_total", "npt_share_pct"}.issubset(rows[0].keys()))

    def test_npt_penalty_reference_uses_service_day_rate(self) -> None:
        rows = list(csv.DictReader(NPT_PENALTY.open(encoding="utf-8", newline="")))
        self.assertTrue({"field", "event_major_category", "penalty_usd_per_npt_day", "penalty_basis"}.issubset(rows[0].keys()))
```

- [ ] **Step 2: Run the NPT tests to verify they fail**

Run: `python -m unittest tests.test_unit_price_npt_analysis -v`

Expected: FAIL because the NPT summary and penalty files do not exist.

- [ ] **Step 3: Implement NPT contributor aggregation and penalty references**

```python
def build_npt_contribution_rows(event_rows: list[dict]) -> list[dict]:
    totals = defaultdict(float)
    for row in event_rows:
        key = (row["field"], row["event_major_category"], row["event_detail"])
        totals[key] += float(row["event_duration_days"] or 0.0)

    by_field = defaultdict(float)
    for (field, _, _), days in totals.items():
        by_field[field] += days

    out: list[dict] = []
    for (field, major, detail), days in sorted(totals.items()):
        out.append(
            {
                "field": field,
                "event_major_category": major,
                "event_detail": detail,
                "npt_days_total": f"{days:.6f}",
                "npt_share_pct": f"{(days / by_field[field] * 100 if by_field[field] else 0.0):.2f}",
            }
        )
    return out
```

```python
def build_npt_penalty_reference(contrib_rows: list[dict], rate_rows: list[dict]) -> list[dict]:
    service_day_rate = median_service_day_rate_by_field(rate_rows)
    out: list[dict] = []
    for row in contrib_rows:
        out.append(
            {
                "field": row["field"],
                "event_major_category": row["event_major_category"],
                "event_detail": row["event_detail"],
                "penalty_usd_per_npt_day": f"{service_day_rate[row['field']]:.6f}",
                "penalty_basis": "median_active_day_service_rate",
            }
        )
    return out
```

- [ ] **Step 4: Run the NPT pipeline and tests**

Run: `python src/modeling/unit_price_npt_analysis.py`

Run: `python -m unittest tests.test_unit_price_npt_analysis -v`

Expected: PASS, with NPT Pareto outputs and field-specific penalty references written to `data/processed/`.

- [ ] **Step 5: Commit**

```bash
git add src/modeling/unit_price_npt_analysis.py tests/test_unit_price_npt_analysis.py reports/unit_price_npt_contribution.md
git commit -m "feat: add npt contribution and penalty analysis"
```

## Task 6: Wire Forecast Outputs and Keep the Current Endpoint Compatible

**Files:**

- Modify: `src/modeling/phase5_estimation_core.py`
- Modify: `src/modeling/streamlined_etl_pipeline.py`
- Modify: `src/app/components/input_panel.py`
- Modify: `docs/refresh_runbook.md`
- Modify: `tests/test_phase5_estimator_engine.py`
- Modify: `tests/test_streamlined_etl_pipeline.py`

- [ ] **Step 1: Write the failing compatibility tests**

```python
    def test_endpoint_accepts_ww_field_and_standard_only_logic(self) -> None:
        campaign_input = {
            "year": 2026,
            "field": "WW",
            "no_pads": 1,
            "no_wells": 1,
            "no_pad_expansion": 0,
            "use_external_forecast": True,
            "use_synthetic_data": False,
        }
        well_rows = [{"well_label": "Well-1", "pad_label": "Pad-1", "depth_ft": 7000, "drill_rate_mode": "Standard"}]
        payload = run_pipeline_endpoint(campaign_input, well_rows, refresh_pipeline=False)
        self.assertEqual(payload["campaign_summary"]["field"], "WAYANG_WINDU")
```

```python
    def test_external_adjustment_reads_macro_weights(self) -> None:
        result = estimate_campaign(
            {"year": 2026, "field": "SLK", "no_pads": 1, "no_wells": 1, "no_pad_expansion": 0, "use_external_forecast": True, "use_synthetic_data": False},
            [{"well_label": "Well-1", "pad_label": "Pad-1", "depth_ft": 7000, "drill_rate_mode": "Standard"}],
        )
        self.assertIn("external_adjustment_formula", result["run_manifest"])
        self.assertNotEqual(result["run_manifest"]["external_adjustment_formula"], "fallback_historical_only_external_series_unavailable")
```

- [ ] **Step 2: Run the compatibility tests to verify they fail**

Run: `python -m unittest tests.test_streamlined_etl_pipeline.TestStreamlinedEtlPipeline.test_endpoint_accepts_ww_field_and_standard_only_logic -v`

Run: `python -m unittest tests.test_phase5_estimator_engine.TestPhase5EstimatorEngine.test_campaign_estimate_and_reconciliation -v`

Expected: FAIL because WW is not accepted and `_external_adjustment()` is still a stub.

- [ ] **Step 3: Implement the minimal endpoint compatibility layer**

```python
FIELD_MAP = {"DRJ": "DARAJAT", "SLK": "SALAK", "WW": "WAYANG_WINDU"}
RATE_FACTOR = {"Standard": 1.0, "Fast": 0.92, "Careful": 1.12}
```

```python
def normalize_inputs(campaign_input: dict, well_rows: list[dict]) -> tuple[dict, list[WellInput]]:
    field = campaign_input.get("field")
    if field not in {"SLK", "DRJ", "WW"}:
        raise ValueError("Field must be SLK, DRJ, or WW")
    normalized_wells = []
    for idx, row in enumerate(well_rows, start=1):
        normalized_wells.append(
            WellInput(
                well_label=row.get("well_label", f"Well-{idx}"),
                pad_label=row["pad_label"],
                depth_ft=_normalize_depth(int(row["depth_ft"])),
                depth_bucket_ft=_normalize_depth(int(row["depth_ft"])),
                leg_type="Standard-J",
                drill_rate_mode=row["drill_rate_mode"],
            )
        )
    return normalized_campaign, normalized_wells
```

```python
def _external_adjustment(enabled: bool, field: str, year: int, pricing_basis: str = "active_day_rate") -> tuple[float, bool, str]:
    if not enabled:
        return 1.0, False, "disabled_by_user"
    weights = load_macro_weight_row(field=field, year=year, pricing_basis=pricing_basis)
    if not weights:
        return 1.0, False, "fallback_historical_only_macro_weights_unavailable"
    factor = 1.0 + weighted_macro_return(weights)
    return factor, True, weights["formula_text"]
```

```python
field = st.sidebar.selectbox("Field", ["SLK", "DRJ", "WW"], index=0)
```

- [ ] **Step 4: Run the full targeted checks**

Run: `python src/modeling/streamlined_etl_pipeline.py --refresh-only`

Run: `python -m unittest tests.test_unit_price_history_pipeline tests.test_unit_price_macro_analysis tests.test_unit_price_well_analysis tests.test_unit_price_npt_analysis tests.test_streamlined_etl_pipeline tests.test_phase5_estimator_engine -v`

Expected: PASS, with the ETL manifest listing the new unit-price outputs and the endpoint remaining reconciled.

- [ ] **Step 5: Commit**

```bash
git add src/modeling/phase5_estimation_core.py src/modeling/streamlined_etl_pipeline.py src/app/components/input_panel.py docs/refresh_runbook.md tests/test_streamlined_etl_pipeline.py tests/test_phase5_estimator_engine.py
git commit -m "feat: wire standard-only unit price forecast outputs into estimator"
```

## Self-Review Checklist

- [ ] Confirm the plan covers all seven campaigns and all three fields.
- [ ] Confirm the plan uses `active_operational_days = actual_days - npt_days`.
- [ ] Confirm the plan removes well-complexity separation from the estimator path.
- [ ] Confirm Pearson weighting uses annual nominal series as the default, with NPV-style comparison treated only as a diagnostic appendix.
- [ ] Confirm `WW` appears in canonical mappings, manifests, and compatibility tests.
- [ ] Confirm every new processed output has an explicit generating module and at least one test.
