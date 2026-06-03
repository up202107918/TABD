"""
Populate operational.seat_result from CNE mapa_2 (official M columns) or D'Hondt fallback.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from config import get_dataset_config, get_dataset_dirs

from pipeline.transform_operational import is_coalition
from pipeline.mapa2_seats import (
    find_mapa2_workbook,
    normalize_territory_key,
    parse_mapa2_cm_seats,
    total_seats_per_municipality,
)


def _resolve_election_and_organ(conn, dataset_key: str) -> Tuple[int, int]:
    cfg = get_dataset_config(dataset_key)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.election_id
            FROM operational.election e
            JOIN operational.election_type et ON et.election_type_id = e.election_type_id
            WHERE et.type_code = %s AND e.election_year = %s
            """,
            (cfg['election_type_code'], cfg['election_year']),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f'No election for dataset {dataset_key}')
        election_id = row[0]

        cur.execute(
            "SELECT organ_id FROM operational.electoral_organ WHERE organ_code = 'CM'"
        )
        organ_row = cur.fetchone()
        if not organ_row:
            raise RuntimeError('CM organ not found')
        organ_id = organ_row[0]

    return election_id, organ_id


def _build_municipality_lookup(conn) -> Dict[Tuple[str, str], int]:
    lookup: Dict[Tuple[str, str], int] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.municipality_id, d.district_name, m.municipality_name
            FROM operational.municipality m
            JOIN operational.district d ON d.district_id = m.district_id
            """
        )
        for municipality_id, district_name, municipality_name in cur.fetchall():
            key = (
                normalize_territory_key(district_name),
                normalize_territory_key(municipality_name),
            )
            lookup[key] = municipality_id
    return lookup


def _find_candidacy_id(
    cur,
    election_id: int,
    organ_id: int,
    municipality_id: int,
    party_acronym: str,
) -> Optional[int]:
    if is_coalition(party_acronym):
        cur.execute(
            """
            SELECT c.candidacy_id
            FROM operational.candidacy c
            JOIN operational.coalition co ON co.coalition_id = c.coalition_id
            WHERE c.election_id = %s AND c.organ_id = %s AND c.municipality_id = %s
              AND co.coalition_acronym = %s
            """,
            (election_id, organ_id, municipality_id, party_acronym),
        )
    else:
        cur.execute(
            """
            SELECT c.candidacy_id
            FROM operational.candidacy c
            JOIN operational.party p ON p.party_id = c.party_id
            WHERE c.election_id = %s AND c.organ_id = %s AND c.municipality_id = %s
              AND p.party_acronym = %s
            """,
            (election_id, organ_id, municipality_id, party_acronym),
        )
    row = cur.fetchone()
    return row[0] if row else None


def _load_from_mapa2(
    conn,
    election_id: int,
    organ_id: int,
    mapa2_path: str,
    muni_lookup: Dict[Tuple[str, str], int],
) -> Dict[str, int]:
    records = parse_mapa2_cm_seats(mapa2_path)
    totals = total_seats_per_municipality(records)
    inserted = 0
    skipped_no_muni = 0
    skipped_no_candidacy = 0

    with conn.cursor() as cur:
        for rec in records:
            if rec['seats'] <= 0:
                continue
            key = (
                normalize_territory_key(rec['distrito']),
                normalize_territory_key(rec['concelho']),
            )
            municipality_id = muni_lookup.get(key)
            if not municipality_id:
                skipped_no_muni += 1
                continue

            candidacy_id = _find_candidacy_id(
                cur,
                election_id,
                organ_id,
                municipality_id,
                rec['party_acronym'],
            )
            if not candidacy_id:
                skipped_no_candidacy += 1
                logging.debug(
                    'No candidacy for %s / %s party %s',
                    rec['distrito'],
                    rec['concelho'],
                    rec['party_acronym'],
                )
                continue

            total_seats = totals.get(key, 0)
            cur.execute(
                """
                INSERT INTO operational.seat_result (
                    candidacy_id, seats_obtained, total_seats_available, allocation_method
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (candidacy_id) DO UPDATE SET
                    seats_obtained = EXCLUDED.seats_obtained,
                    total_seats_available = EXCLUDED.total_seats_available,
                    allocation_method = EXCLUDED.allocation_method
                """,
                (candidacy_id, rec['seats'], total_seats, 'CNE mapa_2'),
            )
            inserted += 1

    conn.commit()
    return {
        'seat_rows_inserted': inserted,
        'seat_rows_skipped_muni': skipped_no_muni,
        'seat_rows_skipped_candidacy': skipped_no_candidacy,
        'mapa2_parties_parsed': len(records),
    }


def run_load_seat_results(conn, dataset_key: str) -> Dict[str, Any]:
    """
    Load seat_result for one election from official CNE mapa_2 (M columns).
    Call after operational vote load, before warehouse reload.
    """
    with conn.cursor() as cur:
        cur.execute('SET search_path TO operational, public')
    conn.commit()

    election_id, organ_id = _resolve_election_and_organ(conn, dataset_key)
    muni_lookup = _build_municipality_lookup(conn)

    dataset_dirs = get_dataset_dirs(dataset_key)
    mapa2_path = find_mapa2_workbook(dataset_dirs)

    stats: Dict[str, Any] = {
        'seat_rows_inserted': 0,
        'seat_source': None,
    }

    if not mapa2_path:
        logging.warning('No mapa_2 workbook for %s — seat_result not loaded', dataset_key)
        return stats

    logging.info('Loading seats from %s', mapa2_path)
    stats.update(_load_from_mapa2(conn, election_id, organ_id, str(mapa2_path), muni_lookup))
    stats['seat_source'] = 'mapa_2'

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM operational.seat_result sr
            JOIN operational.candidacy c ON c.candidacy_id = sr.candidacy_id
            WHERE c.election_id = %s
            """,
            (election_id,),
        )
        stats['seat_result_total'] = cur.fetchone()[0]

    logging.info(
        'seat_result for election_id=%s: %s rows (%s)',
        election_id,
        stats['seat_result_total'],
        stats.get('seat_source'),
    )
    return stats
