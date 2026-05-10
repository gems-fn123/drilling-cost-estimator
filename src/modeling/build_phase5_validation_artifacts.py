#!/usr/bin/env python3
from __future__ import annotations

from src.modeling.phase5_estimation_core import build_validation_artifacts


if __name__ == "__main__":
    try:
        build_validation_artifacts()
    except Exception as exc:
        print(f"Phase 5 refresh failed; falling back to existing processed artifacts. Reason: {exc}")
        build_validation_artifacts(refresh_pipeline=False)
