"""Shared pure-Python helpers for I/O, numerics, and statistics."""

from __future__ import annotations

import csv
import json
import logging
import math
import re
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not columns:
        path.write_text("", encoding="utf-8")
        return
    cols = columns or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


# ---------------------------------------------------------------------------
# Safe type coercions
# ---------------------------------------------------------------------------

def parse_float(value: object) -> float:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def safe_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def format_float(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


# ---------------------------------------------------------------------------
# String normalization
# ---------------------------------------------------------------------------

def normalize_key(value: str) -> str:
    """Lowercase slug: spaces and non-alphanumeric chars become underscores."""
    collapsed = re.sub(r"\s+", " ", (value or "").strip().lower())
    return re.sub(r"[^a-z0-9]+", "_", collapsed).strip("_")


def normalize_exclusion_well(well: str) -> str:
    """Uppercase well name stripped of trailing suffixes RD/ML/OH."""
    text = str(well or "").strip().upper()
    text = re.sub(r"([ -])(RD|ML|OH)$", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_year(text: str) -> int:
    match = re.search(r"(20\d{2})", str(text or ""))
    return int(match.group(1)) if match else 0


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def percentile(values: Iterable[float], pct: float) -> float:
    arr = sorted(values)
    if not arr:
        return 0.0
    if len(arr) == 1:
        return arr[0]
    idx = (len(arr) - 1) * pct
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    frac = idx - lo
    if lo == hi:
        return arr[lo]
    return arr[lo] * (1.0 - frac) + arr[hi] * frac


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0.0 or den_y == 0.0:
        return None
    return num / (den_x * den_y)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=level,
    )
