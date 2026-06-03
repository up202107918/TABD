"""
Export Matplotlib charts (PostgreSQL → PNG) for report and docs/screenshots/.

Usage (from repo root, DB_* or etl/config.py set):

    .venv\\Scripts\\python.exe scripts\\export_charts.py
    .venv\\Scripts\\python.exe scripts\\export_charts.py --election-id 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "etl"))

from charts import (  # noqa: E402
    fetch_election_year,
    fetch_party_comparison_rows,
    render_party_bar_chart,
    write_chart_png,
)
from config import DB_CONFIG  # noqa: E402

OUT_DIR = ROOT / "docs" / "screenshots"


def resolve_default_election_id() -> int:
    import psycopg2

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT election_id FROM operational.election
                ORDER BY election_year DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("No elections in database — run ETL first.")
            return row[0]
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Matplotlib charts to docs/screenshots/")
    parser.add_argument("--election-id", type=int, default=None, help="operational.election_id")
    args = parser.parse_args()

    election_id = args.election_id or resolve_default_election_id()
    year = fetch_election_year(DB_CONFIG, election_id)
    rows = fetch_party_comparison_rows(DB_CONFIG, election_id)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    exports = [
        ("matplotlib_analytics_votes.png", "votes"),
        ("matplotlib_analytics_seats.png", "seats"),
    ]
    for filename, metric in exports:
        png = render_party_bar_chart(rows, metric=metric, election_year=year)
        dest = OUT_DIR / filename
        write_chart_png(str(dest), png)
        print(f"Wrote {dest}")

    print(f"election_id={election_id} year={year} parties={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
