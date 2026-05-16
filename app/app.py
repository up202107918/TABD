"""
Flask Web Application for Election Analytics Platform
Advanced Topics in Databases - Practical Assignment

This application provides a web interface to explore Portuguese election data
stored in PostgreSQL/PostGIS database.
"""

from flask import Flask, render_template, request, jsonify
import psycopg2
import psycopg2.extras
import json
from typing import List, Dict, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.config import DB_CONFIG

app = Flask(__name__)
app.config['SECRET_KEY'] = 'election-analytics-secret-key-change-in-production'

def get_db_connection():
    """Create database connection"""
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def execute_query(query: str, params: tuple = None) -> List[Dict]:
    """Execute query and return results as list of dictionaries"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            results = cur.fetchall()
            return [dict(row) for row in results]
    finally:
        conn.close()

@app.route('/')
def index():
    """Homepage with overview"""
    # Get basic statistics
    stats_query = """
        SELECT 
            COUNT(DISTINCT d.district_id) as total_districts,
            COUNT(DISTINCT m.municipality_id) as total_municipalities,
            COUNT(DISTINCT p.party_id) as total_parties,
            (SELECT MAX(turnout_percentage) FROM operational.turnout) as max_turnout,
            (SELECT MIN(turnout_percentage) FROM operational.turnout) as min_turnout,
            (SELECT ROUND(AVG(turnout_percentage), 2) FROM operational.turnout) as avg_turnout
        FROM operational.district d
        CROSS JOIN operational.municipality m
        CROSS JOIN operational.party p
    """
    
    stats = execute_query(stats_query)
    
    return render_template('index.html', stats=stats[0] if stats else {})

@app.route('/districts')
def districts():
    """List all districts"""
    query = """
        SELECT 
            d.district_id,
            d.district_name,
            COUNT(DISTINCT m.municipality_id) as municipalities_count,
            ROUND(AVG(t.turnout_percentage), 2) as avg_turnout
        FROM operational.district d
        LEFT JOIN operational.municipality m ON d.district_id = m.district_id
        LEFT JOIN operational.turnout t ON m.municipality_id = t.municipality_id
            AND t.election_id = (
                SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1
            )
        GROUP BY d.district_id, d.district_name
        HAVING COUNT(DISTINCT m.municipality_id) > 0
        ORDER BY d.district_name
    """
    
    districts_list = execute_query(query)
    
    return render_template('districts.html', districts=districts_list)

@app.route('/district/<int:district_id>')
def district_detail(district_id: int):
    """Detailed view of a specific district"""
    # Get district info
    district_query = """
        SELECT district_id, district_code, district_name
        FROM operational.district
        WHERE district_id = %s
    """
    district = execute_query(district_query, (district_id,))
    
    if not district:
        return "District not found", 404
    
    # Get municipalities in this district
    municipalities_query = """
        SELECT 
            m.municipality_id,
            m.municipality_name,
            t.turnout_percentage,
            t.registered_voters,
            t.votes_cast
        FROM operational.municipality m
        LEFT JOIN operational.turnout t ON m.municipality_id = t.municipality_id
        WHERE m.district_id = %s
            AND (t.election_id = (
                SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1
            ) OR t.election_id IS NULL)
        ORDER BY m.municipality_name
    """
    municipalities = execute_query(municipalities_query, (district_id,))
    
    # Get party performance in district
    party_query = """
        SELECT 
            COALESCE(p.party_acronym, co.coalition_acronym) as party,
            SUM(vr.votes_obtained) as total_votes,
            ROUND(AVG(vr.vote_percentage), 2) as avg_percentage
        FROM operational.candidacy c
        JOIN operational.municipality m ON c.municipality_id = m.municipality_id
        LEFT JOIN operational.party p ON c.party_id = p.party_id
        LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
        JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
        WHERE m.district_id = %s
            AND c.election_id = (
                SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1
            )
            AND c.organ_id = (SELECT organ_id FROM operational.electoral_organ WHERE organ_code = 'CM')
        GROUP BY COALESCE(p.party_acronym, co.coalition_acronym)
        ORDER BY total_votes DESC
        LIMIT 10
    """
    parties = execute_query(party_query, (district_id,))
    
    return render_template('district_detail.html', 
                         district=district[0], 
                         municipalities=municipalities,
                         parties=parties)

@app.route('/municipality/<int:municipality_id>')
def municipality_detail(municipality_id: int):
    """Detailed view of a specific municipality"""
    # Get municipality info
    muni_query = """
        SELECT 
            m.municipality_id,
            m.municipality_name,
            d.district_name,
            t.registered_voters,
            t.votes_cast,
            t.turnout_percentage,
            t.blank_percentage,
            t.null_percentage
        FROM operational.municipality m
        JOIN operational.district d ON m.district_id = d.district_id
        LEFT JOIN operational.turnout t ON m.municipality_id = t.municipality_id
        WHERE m.municipality_id = %s
            AND (t.election_id = (
                SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1
            ) OR t.election_id IS NULL)
            AND (t.organ_id = (SELECT organ_id FROM operational.electoral_organ WHERE organ_code = 'CM') OR t.organ_id IS NULL)
        LIMIT 1
    """
    municipality = execute_query(muni_query, (municipality_id,))
    
    if not municipality:
        return "Municipality not found", 404
    
    # Get election results for this municipality
    results_query = """
        SELECT 
            COALESCE(p.party_acronym, co.coalition_acronym) as party,
            COALESCE(p.party_name, co.coalition_name) as party_full_name,
            eo.organ_name,
            vr.votes_obtained,
            vr.vote_percentage,
            COALESCE(sr.seats_obtained, 0) as seats,
            vr.is_winner,
            vr.ranking_position
        FROM operational.candidacy c
        JOIN operational.electoral_organ eo ON c.organ_id = eo.organ_id
        LEFT JOIN operational.party p ON c.party_id = p.party_id
        LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
        JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
        LEFT JOIN operational.seat_result sr ON c.candidacy_id = sr.candidacy_id
        WHERE c.municipality_id = %s
            AND c.election_id = (
                SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1
            )
            AND eo.organ_code = 'CM'
        ORDER BY vr.votes_obtained DESC
    """
    results = execute_query(results_query, (municipality_id,))
    
    return render_template('municipality_detail.html',
                         municipality=municipality[0],
                         results=results)

@app.route('/api/map/districts')
def api_map_districts():
    """API endpoint: GeoJSON of districts with election data"""
    query = """
        SELECT 
            d.district_id,
            d.district_name,
            d.district_code,
            ST_AsGeoJSON(d.geometry) as geometry,
            ROUND(AVG(t.turnout_percentage), 2) as avg_turnout,
            COUNT(DISTINCT m.municipality_id) as municipalities
        FROM operational.district d
        LEFT JOIN operational.municipality m ON d.district_id = m.district_id
        LEFT JOIN operational.turnout t ON m.municipality_id = t.municipality_id
        WHERE d.geometry IS NOT NULL
            AND (t.election_id = (
                SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1
            ) OR t.election_id IS NULL)
        GROUP BY d.district_id, d.district_name, d.district_code, d.geometry
    """
    
    results = execute_query(query)
    
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
                    'municipalities': row['municipalities']
                },
                'geometry': json.loads(row['geometry'])
            })
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return jsonify(geojson)

@app.route('/api/map/municipalities/<int:district_id>')
def api_map_municipalities(district_id: int):
    """API endpoint: GeoJSON of municipalities in a district"""
    query = """
        SELECT 
            m.municipality_id,
            m.municipality_name,
            m.municipality_code,
            ST_AsGeoJSON(m.geometry) as geometry,
            t.turnout_percentage,
            (
                SELECT COALESCE(p.party_acronym, co.coalition_acronym)
                FROM operational.candidacy c
                LEFT JOIN operational.party p ON c.party_id = p.party_id
                LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
                JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
                WHERE c.municipality_id = m.municipality_id
                    AND vr.is_winner = true
                    AND c.organ_id = (SELECT organ_id FROM operational.electoral_organ WHERE organ_code = 'CM')
                LIMIT 1
            ) as winner
        FROM operational.municipality m
        LEFT JOIN operational.turnout t ON m.municipality_id = t.municipality_id
        WHERE m.district_id = %s
            AND m.geometry IS NOT NULL
            AND (t.election_id = (
                SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1
            ) OR t.election_id IS NULL)
    """
    
    results = execute_query(query, (district_id,))
    
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
                    'winner': row['winner']
                },
                'geometry': json.loads(row['geometry'])
            })
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return jsonify(geojson)

@app.route('/api/charts/party_comparison')
def api_charts_party_comparison():
    """API endpoint: Data for party comparison chart"""
    query = """
        SELECT 
            COALESCE(p.party_acronym, co.coalition_acronym) as party,
            SUM(vr.votes_obtained) as total_votes,
            SUM(COALESCE(sr.seats_obtained, 0)) as total_seats,
            ROUND(AVG(vr.vote_percentage), 2) as avg_percentage
        FROM operational.candidacy c
        LEFT JOIN operational.party p ON c.party_id = p.party_id
        LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
        JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
        LEFT JOIN operational.seat_result sr ON c.candidacy_id = sr.candidacy_id
        WHERE c.election_id = (
            SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1
        )
        AND c.organ_id = (SELECT organ_id FROM operational.electoral_organ WHERE organ_code = 'CM')
        GROUP BY COALESCE(p.party_acronym, co.coalition_acronym)
        HAVING SUM(vr.votes_obtained) > 1000
        ORDER BY total_votes DESC
        LIMIT 10
    """
    
    results = execute_query(query)
    
    return jsonify({
        'parties': [r['party'] for r in results],
        'votes': [int(r['total_votes']) for r in results],
        'seats': [int(r['total_seats']) for r in results],
        'percentages': [float(r['avg_percentage']) if r['avg_percentage'] else 0 for r in results]
    })

@app.route('/analytics')
def analytics():
    """Analytics dashboard with visualizations"""
    return render_template('analytics.html')

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Use port 8000 by default (5000 conflicts with macOS AirPlay Receiver)
    # Can override with: PORT=5000 python app.py
    import os
    port = int(os.environ.get('PORT', 8000))
    print(f"\n🚀 Starting Flask application on port {port}")
    print(f"📍 Open your browser to: http://localhost:{port}\n")
    app.run(debug=True, host='0.0.0.0', port=port)