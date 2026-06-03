"""
Backfill operational.turnout percentages after ETL bulk load (triggers were skipped).

Usage (from repo root):
  .\\.venv\\Scripts\\python.exe scripts\\fix_turnout_percentages.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))

from config import DB_CONFIG  # noqa: E402

import psycopg2  # noqa: E402


def main() -> int:
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM operational.turnout
                WHERE turnout_percentage IS NULL AND registered_voters > 0
                """
            )
            missing_before = cur.fetchone()[0]
            cur.execute("SELECT calculate_turnout_percentages()")
            updated = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*) FROM operational.turnout
                WHERE turnout_percentage IS NULL AND registered_voters > 0
                """
            )
            missing_after = cur.fetchone()[0]
        conn.commit()
        print(f"Rows missing % before: {missing_before}")
        print(f"calculate_turnout_percentages() updated: {updated}")
        print(f"Rows still missing % after: {missing_after}")
        return 0 if missing_after == 0 else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
