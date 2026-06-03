"""
One-off: fix election descriptions corrupted by UTF-8 / CP1250 mismatch.
Also resets descriptions from etl/config.py canonical values.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "etl"))

from config import DATASETS, DB_CONFIG  # noqa: E402
from text_utils import repair_utf8_cp1250_mojibake  # noqa: E402

import psycopg2  # noqa: E402


def main() -> int:
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT election_id, election_year, description FROM operational.election"
            )
            for election_id, year, description in cur.fetchall():
                repaired = repair_utf8_cp1250_mojibake(description)
                canonical = None
                for cfg in DATASETS.values():
                    if cfg["election_year"] == year:
                        canonical = cfg["description"]
                        break
                new_desc = canonical or repaired or description
                cur.execute(
                    "UPDATE operational.election SET description = %s WHERE election_id = %s",
                    (new_desc, election_id),
                )
                print(f"election_id={election_id} year={year} -> {new_desc!r}")

            cur.execute(
                "UPDATE operational.election_type SET type_name = %s WHERE type_code = 'AUT'",
                ("Autárquicas",),
            )
        conn.commit()
        print("Done.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
