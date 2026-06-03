-- Sample outputs for report/slides (run via scripts/run_sql_demos.py or psql -f).
SET search_path TO operational, warehouse, public;
\pset border 2
\pset format aligned
\timing on

\echo '=== sql/03: calculate_vote_percentage (sample candidacy) ==='
SELECT c.candidacy_id,
       COALESCE(p.party_acronym, co.coalition_acronym) AS party,
       m.municipality_name,
       vr.votes_obtained,
       vr.vote_percentage AS stored_pct,
       calculate_vote_percentage(c.candidacy_id) AS fn_pct
FROM candidacy c
JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
JOIN municipality m ON c.municipality_id = m.municipality_id
LEFT JOIN party p ON c.party_id = p.party_id
LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
WHERE m.municipality_name = 'Lisboa'
  AND c.organ_id = (SELECT organ_id FROM electoral_organ WHERE organ_code = 'CM')
ORDER BY vr.votes_obtained DESC
LIMIT 8;

\echo '=== sql/03: get_party_performance_in_municipality (Lisboa, top party A) ==='
SELECT * FROM get_party_performance_in_municipality(
    (SELECT election_id FROM election WHERE election_year = 2021 LIMIT 1),
    (SELECT municipality_id FROM municipality WHERE municipality_name = 'Lisboa' LIMIT 1),
    'A'
);

\echo '=== sql/03: vw_candidacy_details (Lisboa CM, top parties) ==='
SELECT v.election_year, v.organ_name, v.municipality_name, v.political_entity, v.votes_obtained, v.vote_percentage, v.seats_obtained
FROM vw_candidacy_details v
JOIN candidacy c ON c.candidacy_id = v.candidacy_id
WHERE v.municipality_name = 'Lisboa'
  AND c.organ_id = (SELECT organ_id FROM electoral_organ WHERE organ_code = 'CM')
ORDER BY v.votes_obtained DESC NULLS LAST
LIMIT 10;

\echo '=== sql/03: vw_municipality_summary (Lisboa) ==='
SELECT election_year, municipality_name, district_name, organ_name, total_votes, winner, turnout_percentage
FROM vw_municipality_summary
WHERE municipality_name = 'Lisboa';

\echo '=== sql/03: allocate_seats_dhondt (Lisboa CM, 7 seats) ==='
SELECT party_name, votes, seats_allocated
FROM allocate_seats_dhondt(
    (SELECT election_id FROM election WHERE election_year = 2021 LIMIT 1),
    (SELECT organ_id FROM electoral_organ WHERE organ_code = 'CM'),
    (SELECT municipality_id FROM municipality WHERE municipality_name = 'Lisboa' LIMIT 1),
    7
)
WHERE seats_allocated > 0
ORDER BY seats_allocated DESC, votes DESC;

\echo '=== sql/03: allocate_seats_dhondt (Porto CM, 7 seats) ==='
SELECT party_name, votes, seats_allocated
FROM allocate_seats_dhondt(
    (SELECT election_id FROM election WHERE election_year = 2021 LIMIT 1),
    (SELECT organ_id FROM electoral_organ WHERE organ_code = 'CM'),
    (SELECT municipality_id FROM municipality WHERE municipality_name = 'Porto' LIMIT 1),
    7
)
WHERE seats_allocated > 0
ORDER BY seats_allocated DESC, votes DESC;

\echo '=== sql/04: analytical_query_1 (Lisboa rankings) ==='
SELECT election_year, municipality_name, party, votes_obtained, tied_rank, running_total, pct_of_municipality_votes
FROM analytical_query_1_party_rankings
WHERE municipality_name = 'Lisboa'
ORDER BY tied_rank
LIMIT 12;

\echo '=== sql/04: analytical_query_2 (Lisboa district comparison) ==='
SELECT municipality_name, party, municipality_pct, district_avg_pct, diff_from_district_avg
FROM analytical_query_2_district_comparison
WHERE municipality_name = 'Lisboa'
ORDER BY votes_obtained DESC
LIMIT 10;

\echo '=== sql/04: analytical_query_3 (turnout, top 10 nationally) ==='
SELECT municipality_name, district_name, turnout_percentage, turnout_rank, turnout_quartile
FROM analytical_query_3_turnout_analysis
ORDER BY turnout_percentage DESC
LIMIT 10;

\echo '=== sql/04: analytical_query_4 ROLLUP (Lisboa district slice) ==='
SELECT district_name, municipality_name, party, total_votes, aggregation_level
FROM analytical_query_4_rollup_hierarchical
WHERE district_name = 'Lisboa'
  AND (municipality_name = 'Lisboa' OR municipality_name IS NULL)
  AND (party IS NOT NULL OR aggregation_level LIKE '%TOTAL%')
ORDER BY aggregation_level, total_votes DESC NULLS LAST
LIMIT 15;

\echo '=== sql/04: analytical_query_5 CUBE (sample) ==='
SELECT district_name, party, organ_name, total_votes, cube_dimension
FROM analytical_query_5_cube_multidimensional
WHERE district_name = 'Porto'
  AND party IN ('PS', 'PSD', 'BE')
  AND organ_name ILIKE '%Câmara%'
LIMIT 12;

\echo '=== sql/04: analytical_query_6 advanced aggregates (Lisboa + Porto) ==='
SELECT municipality_name, parties_over_1000_votes, parties_by_votes, top_3_parties, total_votes
FROM analytical_query_6_advanced_aggregates
WHERE municipality_name IN ('Lisboa', 'Porto')
ORDER BY total_votes DESC;

\echo '=== sql/04: analytical_query_8 cross-district (PS top districts) ==='
SELECT district_name, party, total_votes, avg_percentage, district_rank, performance_quartile
FROM analytical_query_8_cross_district_comparison
WHERE party = 'PS'
ORDER BY total_votes DESC
LIMIT 10;

\echo '=== sql/04: demonstrate_dhondt (Lisboa, iteration sample) ==='
SELECT iteration, party, votes, seats_so_far, quotient, gets_seat
FROM demonstrate_dhondt('Lisboa', 2021, 7)
WHERE iteration <= 3 OR gets_seat
ORDER BY iteration, quotient DESC
LIMIT 25;

\echo '=== triggers: audit_log row count ==='
SELECT COUNT(*) AS audit_log_rows FROM audit_log;

\echo '=== warehouse facts row counts ==='
SELECT 'fact_election_result' AS rel, COUNT(*)::bigint AS n FROM warehouse.fact_election_result
UNION ALL
SELECT 'fact_turnout', COUNT(*) FROM warehouse.fact_turnout;
