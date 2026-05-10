#!/usr/bin/env python3
"""Build per-section speed reference bands from Phase.Summary (DRILL + CSGCMT operations).

Each well's total time per section group is the sum of DRILL and CSGCMT phases for that
hole size — casing jobs are inclusive because they are inseparable from section drilling
cost in the unit-price model.

Section groups
--------------
surface_26          : 26", 30", 36" (conductor / surface hole)
intermediate_17_5   : 17.5" (intermediate casing section)
production_12_25    : 12.25", 9.875", 8.5", 7.875" (production / liner sections)

Winsorization
-------------
n >= 15  → 25th / 75th percentile (field-specific, low confidence flagged below 15)
n < 15   → pool across all fields for that section group, still 25/75
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from src.config import PROCESSED, RAW_DIR
from src.io.build_canonical_mappings import clean_text, extract_full_table, read_xlsx
from src.utils import write_csv

log = logging.getLogger(__name__)

DASHBOARD_WORKBOOK = "20260422_Data for Dashboard.xlsx"
SECTION_SPEED_REFERENCE = PROCESSED / "section_speed_reference.csv"

# Canonical hole-size mapping — all known format variants → canonical label
SIZE_CANON: dict[str, str] = {
    "26": "26",
    "30": "30",
    "36": "36",
    "17 1/2": "17.5",
    "17.5": "17.5",
    "17-1/2": "17.5",
    "12 1/4": "12.25",
    "12.25": "12.25",
    "12-1/4": "12.25",
    "9 7/8": "9.875",
    "9.875": "9.875",
    "9-7/8": "9.875",
    "8 1/2": "8.5",
    "8.5": "8.5",
    "7 7/8": "7.875",
    "7.875": "7.875",
    "7-7/8": "7.875",
}

# Section group assignment
SECTION_GROUP: dict[str, str] = {
    "26": "surface_26",
    "30": "surface_26",
    "36": "surface_26",
    "17.5": "intermediate_17_5",
    "12.25": "production_12_25",
    "9.875": "production_12_25",
    "8.5": "production_12_25",
    "7.875": "production_12_25",
}

SECTION_GROUP_LABEL: dict[str, str] = {
    "surface_26": "Surface (26\" and larger)",
    "intermediate_17_5": "Intermediate (17.5\")",
    "production_12_25": "Production (12.25\" and below)",
}

SECTION_GROUP_CANONICAL_SIZES: dict[str, str] = {
    "surface_26": "26, 30, 36",
    "intermediate_17_5": "17.5",
    "production_12_25": "12.25, 9.875, 8.5, 7.875",
}

TARGET_PHASES = {"DRILL", "CSGCMT"}

CAMPAIGN_FIELD_MAP: dict[str, str] = {
    "drj": "DARAJAT",
    "darajat": "DARAJAT",
    "slk": "SALAK",
    "salak": "SALAK",
    "ww": "WAYANG_WINDU",
    "wayang": "WAYANG_WINDU",
    "a_others": "WAYANG_WINDU",
}


def _field_from_campaign(campaign: str) -> str | None:
    c = clean_text(campaign).lower()
    for prefix, field in CAMPAIGN_FIELD_MAP.items():
        if prefix in c:
            return field
    return None


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = p * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def _winsorize_config(n: int) -> Tuple[float, float, str]:
    """Return (lo_p, hi_p, method_label) based on sample count."""
    if n >= 15:
        return 0.25, 0.75, "p25_p75"
    return 0.25, 0.75, "p25_p75_low_confidence"


def load_phase_summary() -> List[dict]:
    path = RAW_DIR / DASHBOARD_WORKBOOK
    if not path.exists():
        log.warning("Dashboard workbook not found at %s — section speed reference will be empty.", path)
        return []
    wb = read_xlsx(path)
    rows = extract_full_table(
        wb.get("Phase.Summary", []),
        [
            "Well Name",
            "Phase 1",
            "Phase 2",
            "Hole/Casing Size",
            "Actual Start Depth (ftKB)",
            "Actual End Depth (ftKB)",
            "Actual Dur (days)",
            "Campaign",
        ],
    )
    return rows


def build_well_section_durations(phase_rows: List[dict]) -> Dict[Tuple[str, str, str], float]:
    """Sum DRILL + CSGCMT duration per (well_name, field, section_group) combination."""
    totals: Dict[Tuple[str, str, str], float] = defaultdict(float)

    for row in phase_rows:
        phase2 = clean_text(row.get("Phase 2", "")).upper()
        if phase2 not in TARGET_PHASES:
            continue

        raw_size = clean_text(row.get("Hole/Casing Size", ""))
        canon_size = SIZE_CANON.get(raw_size)
        if canon_size is None:
            continue

        group = SECTION_GROUP.get(canon_size)
        if group is None:
            continue

        field = _field_from_campaign(row.get("Campaign", ""))
        if field is None:
            continue

        try:
            days = float(clean_text(row.get("Actual Dur (days)", "")))
        except (ValueError, TypeError):
            continue

        if days <= 0.0:
            continue

        well = clean_text(row.get("Well Name", ""))
        totals[(well, field, group)] += days

    return dict(totals)


def build_section_speed_reference(well_section_durations: Dict[Tuple[str, str, str], float]) -> List[dict]:
    """Compute per-field, per-section-group speed bands (Fast / Standard / Careful)."""

    # Group durations by (field, section_group)
    by_field_group: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    by_group: Dict[str, List[float]] = defaultdict(list)

    for (well, field, group), days in well_section_durations.items():
        by_field_group[(field, group)].append(days)
        by_group[group].append(days)

    rows: List[dict] = []

    for group in sorted(SECTION_GROUP_LABEL):
        for field in sorted({"DARAJAT", "SALAK", "WAYANG_WINDU"}):
            field_vals = sorted(by_field_group.get((field, group), []))
            n = len(field_vals)
            lo, hi, method = _winsorize_config(n)
            confidence = "medium" if n >= 15 else "low"

            field_n = len(field_vals)
            if n >= 15:
                fast_days = _percentile(field_vals, lo)
                p50_days = _percentile(field_vals, 0.5)
                careful_days = _percentile(field_vals, hi)
                source = "field_specific"
                note = f"n={field_n} field obs; 25th/75th percentile applied."
            else:
                # Fall back to pooled across all fields for this section group
                pool_vals = sorted(by_group.get(group, []))
                n_pool = len(pool_vals)
                fast_days = _percentile(pool_vals, 0.25) if pool_vals else 0.0
                p50_days = _percentile(pool_vals, 0.5) if pool_vals else 0.0
                careful_days = _percentile(pool_vals, 0.75) if pool_vals else 0.0
                source = "pooled_all_fields"
                confidence = "low"
                note = f"n={field_n} field obs (< 15); pooled all-field n={n_pool} used for bands."

            rows.append(
                {
                    "field": field,
                    "section_group": group,
                    "section_group_label": SECTION_GROUP_LABEL[group],
                    "canonical_sizes": SECTION_GROUP_CANONICAL_SIZES[group],
                    "phases_included": "DRILL,CSGCMT",
                    "field_observation_count": str(field_n),
                    "winsorization_method": method,
                    "band_source": source,
                    "estimator_confidence": confidence,
                    "fast_days": f"{fast_days:.2f}",
                    "standard_days": f"{p50_days:.2f}",
                    "careful_days": f"{careful_days:.2f}",
                    "note": note,
                }
            )

    return rows


def main() -> None:
    phase_rows = load_phase_summary()
    if not phase_rows:
        log.warning("No Phase.Summary rows loaded — writing empty section speed reference.")
        write_csv(SECTION_SPEED_REFERENCE, [], ["field", "section_group", "section_group_label", "canonical_sizes",
                                                  "phases_included", "field_observation_count", "winsorization_method",
                                                  "band_source", "estimator_confidence",
                                                  "fast_days", "standard_days", "careful_days", "note"])
        return

    well_section_durations = build_well_section_durations(phase_rows)
    reference_rows = build_section_speed_reference(well_section_durations)
    write_csv(SECTION_SPEED_REFERENCE, reference_rows, list(reference_rows[0].keys()))
    print(f"Wrote section_speed_reference ({len(reference_rows)} rows, {len(well_section_durations)} well-section observations).")


if __name__ == "__main__":
    main()
