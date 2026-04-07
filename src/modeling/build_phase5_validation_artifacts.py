#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeling.phase5_estimation_core import build_validation_artifacts


if __name__ == "__main__":
    build_validation_artifacts()
