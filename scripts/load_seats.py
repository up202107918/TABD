"""
Load operational.seat_result from CNE mapa_2 (no full ETL).

Usage (repo root):
  .\\.venv\\Scripts\\python.exe scripts\\load_seats.py --dataset aut_2021
  .\\.venv\\Scripts\\python.exe scripts\\load_seats.py --dataset aut_2017
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))

from config import DATASETS  # noqa: E402
from pipeline.db import connect  # noqa: E402
from pipeline.load_seats import run_load_seat_results  # noqa: E402
from pipeline.runner import setup_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Load seat_result from CNE mapa_2")
    parser.add_argument(
        "--dataset",
        choices=sorted(DATASETS.keys()),
        default="aut_2021",
        help="Dataset key (must match loaded election in operational)",
    )
    args = parser.parse_args()
    setup_logging()
    conn = connect()
    try:
        stats = run_load_seat_results(conn, args.dataset)
        print(stats)
        total = stats.get("seat_result_total", 0)
        if total == 0:
            print(
                "WARNING: no seat_result rows — check mapa_2 file under etl/data/ "
                f"for {args.dataset}",
                file=sys.stderr,
            )
            return 1
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
