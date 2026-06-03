"""
Populate warehouse star schema from operational tables for one election year.
"""

import logging
from typing import Any, Dict

from config import get_dataset_config


def clear_warehouse(conn) -> None:
    tables = [
        'warehouse.fact_election_result',
        'warehouse.fact_turnout',
        'warehouse.agg_municipality_party_results',
        'warehouse.agg_district_results',
        'warehouse.bridge_coalition_party',
        'warehouse.dim_party',
        'warehouse.dim_parish',
        'warehouse.dim_municipality',
        'warehouse.dim_district',
        'warehouse.dim_organ',
        'warehouse.dim_election',
    ]
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f'TRUNCATE {table} RESTART IDENTITY CASCADE')
    conn.commit()


def run_load_warehouse(conn, dataset_key: str) -> Dict[str, Any]:
    cfg = get_dataset_config(dataset_key)
    year = cfg['election_year']

    clear_warehouse(conn)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO warehouse.dim_election (
                election_id, election_type_code, election_type_name,
                election_date, election_year, election_description
            )
            SELECT e.election_id, et.type_code, et.type_name,
                   e.election_date, e.election_year, e.description
            FROM operational.election e
            JOIN operational.election_type et ON et.election_type_id = e.election_type_id
            WHERE e.election_year = %s
            """,
            (year,),
        )

        cur.execute(
            """
            INSERT INTO warehouse.dim_organ (
                organ_id, organ_code, organ_name, organ_description, territorial_level
            )
            SELECT organ_id, organ_code, organ_name, description, territorial_level
            FROM operational.electoral_organ
            """
        )

        cur.execute(
            """
            INSERT INTO warehouse.dim_district (
                district_id, district_code, district_name, has_geometry
            )
            SELECT district_id, district_code, district_name, (geometry IS NOT NULL)
            FROM operational.district
            """
        )

        cur.execute(
            """
            INSERT INTO warehouse.dim_municipality (
                municipality_id, municipality_code, municipality_name,
                district_key, district_name, has_geometry
            )
            SELECT m.municipality_id, m.municipality_code, m.municipality_name,
                   dd.district_key, d.district_name, (m.geometry IS NOT NULL)
            FROM operational.municipality m
            JOIN operational.district d ON d.district_id = m.district_id
            JOIN warehouse.dim_district dd ON dd.district_id = d.district_id
            """
        )

        cur.execute(
            """
            INSERT INTO warehouse.dim_party (
                party_id, party_acronym, party_name, is_coalition
            )
            SELECT party_id, party_acronym, party_name, false
            FROM operational.party
            """
        )

        cur.execute(
            """
            INSERT INTO warehouse.dim_party (
                party_acronym, party_name, is_coalition, coalition_id
            )
            SELECT coalition_acronym, coalition_name, true, coalition_id
            FROM operational.coalition co
            JOIN operational.election e ON e.election_id = co.election_id
            WHERE e.election_year = %s
            """,
            (year,),
        )

        cur.execute(
            """
            INSERT INTO warehouse.fact_election_result (
                time_key, election_key, organ_key, municipality_key, party_key,
                votes_obtained, vote_percentage, seats_obtained,
                is_winner, ranking_position, candidacy_id
            )
            SELECT
                TO_CHAR(e.election_date, 'YYYYMMDD')::INTEGER,
                de.election_key,
                dorg.organ_key,
                dm.municipality_key,
                dp.party_key,
                vr.votes_obtained,
                vr.vote_percentage,
                COALESCE(sr.seats_obtained, 0),
                COALESCE(vr.is_winner, false),
                vr.ranking_position,
                c.candidacy_id
            FROM operational.candidacy c
            JOIN operational.election e ON e.election_id = c.election_id
            JOIN operational.electoral_organ eo ON eo.organ_id = c.organ_id
            JOIN operational.vote_result vr ON vr.candidacy_id = c.candidacy_id
            LEFT JOIN operational.seat_result sr ON sr.candidacy_id = c.candidacy_id
            LEFT JOIN operational.party p ON p.party_id = c.party_id
            LEFT JOIN operational.coalition co ON co.coalition_id = c.coalition_id
            JOIN warehouse.dim_election de ON de.election_id = e.election_id
            JOIN warehouse.dim_organ dorg ON dorg.organ_id = eo.organ_id
            JOIN warehouse.dim_municipality dm ON dm.municipality_id = c.municipality_id
            JOIN warehouse.dim_party dp ON (
                (c.party_id IS NOT NULL AND dp.party_id = c.party_id)
                OR (c.coalition_id IS NOT NULL AND dp.coalition_id = c.coalition_id)
            )
            WHERE e.election_year = %s AND c.municipality_id IS NOT NULL
            """,
            (year,),
        )

        cur.execute(
            """
            INSERT INTO warehouse.fact_turnout (
                time_key, election_key, organ_key, municipality_key,
                registered_voters, votes_cast, valid_votes, blank_votes, null_votes,
                abstentions, turnout_percentage, abstention_percentage,
                blank_percentage, null_percentage
            )
            SELECT
                TO_CHAR(e.election_date, 'YYYYMMDD')::INTEGER,
                de.election_key,
                dorg.organ_key,
                dm.municipality_key,
                t.registered_voters,
                t.votes_cast,
                t.valid_votes,
                t.blank_votes,
                t.null_votes,
                t.registered_voters - t.votes_cast,
                t.turnout_percentage,
                t.abstention_percentage,
                t.blank_percentage,
                t.null_percentage
            FROM operational.turnout t
            JOIN operational.election e ON e.election_id = t.election_id
            JOIN warehouse.dim_election de ON de.election_id = e.election_id
            JOIN warehouse.dim_organ dorg ON dorg.organ_id = t.organ_id
            JOIN warehouse.dim_municipality dm ON dm.municipality_id = t.municipality_id
            WHERE e.election_year = %s AND t.municipality_id IS NOT NULL
            """,
            (year,),
        )

        cur.execute('SELECT COUNT(*) FROM warehouse.fact_election_result')
        facts = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM warehouse.fact_turnout')
        turnout_facts = cur.fetchone()[0]

    conn.commit()
    logging.info('Warehouse loaded: %s fact results, %s fact turnout rows', facts, turnout_facts)
    return {'warehouse_facts': facts, 'warehouse_turnout': turnout_facts}
