#!/usr/bin/env python3
"""Phase 4 preflight gate runner and deterministic baseline generator.

Implements Phase 4 kickoff immediate actions:
- Gate checks G1-G8 against Phase 3 validation definitions
- Deterministic baseline generation split by field (DARAJAT/SALAK)
- Auditable run metadata + markdown report outputs
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

MASTER_PATH = PROCESSED_DIR / "wbs_lv5_master.csv"
CLASSIFICATION_PATH = PROCESSED_DIR / "wbs_lv5_classification.csv"

GATE_RESULTS_PATH = PROCESSED_DIR / "phase4_gate_results.csv"
BASELINE_DARAJAT_PATH = PROCESSED_DIR / "baseline_estimates_darajat.csv"
BASELINE_SALAK_PATH = PROCESSED_DIR / "baseline_estimates_salak.csv"
RUN_MANIFEST_PATH = PROCESSED_DIR / "phase4_run_manifest.json"

GATE_REPORT_PATH = REPORTS_DIR / "phase4_gate_preflight_report.md"

VALID_FIELDS = {"DARAJAT", "SALAK"}
VALID_CLASSIFICATIONS = {"well_tied", "campaign_tied", "hybrid"}


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


def build_classification_map(classification_rows: List[dict]) -> Dict[str, dict]:
    return {row["classification_key"]: row for row in classification_rows}


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


def generate_baselines(master_rows: List[dict], class_map: Dict[str, dict]) -> Tuple[List[dict], List[dict]]:
    buckets: Dict[Tuple[str, str, str, str, str, str], List[float]] = defaultdict(list)

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
        cls_row = class_map.get(key)
        classification = "unclassified"
        if cls_row:
            classification = (cls_row.get("classification") or "").strip() or "unclassified"

        group_key = (
            (row.get("field") or "").strip(),
            (row.get("wbs_lvl2") or "").strip(),
            (row.get("wbs_lvl3") or "").strip(),
            (row.get("wbs_lvl4") or "").strip(),
            (row.get("wbs_lvl5") or "").strip(),
            classification,
        )
        buckets[group_key].append(parse_cost(row.get("cost_actual", "0")))

    output_rows: List[dict] = []
    for (field, lvl2, lvl3, lvl4, lvl5, classification), values in sorted(buckets.items()):
        output_rows.append(
            {
                "field": field,
                "wbs_lvl2": lvl2,
                "wbs_lvl3": lvl3,
                "wbs_lvl4": lvl4,
                "wbs_lvl5": lvl5,
                "classification": classification,
                "sample_size": len(values),
                "cost_total": round(sum(values), 6),
                "cost_mean": round(sum(values) / len(values), 6),
                "cost_median": round(median(values), 6),
                "cost_p10": round(percentile(values, 0.10), 6),
                "cost_p90": round(percentile(values, 0.90), 6),
                "cost_min": round(min(values), 6),
                "cost_max": round(max(values), 6),
            }
        )

    darajat = [row for row in output_rows if row["field"] == "DARAJAT"]
    salak = [row for row in output_rows if row["field"] == "SALAK"]
    return darajat, salak


def write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_gate_report(gates: List[dict], master_rows: List[dict], classification_rows: List[dict]) -> None:
    status = "PASS" if all(g["status"] == "PASS" for g in gates[:6]) else "HOLD"
    lines = [
        "# Phase 4 Gate Preflight Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
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


def main() -> None:
    master_rows = read_csv(MASTER_PATH)
    classification_rows = read_csv(CLASSIFICATION_PATH)
    class_map = build_classification_map(classification_rows)

    gates = evaluate_gates(master_rows, classification_rows)
    write_csv(GATE_RESULTS_PATH, gates)
    write_gate_report(gates, master_rows, classification_rows)

    blocking_gate_failed = any(g["status"] == "FAIL" for g in gates[:6])
    if blocking_gate_failed:
        raise SystemExit("Blocking gate failed (G1-G6). Baseline outputs were not generated.")

    darajat_rows, salak_rows = generate_baselines(master_rows, class_map)
    write_csv(BASELINE_DARAJAT_PATH, darajat_rows)
    write_csv(BASELINE_SALAK_PATH, salak_rows)

    manifest = {
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
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
        },
        "outputs": {
            "phase4_gate_results": str(GATE_RESULTS_PATH.relative_to(ROOT)),
            "baseline_estimates_darajat": str(BASELINE_DARAJAT_PATH.relative_to(ROOT)),
            "baseline_estimates_salak": str(BASELINE_SALAK_PATH.relative_to(ROOT)),
            "phase4_gate_report": str(GATE_REPORT_PATH.relative_to(ROOT)),
        },
        "notes": [
            "Phase 4 kickoff run includes deterministic baselines only.",
            "Statistical training/validation artifacts are intentionally out of scope for this step.",
        ],
    }
    RUN_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
