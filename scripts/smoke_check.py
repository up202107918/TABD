"""
Post-ETL smoke checks (counts + Lisboa seats). Exit 0 if thresholds pass.

Usage (repo root, DB_* set or etl/config.py):
    .venv\\Scripts\\python.exe scripts\\smoke_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))

import psycopg2  # noqa: E402
from config import DB_CONFIG  # noqa: E402

# Approximate minimums after aut_2021 full load (CM, municipality)
THRESHOLDS = {
    "stg_election_results": 1000,
    "stg_turnout_data": 250,
    "municipalities": 250,
    "districts_with_geom": 15,
    "vote_rows_2021": 1000,
    "seat_rows_2021": 400,
    "fact_election_result": 1000,
    "fact_turnout": 250,
}


def main() -> int:
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    failed: list[str] = []
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO operational, staging, warehouse, public")

            checks = [
                ("stg_election_results", "SELECT COUNT(*) FROM staging.stg_election_results"),
                ("stg_turnout_data", "SELECT COUNT(*) FROM staging.stg_turnout_data"),
                ("municipalities", "SELECT COUNT(*) FROM municipality"),
                (
                    "districts_with_geom",
                    "SELECT COUNT(*) FROM district WHERE geometry IS NOT NULL",
                ),
                (
                    "vote_rows_2021",
                    """
                    SELECT COUNT(*) FROM vote_result vr
                    JOIN candidacy c ON c.candidacy_id = vr.candidacy_id
                    JOIN election e ON e.election_id = c.election_id
                    WHERE e.election_year = 2021
                    """,
                ),
                (
                    "seat_rows_2021",
                    """
                    SELECT COUNT(*) FROM seat_result sr
                    JOIN candidacy c ON c.candidacy_id = sr.candidacy_id
                    JOIN election e ON e.election_id = c.election_id
                    WHERE e.election_year = 2021 AND sr.seats_obtained > 0
                    """,
                ),
                (
                    "fact_election_result",
                    "SELECT COUNT(*) FROM warehouse.fact_election_result",
                ),
                ("fact_turnout", "SELECT COUNT(*) FROM warehouse.fact_turnout"),
            ]

            print("Smoke check results:")
            for name, sql in checks:
                cur.execute(sql)
                n = cur.fetchone()[0]
                min_n = THRESHOLDS.get(name, 1)
                ok = n >= min_n
                status = "OK" if ok else "FAIL"
                print(f"  {name}: {n} (min {min_n}) [{status}]")
                if not ok:
                    failed.append(name)

            cur.execute(
                """
                SELECT COALESCE(p.party_acronym, co.coalition_acronym), sr.seats_obtained
                FROM operational.candidacy c
                JOIN operational.seat_result sr ON c.candidacy_id = sr.candidacy_id
                LEFT JOIN operational.party p ON c.party_id = p.party_id
                LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
                JOIN operational.municipality m ON m.municipality_id = c.municipality_id
                JOIN operational.election e ON e.election_id = c.election_id
                WHERE m.municipality_id = (
                    SELECT m2.municipality_id
                    FROM operational.municipality m2
                    JOIN operational.district d ON d.district_id = m2.district_id
                    WHERE m2.municipality_name = 'Lisboa' AND d.district_name = 'Lisboa'
                    LIMIT 1
                )
                  AND e.election_year = 2021
                  AND c.organ_id = (
                      SELECT organ_id FROM operational.electoral_organ WHERE organ_code = 'CM'
                  )
                  AND sr.seats_obtained > 0
                ORDER BY sr.seats_obtained DESC
                """
            )
            lisboa = cur.fetchall()
            lisboa_map = dict(lisboa) if lisboa else {}
            print("  Lisboa 2021 CM seats:", lisboa_map)
            if lisboa_map.get("A", 0) < 7 or lisboa_map.get("B", 0) < 7:
                failed.append("lisboa_seats_sample")
            if sum(lisboa_map.values()) < 15:
                failed.append("lisboa_seats_total")

            cur.execute(
                """
                SELECT run_name, status FROM staging.stg_etl_run_log
                ORDER BY run_id DESC LIMIT 1
                """
            )
            last_run = cur.fetchone()
            print(f"  last_etl_run: {last_run}")
            if not last_run or last_run[1] != "completed":
                failed.append("last_etl_run")
            elif "aut_2021" not in (last_run[0] or ""):
                print("  (note: last completed ETL was not aut_2021 — OK if 2021 already loaded)")
            elif "aut_2021" not in (last_run[0] or "") and "aut_2017" not in (last_run[0] or ""):
                print("  (note: last ETL run is not aut_2021 — re-run if testing 2021 only)")

    finally:
        conn.close()

    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
