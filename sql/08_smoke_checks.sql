-- Smoke checks after full ETL (assignment §9 reproducibility).
-- Run: psql -U postgres -d election_analytics -f sql/08_smoke_checks.sql
SET search_path TO operational, staging, warehouse, public;
\pset border 2
\timing off

\echo '=== Staging row counts ==='
SELECT 'stg_election_results' AS rel, COUNT(*)::bigint AS n FROM staging.stg_election_results
UNION ALL SELECT 'stg_turnout_data', COUNT(*) FROM staging.stg_turnout_data
UNION ALL SELECT 'stg_etl_run_log (last status)', COUNT(*) FROM staging.stg_etl_run_log WHERE status = 'completed';

\echo '=== Operational (2021, CM) ==='
SELECT COUNT(*)::bigint AS municipalities FROM municipality;
SELECT COUNT(*)::bigint AS districts_with_geom FROM district WHERE geometry IS NOT NULL;
SELECT COUNT(*)::bigint AS municipalities_with_geom FROM municipality WHERE geometry IS NOT NULL;
SELECT COUNT(*)::bigint AS vote_rows_2021
FROM vote_result vr
JOIN candidacy c ON c.candidacy_id = vr.candidacy_id
JOIN election e ON e.election_id = c.election_id
WHERE e.election_year = 2021;
SELECT COUNT(*)::bigint AS seat_rows_2021
FROM seat_result sr
JOIN candidacy c ON c.candidacy_id = sr.candidacy_id
JOIN election e ON e.election_id = c.election_id
WHERE e.election_year = 2021 AND sr.seats_obtained > 0;

\echo '=== Warehouse ==='
SELECT 'fact_election_result' AS rel, COUNT(*)::bigint AS n FROM warehouse.fact_election_result
UNION ALL SELECT 'fact_turnout', COUNT(*) FROM warehouse.fact_turnout;

\echo '=== Last ETL run ==='
SELECT run_id, run_name, status, rows_staged, rows_loaded, end_time
FROM staging.stg_etl_run_log
ORDER BY run_id DESC
LIMIT 1;

\echo '=== Sample: Lisboa 2021 seats (mapa_2) ==='
SELECT COALESCE(p.party_acronym, co.coalition_acronym) AS party, sr.seats_obtained
FROM candidacy c
JOIN seat_result sr ON sr.candidacy_id = c.candidacy_id
LEFT JOIN party p ON p.party_id = c.party_id
LEFT JOIN coalition co ON co.coalition_id = c.coalition_id
JOIN municipality m ON m.municipality_id = c.municipality_id
JOIN election e ON e.election_id = c.election_id
WHERE m.municipality_name = 'Lisboa'
  AND e.election_year = 2021
  AND c.organ_id = (SELECT organ_id FROM electoral_organ WHERE organ_code = 'CM')
  AND sr.seats_obtained > 0
ORDER BY sr.seats_obtained DESC;
