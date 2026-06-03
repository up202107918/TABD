"""
Flask Web Application for Election Analytics Platform
Advanced Topics in Databases - Practical Assignment
"""

import json
import os
import sys
from typing import Dict, List, Optional

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, render_template, request

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.config import DB_CONFIG

app = Flask(__name__)
app.config['SECRET_KEY'] = 'election-analytics-secret-key-change-in-production'

ORGAN_CM_SUBQUERY = (
    "SELECT organ_id FROM operational.electoral_organ WHERE organ_code = 'CM'"
)


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def execute_query(query: str, params: Optional[tuple] = None) -> List[Dict]:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_elections() -> List[Dict]:
    return execute_query(
        """
        SELECT e.election_id, e.election_year, e.description, et.type_name
        FROM operational.election e
        JOIN operational.election_type et ON et.election_type_id = e.election_type_id
        ORDER BY e.election_year DESC
        """
    )


def resolve_comparison_election_ids(
    elections: Optional[List[Dict]] = None,
) -> Optional[tuple]:
    """
    Return (election_id_a, election_id_b) for cross-election charts.
    Query params: election_id_a / election_id_b, or election_year_a / election_year_b.
    Defaults: two most recent distinct years in the database.
    """
    elections = elections if elections is not None else fetch_elections()
    if len(elections) < 2:
        return None

    by_id = {e['election_id']: e for e in elections}

    def id_from_arg(param_id: str, param_year: str) -> Optional[int]:
        if request.args.get(param_id):
            return int(request.args[param_id])
        if request.args.get(param_year):
            year = int(request.args[param_year])
            for e in elections:
                if e['election_year'] == year:
                    return e['election_id']
        return None

    id_a = id_from_arg('election_id_a', 'election_year_a')
    id_b = id_from_arg('election_id_b', 'election_year_b')

    if id_a is None and id_b is None:
        id_a = elections[-1]['election_id']
        id_b = elections[-2]['election_id']
    elif id_a is None:
        id_a = elections[-1]['election_id'] if id_b != elections[-1]['election_id'] else elections[-2]['election_id']
    elif id_b is None:
        id_b = elections[-2]['election_id'] if id_a != elections[-2]['election_id'] else elections[-1]['election_id']

    if id_a == id_b:
        return None

    if id_a not in by_id or id_b not in by_id:
        return None

    # Always return (older, newer) for consistent chart labels
    ea, eb = by_id[id_a], by_id[id_b]
    if ea['election_year'] <= eb['election_year']:
        return id_a, id_b
    return id_b, id_a


def resolve_election_id(elections: Optional[List[Dict]] = None) -> Optional[int]:
    """Pick election from query string or default to the latest in the database."""
    if request.args.get('election_id'):
        return int(request.args['election_id'])

    if request.args.get('election_year'):
        year = int(request.args['election_year'])
        rows = execute_query(
            'SELECT election_id FROM operational.election WHERE election_year = %s LIMIT 1',
            (year,),
        )
        return rows[0]['election_id'] if rows else None

    elections = elections if elections is not None else fetch_elections()
    return elections[0]['election_id'] if elections else None


def fetch_municipalities_for_select() -> List[Dict]:
    return execute_query(
        """
        SELECT m.municipality_id, m.municipality_name, d.district_name
        FROM operational.municipality m
        JOIN operational.district d ON d.district_id = m.district_id
        ORDER BY d.district_name, m.municipality_name
        """
    )


@app.context_processor
def inject_election_context():
    elections = fetch_elections()
    election_id = resolve_election_id(elections)
    current = next(
        (e for e in elections if e['election_id'] == election_id),
        elections[0] if elections else None,
    )
    return {
        'elections': elections,
        'current_election_id': election_id,
        'current_election': current,
        'municipalities_select': fetch_municipalities_for_select(),
    }


@app.route('/')
def index():
    election_id = resolve_election_id()
    stats = {}
    if election_id:
        rows = execute_query(
            """
            SELECT
                COUNT(DISTINCT d.district_id) AS total_districts,
                COUNT(DISTINCT m.municipality_id) AS total_municipalities,
                (SELECT COUNT(DISTINCT COALESCE(c.party_id, c.coalition_id))
                 FROM operational.candidacy c
                 WHERE c.election_id = %s) AS total_parties,
                (SELECT MAX(t.turnout_percentage) FROM operational.turnout t
                 WHERE t.election_id = %s) AS max_turnout,
                (SELECT MIN(t.turnout_percentage) FROM operational.turnout t
                 WHERE t.election_id = %s AND t.turnout_percentage IS NOT NULL) AS min_turnout,
                (SELECT ROUND(AVG(t.turnout_percentage), 2) FROM operational.turnout t
                 WHERE t.election_id = %s) AS avg_turnout
            FROM operational.district d
            JOIN operational.municipality m ON m.district_id = d.district_id
            LEFT JOIN operational.turnout t ON t.municipality_id = m.municipality_id
                AND t.election_id = %s
            """,
            (election_id, election_id, election_id, election_id, election_id),
        )
        stats = rows[0] if rows else {}

    return render_template('index.html', stats=stats)


@app.route('/districts')
def districts():
    election_id = resolve_election_id()
    districts_list = execute_query(
        """
        SELECT
            d.district_id,
            d.district_name,
            COUNT(DISTINCT m.municipality_id) AS municipalities_count,
            ROUND(AVG(t.turnout_percentage), 2) AS avg_turnout
        FROM operational.district d
        LEFT JOIN operational.municipality m ON d.district_id = m.district_id
        LEFT JOIN operational.turnout t ON m.municipality_id = t.municipality_id
            AND t.election_id = %s
        GROUP BY d.district_id, d.district_name
        HAVING COUNT(DISTINCT m.municipality_id) > 0
        ORDER BY d.district_name
        """,
        (election_id,),
    )
    return render_template('districts.html', districts=districts_list)


@app.route('/district/<int:district_id>')
def district_detail(district_id: int):
    election_id = resolve_election_id()
    district = execute_query(
        'SELECT district_id, district_code, district_name FROM operational.district WHERE district_id = %s',
        (district_id,),
    )
    if not district:
        return 'District not found', 404

    municipalities = execute_query(
        """
        SELECT m.municipality_id, m.municipality_name,
               t.turnout_percentage, t.registered_voters, t.votes_cast
        FROM operational.municipality m
        LEFT JOIN operational.turnout t ON m.municipality_id = t.municipality_id
            AND t.election_id = %s
            AND t.organ_id = ({organ})
        WHERE m.district_id = %s
        ORDER BY m.municipality_name
        """.format(organ=ORGAN_CM_SUBQUERY),
        (election_id, district_id),
    )

    parties = execute_query(
        """
        SELECT COALESCE(p.party_acronym, co.coalition_acronym) AS party,
               SUM(vr.votes_obtained) AS total_votes,
               ROUND(AVG(vr.vote_percentage), 2) AS avg_percentage
        FROM operational.candidacy c
        JOIN operational.municipality m ON c.municipality_id = m.municipality_id
        LEFT JOIN operational.party p ON c.party_id = p.party_id
        LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
        JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
        WHERE m.district_id = %s AND c.election_id = %s
            AND c.organ_id = ({organ})
        GROUP BY COALESCE(p.party_acronym, co.coalition_acronym)
        ORDER BY total_votes DESC
        LIMIT 10
        """.format(organ=ORGAN_CM_SUBQUERY),
        (district_id, election_id),
    )

    return render_template(
        'district_detail.html',
        district=district[0],
        municipalities=municipalities,
        parties=parties,
    )


@app.route('/municipality/<int:municipality_id>')
def municipality_detail(municipality_id: int):
    election_id = resolve_election_id()
    municipality = execute_query(
        """
        SELECT m.municipality_id, m.municipality_name, d.district_name,
               t.registered_voters, t.votes_cast, t.turnout_percentage,
               t.blank_percentage, t.null_percentage
        FROM operational.municipality m
        JOIN operational.district d ON m.district_id = d.district_id
        LEFT JOIN operational.turnout t ON m.municipality_id = t.municipality_id
            AND t.election_id = %s
            AND t.organ_id = ({organ})
        WHERE m.municipality_id = %s
        LIMIT 1
        """.format(organ=ORGAN_CM_SUBQUERY),
        (election_id, municipality_id),
    )
    if not municipality:
        return 'Municipality not found', 404

    results = execute_query(
        """
        SELECT COALESCE(p.party_acronym, co.coalition_acronym) AS party,
               COALESCE(p.party_name, co.coalition_name) AS party_full_name,
               eo.organ_name, vr.votes_obtained, vr.vote_percentage,
               COALESCE(sr.seats_obtained, 0) AS seats,
               vr.is_winner, vr.ranking_position
        FROM operational.candidacy c
        JOIN operational.electoral_organ eo ON c.organ_id = eo.organ_id
        LEFT JOIN operational.party p ON c.party_id = p.party_id
        LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
        JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
        LEFT JOIN operational.seat_result sr ON c.candidacy_id = sr.candidacy_id
        WHERE c.municipality_id = %s AND c.election_id = %s AND eo.organ_code = 'CM'
        ORDER BY vr.votes_obtained DESC
        """,
        (municipality_id, election_id),
    )

    return render_template('municipality_detail.html', municipality=municipality[0], results=results)


@app.route('/api/map/districts')
def api_map_districts():
    election_id = resolve_election_id()
    results = execute_query(
        """
        SELECT d.district_id, d.district_name, d.district_code,
               ST_AsGeoJSON(d.geometry) AS geometry,
               ROUND(AVG(t.turnout_percentage), 2) AS avg_turnout,
               COUNT(DISTINCT m.municipality_id) AS municipalities
        FROM operational.district d
        LEFT JOIN operational.municipality m ON d.district_id = m.district_id
        LEFT JOIN operational.turnout t ON m.municipality_id = t.municipality_id
            AND t.election_id = %s
        WHERE d.geometry IS NOT NULL
        GROUP BY d.district_id, d.district_name, d.district_code, d.geometry
        """,
        (election_id,),
    )

    features = []
    for row in results:
        if row['geometry']:
            features.append({
                'type': 'Feature',
                'id': row['district_id'],
                'properties': {
                    'name': row['district_name'],
                    'code': row['district_code'],
                    'avg_turnout': float(row['avg_turnout']) if row['avg_turnout'] else None,
                    'municipalities': row['municipalities'],
                },
                'geometry': json.loads(row['geometry']),
            })

    return jsonify({'type': 'FeatureCollection', 'features': features})


@app.route('/api/map/municipalities/<int:district_id>')
def api_map_municipalities(district_id: int):
    election_id = resolve_election_id()
    results = execute_query(
        """
        SELECT m.municipality_id, m.municipality_name, m.municipality_code,
               ST_AsGeoJSON(m.geometry) AS geometry,
               t.turnout_percentage,
               (
                   SELECT COALESCE(p.party_acronym, co.coalition_acronym)
                   FROM operational.candidacy c
                   LEFT JOIN operational.party p ON c.party_id = p.party_id
                   LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
                   JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
                   WHERE c.municipality_id = m.municipality_id
                     AND c.election_id = %s
                     AND vr.is_winner = true
                     AND c.organ_id = ({organ})
                   LIMIT 1
               ) AS winner
        FROM operational.municipality m
        LEFT JOIN operational.turnout t ON m.municipality_id = t.municipality_id
            AND t.election_id = %s
        WHERE m.district_id = %s AND m.geometry IS NOT NULL
        """.format(organ=ORGAN_CM_SUBQUERY),
        (election_id, election_id, district_id),
    )

    features = []
    for row in results:
        if row['geometry']:
            features.append({
                'type': 'Feature',
                'id': row['municipality_id'],
                'properties': {
                    'name': row['municipality_name'],
                    'code': row['municipality_code'],
                    'turnout': float(row['turnout_percentage']) if row['turnout_percentage'] else None,
                    'winner': row['winner'],
                },
                'geometry': json.loads(row['geometry']),
            })

    return jsonify({'type': 'FeatureCollection', 'features': features})


def _fetch_national_party_totals(election_id: int, min_votes: int = 500) -> Dict[str, int]:
    rows = execute_query(
        """
        SELECT COALESCE(p.party_acronym, co.coalition_acronym) AS party,
               SUM(vr.votes_obtained) AS total_votes
        FROM operational.candidacy c
        LEFT JOIN operational.party p ON c.party_id = p.party_id
        LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
        JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
        WHERE c.election_id = %s AND c.organ_id = ({organ})
        GROUP BY COALESCE(p.party_acronym, co.coalition_acronym)
        HAVING SUM(vr.votes_obtained) >= %s
        ORDER BY total_votes DESC
        """.format(organ=ORGAN_CM_SUBQUERY),
        (election_id, min_votes),
    )
    return {r['party']: int(r['total_votes']) for r in rows}


def _fetch_avg_turnout(election_id: int) -> Optional[float]:
    rows = execute_query(
        """
        SELECT ROUND(AVG(
            COALESCE(
                t.turnout_percentage,
                100.0 * t.votes_cast::NUMERIC / NULLIF(t.registered_voters, 0)
            )
        ), 2) AS avg_turnout
        FROM operational.turnout t
        WHERE t.election_id = %s
          AND t.organ_id = ({organ})
          AND t.municipality_id IS NOT NULL
          AND t.registered_voters > 0
        """.format(organ=ORGAN_CM_SUBQUERY),
        (election_id,),
    )
    if not rows or rows[0]['avg_turnout'] is None:
        return None
    return float(rows[0]['avg_turnout'])


@app.route('/api/charts/election_comparison')
def api_charts_election_comparison():
    """National CM totals for two local elections (for grouped bar chart)."""
    elections = fetch_elections()
    pair = resolve_comparison_election_ids(elections)
    if not pair:
        return jsonify({
            'error': 'Need at least two elections loaded (e.g. aut_2017 and aut_2021).',
            'elections_available': len(elections),
        }), 400

    id_a, id_b = pair
    meta = {e['election_id']: e for e in elections}
    year_a = int(meta[id_a]['election_year'])
    year_b = int(meta[id_b]['election_year'])
    label_a = str(year_a)
    label_b = str(year_b)

    votes_a = _fetch_national_party_totals(id_a)
    votes_b = _fetch_national_party_totals(id_b)

    ranked = sorted(
        set(votes_a) | set(votes_b),
        key=lambda p: max(votes_a.get(p, 0), votes_b.get(p, 0)),
        reverse=True,
    )[:12]

    total_a = sum(votes_a.values()) or 1
    total_b = sum(votes_b.values()) or 1
    rows = []
    for party in ranked:
        va = votes_a.get(party, 0)
        vb = votes_b.get(party, 0)
        pct_a = round(100.0 * va / total_a, 2)
        pct_b = round(100.0 * vb / total_b, 2)
        rows.append({
            'party': party,
            'votes_a': va,
            'votes_b': vb,
            'pct_a': pct_a,
            'pct_b': pct_b,
            'pct_delta': round(pct_b - pct_a, 2),
        })

    return jsonify({
        'election_id_a': id_a,
        'election_id_b': id_b,
        'label_a': label_a,
        'label_b': label_b,
        'parties': ranked,
        'datasets': [
            {'label': label_a, 'data': [votes_a.get(p, 0) for p in ranked]},
            {'label': label_b, 'data': [votes_b.get(p, 0) for p in ranked]},
        ],
        'percentages': {
            label_a: [round(100.0 * votes_a.get(p, 0) / total_a, 2) for p in ranked],
            label_b: [round(100.0 * votes_b.get(p, 0) / total_b, 2) for p in ranked],
        },
        'rows': rows,
        'turnout': {
            label_a: _fetch_avg_turnout(id_a),
            label_b: _fetch_avg_turnout(id_b),
        },
        'totals': {label_a: total_a, label_b: total_b},
    })


@app.route('/api/charts/party_comparison')
def api_charts_party_comparison():
    election_id = resolve_election_id()
    results = execute_query(
        """
        SELECT COALESCE(p.party_acronym, co.coalition_acronym) AS party,
               SUM(vr.votes_obtained) AS total_votes,
               SUM(COALESCE(sr.seats_obtained, 0)) AS total_seats,
               ROUND(AVG(vr.vote_percentage), 2) AS avg_percentage
        FROM operational.candidacy c
        LEFT JOIN operational.party p ON c.party_id = p.party_id
        LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
        JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
        LEFT JOIN operational.seat_result sr ON c.candidacy_id = sr.candidacy_id
        WHERE c.election_id = %s AND c.organ_id = ({organ})
        GROUP BY COALESCE(p.party_acronym, co.coalition_acronym)
        HAVING SUM(vr.votes_obtained) > 1000
        ORDER BY total_votes DESC
        LIMIT 10
        """.format(organ=ORGAN_CM_SUBQUERY),
        (election_id,),
    )

    return jsonify({
        'parties': [r['party'] for r in results],
        'votes': [int(r['total_votes']) for r in results],
        'seats': [int(r['total_seats']) for r in results],
        'percentages': [float(r['avg_percentage']) if r['avg_percentage'] else 0 for r in results],
    })


@app.route('/analytics')
def analytics():
    elections = fetch_elections()
    compare_pair = resolve_comparison_election_ids(elections)
    compare_a_id = compare_b_id = None
    if compare_pair:
        compare_a_id, compare_b_id = compare_pair
    return render_template(
        'analytics.html',
        compare_election_a_id=compare_a_id,
        compare_election_b_id=compare_b_id,
        can_compare_elections=compare_pair is not None,
    )


@app.errorhandler(404)
def not_found(_e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(_e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f'\nStarting Flask on http://localhost:{port}\n')
    app.run(debug=True, host='0.0.0.0', port=port)
