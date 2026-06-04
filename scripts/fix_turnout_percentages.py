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
            cur.execute("SELECT COUNT(*) FROM operational.turnout")
            total_turnout = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*) FROM operational.turnout
                WHERE registered_voters > 0 AND COALESCE(votes_cast, 0) > 0
                """
            )
            with_votes = cur.fetchone()[0]
            cur.execute(
                """
                CREATE OR REPLACE FUNCTION calculate_turnout_percentages()
                RETURNS INTEGER AS $$
                DECLARE
                    v_count INTEGER := 0;
                BEGIN
                    UPDATE operational.turnout
                    SET
                        turnout_percentage = CASE
                            WHEN registered_voters > 0 AND COALESCE(votes_cast, 0) > 0
                            THEN ROUND((votes_cast::NUMERIC / registered_voters) * 100, 2)
                            ELSE NULL
                        END,
                        abstention_percentage = CASE
                            WHEN registered_voters > 0 AND COALESCE(votes_cast, 0) > 0
                            THEN ROUND(
                                ((registered_voters - votes_cast)::NUMERIC / registered_voters) * 100, 2
                            )
                            ELSE NULL
                        END,
                        blank_percentage = CASE
                            WHEN votes_cast > 0
                            THEN ROUND((blank_votes::NUMERIC / votes_cast) * 100, 2)
                            ELSE NULL
                        END,
                        null_percentage = CASE
                            WHEN votes_cast > 0
                            THEN ROUND((null_votes::NUMERIC / votes_cast) * 100, 2)
                            ELSE NULL
                        END
                    WHERE registered_voters > 0
                      AND COALESCE(votes_cast, 0) > 0
                      AND (
                        turnout_percentage IS NULL
                        OR turnout_percentage = 0
                        OR abstention_percentage IS NULL
                        OR blank_percentage IS NULL
                        OR null_percentage IS NULL
                      );
                    GET DIAGNOSTICS v_count = ROW_COUNT;
                    RETURN v_count;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
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
        print(f"Turnout rows total: {total_turnout} (with votes_cast>0: {with_votes})")
        print(f"Rows missing % before: {missing_before}")
        print(f"calculate_turnout_percentages() updated: {updated}")
        print(f"Rows still missing % after: {missing_after}")
        if with_votes == 0:
            print(
                "No turnout facts in DB — run ETL first, e.g.\n"
                "  cd etl && ..\\.venv\\Scripts\\python.exe run_etl.py --dataset aut_2021 --mode full"
            )
            return 1
        return 0 if missing_after == 0 else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
