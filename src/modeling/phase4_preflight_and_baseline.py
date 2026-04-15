#!/usr/bin/env python3
"""Phase 4 preflight gate runner and deterministic baseline generator.

Enhancements in this revision:
- Adds aggregation grain controls to avoid single-row Lv5-only baselines.
- Adds synthetic data toggles to optionally enrich sample coverage.
- Publishes driver-to-cost aggregation report for immediate estimator-readiness feedback.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

MASTER_PATH = PROCESSED_DIR / "wbs_lv5_master.csv"
CLASSIFICATION_PATH = PROCESSED_DIR / "wbs_lv5_classification.csv"
SYNTHETIC_LV5_PATH = PROCESSED_DIR / "synthetic_wbs_lv5_placeholders.csv"

GATE_RESULTS_PATH = PROCESSED_DIR / "phase4_gate_results.csv"
BASELINE_DARAJAT_PATH = PROCESSED_DIR / "baseline_estimates_darajat.csv"
BASELINE_SALAK_PATH = PROCESSED_DIR / "baseline_estimates_salak.csv"
RUN_MANIFEST_PATH = PROCESSED_DIR / "phase4_run_manifest.json"

GATE_REPORT_PATH = REPORTS_DIR / "phase4_gate_preflight_report.md"
DRIVER_REPORT_PATH = REPORTS_DIR / "phase4_driver_analysis.md"

VALID_FIELDS = {"DARAJAT", "SALAK"}
VALID_CLASSIFICATIONS = {"well_tied", "campaign_tied", "hybrid"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 4 gate checks and deterministic baseline generation.")
    parser.add_argument(
        "--group-by",
        choices=["family", "lv5"],
        default="family",
        help="Baseline aggregation grain. 'family' supports cross-campaign-year mapping within field.",
    )
    parser.add_argument(
        "--use-synthetic",
        action="store_true",
        help="Include synthetic Lv5 placeholder rows as optional sample enrichments.",
    )
    parser.add_argument(
        "--synthetic-policy",
        choices=["training", "all"],
        default="training",
        help="When --use-synthetic is enabled, include only training-approved rows or all placeholders.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def parse_cost(value: str) -> float:
    text = (value or "").strip()
    if not text:
        return 0.0
    return float(text.replace(",", ""))


def percentile(values: Iterable[float], pct: float) -> float:
    arr = sorted(values)
    if not arr:
        return 0.0
    if len(arr) == 1:
        return arr[0]
    idx = (len(arr) - 1) * pct
    lo = int(idx)
    hi = min(lo + 1, len(arr) - 1)
    frac = idx - lo
    return arr[lo] * (1 - frac) + arr[hi] * frac


def normalize_text(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", (value or "").strip().lower())
    return re.sub(r"[^a-z0-9]+", "_", collapsed).strip("_")


def build_classification_maps(classification_rows: List[dict]) -> Tuple[Dict[str, dict], Dict[Tuple[str, str], str], Dict[Tuple[str, str], str]]:
    key_map = {row["classification_key"]: row for row in classification_rows}

    family_to_class: Dict[Tuple[str, str], str] = {}
    family_to_driver: Dict[Tuple[str, str], str] = {}
    votes: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
    driver_votes: Dict[Tuple[str, str], Counter] = defaultdict(Counter)

    for row in classification_rows:
        field = (row.get("field") or "").strip()
        family = normalize_text(row.get("wbs_family_tag", ""))
        if not field or not family:
            continue
        votes[(field, family)][(row.get("classification") or "").strip()] += 1
        driver_votes[(field, family)][(row.get("driver_family") or "").strip()] += 1

    for key, counter in votes.items():
        family_to_class[key] = counter.most_common(1)[0][0] if counter else "unclassified"
    for key, counter in driver_votes.items():
        family_to_driver[key] = counter.most_common(1)[0][0] if counter else "unknown_driver"

    return key_map, family_to_class, family_to_driver


def evaluate_gates(master_rows: List[dict], classification_rows: List[dict]) -> List[dict]:
    hierarchy_cols = ["wbs_lvl1", "wbs_lvl2", "wbs_lvl3", "wbs_lvl4", "wbs_lvl5"]
    hierarchy_blanks = sum(
        1
        for row in master_rows
        if any(not (row.get(col) or "").strip() for col in hierarchy_cols)
    )

    campaign_blanks = sum(
        1
        for row in master_rows
        if not (row.get("campaign_code") or "").strip()
        or not (row.get("campaign_canonical") or "").strip()
    )

    valid_field_rows = sum(1 for row in master_rows if (row.get("field") or "").strip() in VALID_FIELDS)

    keys = [row.get("classification_key", "") for row in classification_rows]
    duplicate_count = len(keys) - len(set(keys))

    valid_class_rows = sum(
        1
        for row in classification_rows
        if (row.get("classification") or "").strip() in VALID_CLASSIFICATIONS
    )

    coverage = defaultdict(lambda: defaultdict(int))
    for row in classification_rows:
        field = (row.get("field") or "").strip()
        klass = (row.get("classification") or "").strip()
        if field in VALID_FIELDS and klass in VALID_CLASSIFICATIONS:
            coverage[field][klass] += 1

    well_populated = sum(1 for row in master_rows if (row.get("well_canonical") or "").strip())
    event_populated = sum(1 for row in master_rows if (row.get("event_code_raw") or "").strip())

    gates = [
        {
            "gate_id": "G1",
            "gate": "Hierarchy completeness (wbs_lvl1..wbs_lvl5)",
            "threshold": "0 blank rows",
            "observed": str(hierarchy_blanks),
            "status": "PASS" if hierarchy_blanks == 0 else "FAIL",
            "detail": "Rows with any blank hierarchy column.",
        },
        {
            "gate_id": "G2",
            "gate": "Campaign mapping completeness",
            "threshold": "0 blank rows",
            "observed": str(campaign_blanks),
            "status": "PASS" if campaign_blanks == 0 else "FAIL",
            "detail": "Rows with blank campaign_code or campaign_canonical.",
        },
        {
            "gate_id": "G3",
            "gate": "Field membership validity",
            "threshold": "100% in {DARAJAT,SALAK}",
            "observed": f"{valid_field_rows}/{len(master_rows)}",
            "status": "PASS" if valid_field_rows == len(master_rows) else "FAIL",
            "detail": "Master rows with valid field values.",
        },
        {
            "gate_id": "G4",
            "gate": "Classification key uniqueness",
            "threshold": "0 duplicates",
            "observed": str(duplicate_count),
            "status": "PASS" if duplicate_count == 0 else "FAIL",
            "detail": "Duplicate classification_key count.",
        },
        {
            "gate_id": "G5",
            "gate": "Classification label validity",
            "threshold": "100% in {well_tied,campaign_tied,hybrid}",
            "observed": f"{valid_class_rows}/{len(classification_rows)}",
            "status": "PASS" if valid_class_rows == len(classification_rows) else "FAIL",
            "detail": "Classification rows with valid class labels.",
        },
        {
            "gate_id": "G6",
            "gate": "Field-specific class coverage reported",
            "threshold": "mandatory report",
            "observed": "Reported" if all(f in coverage for f in VALID_FIELDS) else "Missing",
            "status": "PASS" if all(f in coverage for f in VALID_FIELDS) else "FAIL",
            "detail": json.dumps(coverage, sort_keys=True),
        },
        {
            "gate_id": "G7",
            "gate": "Well attribution coverage disclosure",
            "threshold": "mandatory disclosure if <100%",
            "observed": f"{well_populated}/{len(master_rows)} populated",
            "status": "PASS" if well_populated == len(master_rows) else "KNOWN LIMITATION",
            "detail": "Continue with campaign/WBS-grain design when incomplete.",
        },
        {
            "gate_id": "G8",
            "gate": "Event-code coverage disclosure",
            "threshold": "mandatory disclosure if <100%",
            "observed": f"{event_populated}/{len(master_rows)} populated",
            "status": "PASS" if event_populated == len(master_rows) else "KNOWN LIMITATION",
            "detail": "Continue with campaign/WBS-grain design when incomplete.",
        },
    ]
    return gates


def derive_group_key(row: dict, class_row: dict | None, group_by: str) -> Tuple[str, str, str, str]:
    field = (row.get("field") or "").strip()
    family_tag = normalize_text((class_row or {}).get("wbs_family_tag", "") or row.get("tag_lvl5", ""))
    classification = (class_row or {}).get("classification", "").strip() or "unclassified"
    driver_family = (class_row or {}).get("driver_family", "").strip() or "unknown_driver"

    if group_by == "lv5":
        group_key = (row.get("wbs_lvl5") or "").strip()
        return field, group_key, classification, driver_family

    # family grain for cross-campaign-year mapping within field
    group_key = family_tag or normalize_text((row.get("wbs_label_raw") or "").strip()) or "unknown_family"
    return field, group_key, classification, driver_family


def convert_synthetic_rows(
    synthetic_rows: List[dict],
    family_to_class: Dict[Tuple[str, str], str],
    family_to_driver: Dict[Tuple[str, str], str],
    policy: str,
    group_by: str,
) -> List[dict]:
    converted: List[dict] = []
    for row in synthetic_rows:
        if (row.get("is_synthetic") or "").strip().lower() != "yes":
            continue
        if policy == "training" and (row.get("include_for_training") or "").strip().lower() != "yes":
            continue

        field = (row.get("Asset") or "").strip().upper()
        if field not in VALID_FIELDS:
            continue

        family_key = normalize_text(row.get("L5_Group", "") or row.get("Description", ""))
        classification = family_to_class.get((field, family_key), "unclassified")
        driver_family = family_to_driver.get((field, family_key), "unknown_driver")

        family_label = (row.get("L5_Group") or row.get("Description") or "").strip()
        converted.append(
            {
                "field": field,
                "group_by": group_by,
                "group_key": (row.get("WBS_ID") or "").strip() if group_by == "lv5" else (family_key or normalize_text(family_label) or "unknown_family"),
                "classification": classification,
                "driver_family": driver_family,
                "campaign_code": (row.get("Campaign") or "").strip(),
                "cost_actual": parse_cost(row.get("ACTUAL, USD", "0")),
                "is_synthetic": "yes",
            }
        )
    return converted


def build_analysis_rows(
    master_rows: List[dict],
    class_map: Dict[str, dict],
    group_by: str,
) -> List[dict]:
    rows: List[dict] = []
    for row in master_rows:
        key = "|".join(
            [
                (row.get("field") or "").strip(),
                (row.get("wbs_lvl2") or "").strip(),
                (row.get("wbs_lvl3") or "").strip(),
                (row.get("wbs_lvl4") or "").strip(),
                (row.get("wbs_lvl5") or "").strip(),
            ]
        )
        class_row = class_map.get(key)
        field, group_key, classification, driver_family = derive_group_key(row, class_row, group_by)
        rows.append(
            {
                "field": field,
                "group_by": group_by,
                "group_key": group_key,
                "classification": classification,
                "driver_family": driver_family,
                "campaign_code": (row.get("campaign_code") or "").strip(),
                "cost_actual": parse_cost(row.get("cost_actual", "0")),
                "is_synthetic": "no",
            }
        )
    return rows


def generate_baselines(analysis_rows: List[dict]) -> Tuple[List[dict], List[dict]]:
    buckets: Dict[Tuple[str, str, str, str], List[float]] = defaultdict(list)
    synthetic_counts: Dict[Tuple[str, str, str, str], int] = defaultdict(int)
    campaign_sets: Dict[Tuple[str, str, str, str], set] = defaultdict(set)

    for row in analysis_rows:
        group_key = (row["field"], row["group_key"], row["classification"], row["driver_family"])
        buckets[group_key].append(float(row["cost_actual"]))
        if row.get("is_synthetic") == "yes":
            synthetic_counts[group_key] += 1
        campaign_sets[group_key].add(row.get("campaign_code", ""))

    output_rows: List[dict] = []
    for (field, group_key, classification, driver_family), values in sorted(buckets.items()):
        output_rows.append(
            {
                "field": field,
                "group_key": group_key,
                "classification": classification,
                "driver_family": driver_family,
                "sample_size": len(values),
                "campaign_count": len([x for x in campaign_sets[(field, group_key, classification, driver_family)] if x]),
                "synthetic_rows_used": synthetic_counts[(field, group_key, classification, driver_family)],
                "cost_total": round(sum(values), 6),
                "cost_mean": round(sum(values) / len(values), 6),
                "cost_median": round(median(values), 6),
                "cost_p10": round(percentile(values, 0.10), 6),
                "cost_p90": round(percentile(values, 0.90), 6),
                "cost_min": round(min(values), 6),
                "cost_max": round(max(values), 6),
                "estimator_readiness": "ready" if len(values) >= 3 else "thin_sample",
            }
        )

    darajat = [row for row in output_rows if row["field"] == "DARAJAT"]
    salak = [row for row in output_rows if row["field"] == "SALAK"]
    return darajat, salak


def build_driver_summary(analysis_rows: List[dict]) -> Dict[str, List[dict]]:
    totals_by_field = defaultdict(float)
    by_driver = defaultdict(float)
    by_class = defaultdict(float)

    for row in analysis_rows:
        field = row["field"]
        cost = float(row["cost_actual"])
        totals_by_field[field] += cost
        by_driver[(field, row["driver_family"])] += cost
        by_class[(field, row["classification"])] += cost

    result: Dict[str, List[dict]] = {"driver": [], "classification": []}

    for (field, driver), total_cost in sorted(by_driver.items()):
        denom = totals_by_field[field] or 1.0
        result["driver"].append(
            {
                "field": field,
                "driver_family": driver,
                "cost_total": round(total_cost, 6),
                "cost_share": round(total_cost / denom, 6),
            }
        )

    for (field, klass), total_cost in sorted(by_class.items()):
        denom = totals_by_field[field] or 1.0
        result["classification"].append(
            {
                "field": field,
                "classification": klass,
                "cost_total": round(total_cost, 6),
                "cost_share": round(total_cost / denom, 6),
            }
        )

    return result


def write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_gate_report(gates: List[dict], master_rows: List[dict], classification_rows: List[dict], args: argparse.Namespace) -> None:
    status = "PASS" if all(g["status"] == "PASS" for g in gates[:6]) else "HOLD"
    lines = [
        "# Phase 4 Gate Preflight Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Runtime Toggles",
        f"- group_by: `{args.group_by}`",
        f"- use_synthetic: `{args.use_synthetic}`",
        f"- synthetic_policy: `{args.synthetic_policy if args.use_synthetic else 'not_applied'}`",
        "",
        "## Snapshot",
        f"- `wbs_lv5_master.csv` rows: **{len(master_rows)}**",
        f"- `wbs_lv5_classification.csv` rows: **{len(classification_rows)}**",
        f"- Gate recommendation (G1-G6): **{status}**",
        "",
        "## Gate Results",
        "| gate_id | gate | threshold | observed | status |",
        "|---|---|---:|---:|---|",
    ]
    for gate in gates:
        lines.append(
            f"| {gate['gate_id']} | {gate['gate']} | {gate['threshold']} | {gate['observed']} | {gate['status']} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "- G7 and G8 are disclosure gates and remain non-blocking known limitations when coverage is incomplete.",
            "- Baseline artifacts are generated only when G1-G6 pass.",
        ]
    )

    GATE_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_driver_report(driver_summary: Dict[str, List[dict]], args: argparse.Namespace) -> None:
    lines = [
        "# Phase 4 Driver-to-Cost Aggregation Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Runtime Toggles",
        f"- group_by: `{args.group_by}`",
        f"- use_synthetic: `{args.use_synthetic}`",
        f"- synthetic_policy: `{args.synthetic_policy if args.use_synthetic else 'not_applied'}`",
        "",
        "## Driver Family Cost Share",
        "| field | driver_family | cost_total | cost_share |",
        "|---|---|---:|---:|",
    ]

    for row in driver_summary["driver"]:
        lines.append(
            f"| {row['field']} | {row['driver_family']} | {row['cost_total']} | {row['cost_share']} |"
        )

    lines.extend(
        [
            "",
            "## Classification Cost Share",
            "| field | classification | cost_total | cost_share |",
            "|---|---|---:|---:|",
        ]
    )
    for row in driver_summary["classification"]:
        lines.append(
            f"| {row['field']} | {row['classification']} | {row['cost_total']} | {row['cost_share']} |"
        )

    DRIVER_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_phase4(group_by: str = "family", use_synthetic: bool = False, synthetic_policy: str = "training") -> dict:
    args = argparse.Namespace(
        group_by=group_by,
        use_synthetic=use_synthetic,
        synthetic_policy=synthetic_policy,
    )

    master_rows = read_csv(MASTER_PATH)
    classification_rows = read_csv(CLASSIFICATION_PATH)
    class_map, family_to_class, family_to_driver = build_classification_maps(classification_rows)

    gates = evaluate_gates(master_rows, classification_rows)
    write_csv(GATE_RESULTS_PATH, gates)
    write_gate_report(gates, master_rows, classification_rows, args)

    blocking_gate_failed = any(g["status"] == "FAIL" for g in gates[:6])
    if blocking_gate_failed:
        raise SystemExit("Blocking gate failed (G1-G6). Baseline outputs were not generated.")

    analysis_rows = build_analysis_rows(master_rows, class_map, group_by=args.group_by)

    synthetic_rows_used = 0
    if args.use_synthetic:
        synthetic_rows = read_csv(SYNTHETIC_LV5_PATH)
        converted = convert_synthetic_rows(
            synthetic_rows,
            family_to_class=family_to_class,
            family_to_driver=family_to_driver,
            policy=args.synthetic_policy,
            group_by=args.group_by,
        )
        analysis_rows.extend(converted)
        synthetic_rows_used = len(converted)

    darajat_rows, salak_rows = generate_baselines(analysis_rows)
    write_csv(BASELINE_DARAJAT_PATH, darajat_rows)
    write_csv(BASELINE_SALAK_PATH, salak_rows)

    driver_summary = build_driver_summary(analysis_rows)
    write_driver_report(driver_summary, args)

    manifest = {
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_toggles": {
            "group_by": args.group_by,
            "use_synthetic": args.use_synthetic,
            "synthetic_policy": args.synthetic_policy if args.use_synthetic else "not_applied",
        },
        "inputs": {
            "wbs_lv5_master": {
                "path": str(MASTER_PATH.relative_to(ROOT)),
                "sha256": file_sha256(MASTER_PATH),
                "row_count": len(master_rows),
            },
            "wbs_lv5_classification": {
                "path": str(CLASSIFICATION_PATH.relative_to(ROOT)),
                "sha256": file_sha256(CLASSIFICATION_PATH),
                "row_count": len(classification_rows),
            },
            "synthetic_wbs_lv5_placeholders": {
                "path": str(SYNTHETIC_LV5_PATH.relative_to(ROOT)),
                "sha256": file_sha256(SYNTHETIC_LV5_PATH),
                "rows_used": synthetic_rows_used,
            },
        },
        "outputs": {
            "phase4_gate_results": str(GATE_RESULTS_PATH.relative_to(ROOT)),
            "baseline_estimates_darajat": str(BASELINE_DARAJAT_PATH.relative_to(ROOT)),
            "baseline_estimates_salak": str(BASELINE_SALAK_PATH.relative_to(ROOT)),
            "phase4_gate_report": str(GATE_REPORT_PATH.relative_to(ROOT)),
            "phase4_driver_analysis_report": str(DRIVER_REPORT_PATH.relative_to(ROOT)),
        },
        "notes": [
            "This run remains deterministic and does not fit predictive statistical models.",
            "Family-grain aggregation is the default to support cross-campaign-year mapping readiness within field.",
        ],
    }
    RUN_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    args = parse_args()
    run_phase4(
        group_by=args.group_by,
        use_synthetic=args.use_synthetic,
        synthetic_policy=args.synthetic_policy,
    )


if __name__ == "__main__":
    main()
