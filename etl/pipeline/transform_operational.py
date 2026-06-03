"""
Load staging tables into the operational schema (MVP: CM / municipality / 2021).
"""

import logging
import re
import unicodedata
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from config import get_dataset_config

# INE-style district codes (keys = title-cased district names)
DISTRICT_CODES = {
    'Aveiro': '01',
    'Beja': '02',
    'Braga': '03',
    'Braganca': '04',
    'Bragança': '04',
    'Castelo Branco': '05',
    'Coimbra': '06',
    'Evora': '07',
    'Évora': '07',
    'Faro': '08',
    'Guarda': '09',
    'Leiria': '10',
    'Lisboa': '11',
    'Portalegre': '12',
    'Porto': '13',
    'Santarem': '14',
    'Santarém': '14',
    'Setubal': '15',
    'Setúbal': '15',
    'Viana Do Castelo': '16',
    'Viana do Castelo': '16',
    'Vila Real': '17',
    'Viseu': '18',
    'Acores': '20',
    'Açores': '20',
    'Madeira': '30',
}


def title_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.title()


def district_code_for(name: str) -> str:
    titled = title_name(name) or name
    if titled in DISTRICT_CODES:
        return DISTRICT_CODES[titled]
    # Fallback: strip accents and retry
    plain = unicodedata.normalize('NFKD', titled).encode('ASCII', 'ignore').decode('utf-8')
    for key, code in DISTRICT_CODES.items():
        key_plain = unicodedata.normalize('NFKD', key).encode('ASCII', 'ignore').decode('utf-8')
        if key_plain.lower() == plain.lower():
            return code
    slug = re.sub(r'[^A-Z0-9]', '', plain.upper())[:2] or '99'
    return slug.zfill(2)


def clear_election_data(conn, election_id: int) -> None:
    """Remove operational rows for one election before reload."""
    tables = [
        ('operational.vote_result', 'candidacy_id IN (SELECT candidacy_id FROM operational.candidacy WHERE election_id = %s)'),
        ('operational.seat_result', 'candidacy_id IN (SELECT candidacy_id FROM operational.candidacy WHERE election_id = %s)'),
        ('operational.candidacy', 'election_id = %s'),
        ('operational.turnout', 'election_id = %s'),
        ('operational.party_municipality_summary', 'election_id = %s'),
        ('operational.coalition_member', 'coalition_id IN (SELECT coalition_id FROM operational.coalition WHERE election_id = %s)'),
        ('operational.coalition', 'election_id = %s'),
    ]
    with conn.cursor() as cur:
        for table, condition in tables:
            cur.execute(f'DELETE FROM {table} WHERE {condition}', (election_id,))
    conn.commit()
    logging.info('Cleared operational data for election_id=%s', election_id)


def ensure_election(conn, cfg: Dict[str, Any]) -> int:
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
        if row:
            election_id = row[0]
        else:
            cur.execute(
                """
                INSERT INTO operational.election (election_type_id, election_date, election_year, description)
                SELECT et.election_type_id, %s::date, %s, %s
                FROM operational.election_type et
                WHERE et.type_code = %s
                RETURNING election_id
                """,
                (
                    cfg['election_date'],
                    cfg['election_year'],
                    cfg['description'],
                    cfg['election_type_code'],
                ),
            )
            election_id = cur.fetchone()[0]
    conn.commit()
    return election_id


def get_organ_id(conn, organ_code: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            'SELECT organ_id FROM operational.electoral_organ WHERE organ_code = %s',
            (organ_code,),
        )
        row = cur.fetchone()
    if not row:
        raise RuntimeError(f'Electoral organ not found: {organ_code}')
    return row[0]


def fetch_territory_pairs(conn) -> List[Tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT distrito, concelho
            FROM (
                SELECT distrito, concelho FROM staging.stg_election_results
                WHERE concelho IS NOT NULL AND UPPER(COALESCE(orgao, '')) = 'CM'
                UNION
                SELECT distrito, concelho FROM staging.stg_turnout_data
                WHERE concelho IS NOT NULL AND UPPER(COALESCE(orgao, '')) = 'CM'
            ) t
            WHERE distrito IS NOT NULL
            ORDER BY distrito, concelho
            """
        )
        return [(row[0], row[1]) for row in cur.fetchall()]


def load_territories(conn) -> Dict[Tuple[str, str], int]:
    """Insert districts and municipalities; return (distrito, concelho) -> municipality_id."""
    pairs = fetch_territory_pairs(conn)
    district_ids: Dict[str, int] = {}
    municipality_ids: Dict[Tuple[str, str], int] = {}
    per_district_counter: Dict[str, int] = defaultdict(int)

    with conn.cursor() as cur:
        districts = sorted({title_name(d) or d for d, _ in pairs})
        for district_name in districts:
            code = district_code_for(district_name)
            cur.execute(
                """
                INSERT INTO operational.district (district_code, district_name)
                VALUES (%s, %s)
                ON CONFLICT (district_code) DO UPDATE SET district_name = EXCLUDED.district_name
                RETURNING district_id
                """,
                (code, district_name),
            )
            district_ids[district_name] = cur.fetchone()[0]

        for distrito_raw, concelho_raw in pairs:
            distrito = title_name(distrito_raw) or distrito_raw
            concelho = title_name(concelho_raw) or concelho_raw
            district_id = district_ids[distrito]
            per_district_counter[distrito] += 1
            muni_code = f"{district_code_for(distrito)}{per_district_counter[distrito]:02d}"
            cur.execute(
                """
                INSERT INTO operational.municipality (municipality_code, municipality_name, district_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (municipality_code) DO UPDATE
                    SET municipality_name = EXCLUDED.municipality_name,
                        district_id = EXCLUDED.district_id
                RETURNING municipality_id
                """,
                (muni_code, concelho, district_id),
            )
            municipality_ids[(distrito_raw, concelho_raw)] = cur.fetchone()[0]

    conn.commit()
    logging.info('Territories loaded: %s districts, %s municipalities', len(district_ids), len(municipality_ids))
    return municipality_ids


def is_coalition(acronym: str) -> bool:
    return '/' in acronym


def get_party_id(conn, acronym: str, cache: Dict[str, int]) -> int:
    if acronym in cache:
        return cache[acronym]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO operational.party (party_acronym, party_name)
            VALUES (%s, %s)
            ON CONFLICT (party_acronym) DO UPDATE SET party_name = EXCLUDED.party_name
            RETURNING party_id
            """,
            (acronym, acronym),
        )
        party_id = cur.fetchone()[0]
    conn.commit()
    cache[acronym] = party_id
    return party_id


def get_coalition_id(conn, acronym: str, election_id: int, cache: Dict[Tuple[str, int], int]) -> int:
    key = (acronym, election_id)
    if key in cache:
        return cache[key]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT coalition_id FROM operational.coalition
            WHERE election_id = %s AND coalition_acronym = %s
            """,
            (election_id, acronym),
        )
        row = cur.fetchone()
        if row:
            coalition_id = row[0]
        else:
            cur.execute(
                """
                INSERT INTO operational.coalition (coalition_acronym, coalition_name, election_id)
                VALUES (%s, %s, %s)
                RETURNING coalition_id
                """,
                (acronym, acronym, election_id),
            )
            coalition_id = cur.fetchone()[0]
    conn.commit()
    cache[key] = coalition_id
    return coalition_id


def load_turnout(conn, election_id: int, organ_id: int, municipality_ids: Dict[Tuple[str, str], int]) -> int:
    count = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT distrito, concelho, eleitores_inscritos, votantes,
                   votos_validos, votos_brancos, votos_nulos
            FROM staging.stg_turnout_data
            WHERE concelho IS NOT NULL AND UPPER(COALESCE(orgao, '')) = 'CM'
            """
        )
        for row in cur.fetchall():
            muni_id = municipality_ids.get((row[0], row[1]))
            if not muni_id:
                continue
            valid = row[4] if row[4] is not None else max(0, (row[2] or 0) - (row[5] or 0) - (row[6] or 0))
            cur.execute(
                """
                INSERT INTO operational.turnout (
                    election_id, organ_id, municipality_id,
                    registered_voters, votes_cast, valid_votes, blank_votes, null_votes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (election_id, organ_id, muni_id, row[2], row[3], valid, row[5] or 0, row[6] or 0),
            )
            count += 1
    conn.commit()
    logging.info('Turnout rows loaded: %s', count)
    return count


def load_results(
    conn,
    election_id: int,
    organ_id: int,
    municipality_ids: Dict[Tuple[str, str], int],
) -> int:
    party_cache: Dict[str, int] = {}
    coalition_cache: Dict[Tuple[str, int], int] = {}
    loaded = 0

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT distrito, concelho, candidatura, votos
            FROM staging.stg_election_results
            WHERE concelho IS NOT NULL
              AND candidatura IS NOT NULL
              AND votos IS NOT NULL
              AND UPPER(COALESCE(orgao, '')) = 'CM'
            """
        )
        for distrito, concelho, candidatura, votos in cur.fetchall():
            muni_id = municipality_ids.get((distrito, concelho))
            if not muni_id:
                continue

            if is_coalition(candidatura):
                coalition_id = get_coalition_id(conn, candidatura, election_id, coalition_cache)
                party_id = None
            else:
                party_id = get_party_id(conn, candidatura, party_cache)
                coalition_id = None

            cur.execute(
                """
                SELECT candidacy_id FROM operational.candidacy
                WHERE election_id = %s AND organ_id = %s AND municipality_id = %s
                  AND COALESCE(party_id, -1) = COALESCE(%s, -1)
                  AND COALESCE(coalition_id, -1) = COALESCE(%s, -1)
                """,
                (election_id, organ_id, muni_id, party_id, coalition_id),
            )
            found = cur.fetchone()
            if found:
                candidacy_id = found[0]
            else:
                cur.execute(
                    """
                    INSERT INTO operational.candidacy (
                        election_id, organ_id, municipality_id, party_id, coalition_id
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING candidacy_id
                    """,
                    (election_id, organ_id, muni_id, party_id, coalition_id),
                )
                candidacy_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO operational.vote_result (candidacy_id, votes_obtained)
                VALUES (%s, %s)
                ON CONFLICT (candidacy_id) DO UPDATE
                    SET votes_obtained = EXCLUDED.votes_obtained
                """,
                (candidacy_id, votos),
            )
            loaded += 1

    conn.commit()
    logging.info('Vote results loaded: %s', loaded)
    return loaded


def update_rankings(conn, election_id: int, organ_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH ranked AS (
                SELECT vr.vote_result_id,
                       RANK() OVER (
                           PARTITION BY c.municipality_id
                           ORDER BY vr.votes_obtained DESC
                       ) AS rnk
                FROM operational.vote_result vr
                JOIN operational.candidacy c ON c.candidacy_id = vr.candidacy_id
                WHERE c.election_id = %s AND c.organ_id = %s
            )
            UPDATE operational.vote_result vr
            SET ranking_position = ranked.rnk,
                is_winner = (ranked.rnk = 1)
            FROM ranked
            WHERE vr.vote_result_id = ranked.vote_result_id
            """,
            (election_id, organ_id),
        )
        cur.execute(
            """
            UPDATE operational.vote_result vr
            SET vote_percentage = LEAST(
                ROUND((vr.votes_obtained::numeric / NULLIF(t.valid_votes, 0)) * 100, 2),
                100
            )
            FROM operational.candidacy c
            JOIN operational.turnout t ON (
                t.election_id = c.election_id
                AND t.organ_id = c.organ_id
                AND t.municipality_id = c.municipality_id
            )
            WHERE vr.candidacy_id = c.candidacy_id
              AND c.election_id = %s
              AND c.organ_id = %s
              AND t.valid_votes > 0
            """,
            (election_id, organ_id),
        )
    conn.commit()
    logging.info('Rankings and vote percentages updated')


def run_transform_operational(conn, dataset_key: str) -> Dict[str, int]:
    cfg = get_dataset_config(dataset_key)
    organ_code = cfg.get('primary_organ', 'CM')
    organ_id = get_organ_id(conn, organ_code)

    with conn.cursor() as cur:
        cur.execute('SET session_replication_role = replica')

    election_id = ensure_election(conn, cfg)
    clear_election_data(conn, election_id)

    municipality_ids = load_territories(conn)
    turnout_count = load_turnout(conn, election_id, organ_id, municipality_ids)
    results_count = load_results(conn, election_id, organ_id, municipality_ids)
    update_rankings(conn, election_id, organ_id)

    with conn.cursor() as cur:
        cur.execute('SET session_replication_role = DEFAULT')
    conn.commit()

    total = turnout_count + results_count
    return {
        'transformed': total,
        'loaded': total,
        'election_id': election_id,
    }
