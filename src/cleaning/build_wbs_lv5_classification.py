from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cleaning.wbs_lv5_driver_alignment import main as driver_alignment_main


if __name__ == "__main__":
    driver_alignment_main()
