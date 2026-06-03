"""
Post-load maintenance: refresh summary tables after operational load.
"""

import logging
from typing import Dict

from config import get_dataset_config


def run_post_load(conn, dataset_key: str) -> Dict[str, int]:
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
            logging.warning('No election row for post_load')
            return {'summary_refreshed': 0}
        election_id = row[0]

        cur.execute(
            'DELETE FROM operational.party_municipality_summary WHERE election_id = %s',
            (election_id,),
        )
        cur.execute(
            """
            INSERT INTO operational.party_municipality_summary (
                election_id, municipality_id, party_id, total_votes, total_seats, organs_won
            )
            SELECT
                c.election_id,
                c.municipality_id,
                c.party_id,
                SUM(vr.votes_obtained),
                SUM(COALESCE(sr.seats_obtained, 0)),
                COUNT(DISTINCT CASE WHEN vr.is_winner THEN c.organ_id END)
            FROM operational.candidacy c
            LEFT JOIN operational.vote_result vr ON vr.candidacy_id = c.candidacy_id
            LEFT JOIN operational.seat_result sr ON sr.candidacy_id = c.candidacy_id
            WHERE c.election_id = %s
              AND c.party_id IS NOT NULL
              AND c.municipality_id IS NOT NULL
            GROUP BY c.election_id, c.municipality_id, c.party_id
            """,
            (election_id,),
        )
        cur.execute(
            'SELECT COUNT(*) FROM operational.party_municipality_summary WHERE election_id = %s',
            (election_id,),
        )
        count = cur.fetchone()[0]

        cur.execute('SELECT calculate_turnout_percentages()')
        turnout_fixed = cur.fetchone()[0]
        logging.info('Turnout percentages ensured: %s rows updated', turnout_fixed)

    conn.commit()
    logging.info('Refreshed party_municipality_summary: %s rows for election_id=%s', count, election_id)
    return {'summary_refreshed': count}
