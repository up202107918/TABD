-- ============================================================================
-- ANALYTICAL SQL QUERIES
-- Advanced Topics in Databases - Practical Assignment
-- ============================================================================
-- Demonstrates: Window Functions, ROLLUP, CUBE, Advanced Aggregates, D'Hondt
-- ============================================================================

SET search_path TO operational, warehouse, public;

DROP VIEW IF EXISTS analytical_query_8_cross_district_comparison CASCADE;
DROP VIEW IF EXISTS analytical_query_6_advanced_aggregates CASCADE;
DROP VIEW IF EXISTS analytical_query_5_cube_multidimensional CASCADE;
DROP VIEW IF EXISTS analytical_query_4_rollup_hierarchical CASCADE;
DROP VIEW IF EXISTS analytical_query_3_turnout_analysis CASCADE;
DROP VIEW IF EXISTS analytical_query_2_district_comparison CASCADE;
DROP VIEW IF EXISTS analytical_query_1_party_rankings CASCADE;

-- ============================================================================
-- WINDOW FUNCTION QUERIES
-- ============================================================================

-- Query 1: Ranking parties by votes with running totals and percentages
-- Uses: ROW_NUMBER(), RANK(), SUM() OVER, PERCENT_RANK()
CREATE OR REPLACE VIEW analytical_query_1_party_rankings AS
SELECT 
    e.election_year,
    eo.organ_code,
    m.municipality_name,
    d.district_name,
    COALESCE(p.party_acronym, co.coalition_acronym) as party,
    vr.votes_obtained,
    
    -- Ranking within municipality (handles ties)
    ROW_NUMBER() OVER (PARTITION BY c.election_id, c.organ_id, c.municipality_id ORDER BY vr.votes_obtained DESC) as row_rank,
    RANK() OVER (PARTITION BY c.election_id, c.organ_id, c.municipality_id ORDER BY vr.votes_obtained DESC) as tied_rank,
    
    -- Running total of votes
    SUM(vr.votes_obtained) OVER (
        PARTITION BY c.election_id, c.organ_id, c.municipality_id 
        ORDER BY vr.votes_obtained DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) as running_total,
    
    -- Percentage of total votes in municipality
    ROUND(
        vr.votes_obtained::NUMERIC / 
        SUM(vr.votes_obtained) OVER (PARTITION BY c.election_id, c.organ_id, c.municipality_id) * 100, 
        2
    ) as pct_of_municipality_votes,
    
    -- Percentile ranking
    ROUND((PERCENT_RANK() OVER (PARTITION BY c.election_id, c.organ_id, c.municipality_id ORDER BY vr.votes_obtained) * 100)::NUMERIC, 2) as percentile_rank
    
FROM candidacy c
JOIN election e ON c.election_id = e.election_id
JOIN electoral_organ eo ON c.organ_id = eo.organ_id
JOIN municipality m ON c.municipality_id = m.municipality_id
JOIN district d ON m.district_id = d.district_id
JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
LEFT JOIN party p ON c.party_id = p.party_id
LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
WHERE e.election_type_id = (SELECT election_type_id FROM election_type WHERE type_code = 'AUT')
ORDER BY m.municipality_name, tied_rank;

COMMENT ON VIEW analytical_query_1_party_rankings IS 
'Window Functions: Party rankings with running totals and percentiles per municipality';

-- Query 2: Compare party performance to district average using window functions
-- Uses: AVG() OVER, LAG(), LEAD()
CREATE OR REPLACE VIEW analytical_query_2_district_comparison AS
SELECT 
    e.election_year,
    eo.organ_code,
    d.district_name,
    m.municipality_name,
    COALESCE(p.party_acronym, co.coalition_acronym) as party,
    vr.votes_obtained,
    vr.vote_percentage as municipality_pct,
    
    -- District average for this party
    ROUND(AVG(vr.vote_percentage) OVER (
        PARTITION BY c.election_id, c.organ_id, d.district_id, COALESCE(p.party_id, -co.coalition_id)
    ), 2) as district_avg_pct,
    
    -- Difference from district average
    ROUND(
        vr.vote_percentage - AVG(vr.vote_percentage) OVER (
            PARTITION BY c.election_id, c.organ_id, d.district_id, COALESCE(p.party_id, -co.coalition_id)
        ), 
        2
    ) as diff_from_district_avg,
    
    -- Previous municipality result for same party (alphabetically)
    LAG(vr.vote_percentage) OVER (
        PARTITION BY c.election_id, c.organ_id, d.district_id, COALESCE(p.party_id, -co.coalition_id)
        ORDER BY m.municipality_name
    ) as prev_municipality_pct,
    
    -- Next municipality result for same party
    LEAD(vr.vote_percentage) OVER (
        PARTITION BY c.election_id, c.organ_id, d.district_id, COALESCE(p.party_id, -co.coalition_id)
        ORDER BY m.municipality_name
    ) as next_municipality_pct

FROM candidacy c
JOIN election e ON c.election_id = e.election_id
JOIN electoral_organ eo ON c.organ_id = eo.organ_id
JOIN municipality m ON c.municipality_id = m.municipality_id
JOIN district d ON m.district_id = d.district_id
JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
LEFT JOIN party p ON c.party_id = p.party_id
LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
WHERE e.election_type_id = (SELECT election_type_id FROM election_type WHERE type_code = 'AUT')
ORDER BY d.district_name, party, m.municipality_name;

COMMENT ON VIEW analytical_query_2_district_comparison IS 
'Window Functions: Compare municipality results to district averages with LAG/LEAD';

-- Query 3: Moving averages and rank densities for turnout analysis
-- Uses: AVG() OVER with frame, DENSE_RANK(), NTILE()
CREATE OR REPLACE VIEW analytical_query_3_turnout_analysis AS
SELECT 
    e.election_year,
    eo.organ_code,
    m.municipality_name,
    d.district_name,
    t.turnout_percentage,
    
    -- Rank by turnout
    DENSE_RANK() OVER (PARTITION BY t.election_id, t.organ_id ORDER BY t.turnout_percentage DESC) as turnout_rank,
    
    -- Divide into quartiles
    NTILE(4) OVER (PARTITION BY t.election_id, t.organ_id ORDER BY t.turnout_percentage) as turnout_quartile,
    
    -- Moving average of turnout (3 municipalities window)
    ROUND(AVG(t.turnout_percentage) OVER (
        PARTITION BY t.election_id, t.organ_id
        ORDER BY t.turnout_percentage
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ), 2) as moving_avg_turnout,
    
    -- Cumulative average
    ROUND(AVG(t.turnout_percentage) OVER (
        PARTITION BY t.election_id, t.organ_id
        ORDER BY m.municipality_name
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) as cumulative_avg_turnout,
    
    t.registered_voters,
    t.votes_cast

FROM turnout t
JOIN election e ON t.election_id = e.election_id
JOIN electoral_organ eo ON t.organ_id = eo.organ_id
JOIN municipality m ON t.municipality_id = m.municipality_id
JOIN district d ON m.district_id = d.district_id
WHERE e.election_type_id = (SELECT election_type_id FROM election_type WHERE type_code = 'AUT')
ORDER BY t.turnout_percentage DESC;

COMMENT ON VIEW analytical_query_3_turnout_analysis IS 
'Window Functions: Turnout analysis with rankings, quartiles, and moving averages';

-- ============================================================================
-- GROUP BY ROLLUP QUERY
-- ============================================================================

-- Query 4: Hierarchical vote totals using ROLLUP (District → Municipality → Party)
CREATE OR REPLACE VIEW analytical_query_4_rollup_hierarchical AS
SELECT 
    e.election_year,
    eo.organ_code,
    d.district_name,
    m.municipality_name,
    COALESCE(p.party_acronym, co.coalition_acronym) as party,
    
    COUNT(DISTINCT c.candidacy_id) as num_candidacies,
    SUM(vr.votes_obtained) as total_votes,
    ROUND(AVG(vr.vote_percentage), 2) as avg_vote_percentage,
    SUM(COALESCE(sr.seats_obtained, 0)) as total_seats,
    
    -- Indicate the grouping level
    CASE 
        WHEN GROUPING(d.district_name) = 1 THEN 'GRAND TOTAL'
        WHEN GROUPING(m.municipality_name) = 1 THEN 'District Subtotal'
        WHEN GROUPING(COALESCE(p.party_acronym, co.coalition_acronym)) = 1 THEN 'Municipality Subtotal'
        ELSE 'Detail'
    END as aggregation_level

FROM candidacy c
JOIN election e ON c.election_id = e.election_id
JOIN electoral_organ eo ON c.organ_id = eo.organ_id
JOIN municipality m ON c.municipality_id = m.municipality_id
JOIN district d ON m.district_id = d.district_id
LEFT JOIN party p ON c.party_id = p.party_id
LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
LEFT JOIN seat_result sr ON c.candidacy_id = sr.candidacy_id
WHERE e.election_type_id = (SELECT election_type_id FROM election_type WHERE type_code = 'AUT')

GROUP BY ROLLUP(e.election_year, eo.organ_code, d.district_name, m.municipality_name, COALESCE(p.party_acronym, co.coalition_acronym))
ORDER BY e.election_year NULLS LAST, eo.organ_code NULLS LAST, d.district_name NULLS LAST, m.municipality_name NULLS LAST, party NULLS LAST;

COMMENT ON VIEW analytical_query_4_rollup_hierarchical IS 
'ROLLUP: Hierarchical aggregation of votes by district → municipality → party';

-- ============================================================================
-- GROUP BY CUBE QUERY
-- ============================================================================

-- Query 5: Multi-dimensional analysis using CUBE (District × Party × Organ)
CREATE OR REPLACE VIEW analytical_query_5_cube_multidimensional AS
SELECT 
    e.election_year,
    d.district_name,
    COALESCE(p.party_acronym, co.coalition_acronym) as party,
    eo.organ_name,
    
    COUNT(DISTINCT c.candidacy_id) as candidacies,
    SUM(vr.votes_obtained) as total_votes,
    SUM(COALESCE(sr.seats_obtained, 0)) as total_seats,
    ROUND(AVG(vr.vote_percentage), 2) as avg_percentage,
    
    -- Identify which dimensions are being aggregated
    CASE 
        WHEN GROUPING(d.district_name) = 1 AND GROUPING(COALESCE(p.party_acronym, co.coalition_acronym)) = 1 AND GROUPING(eo.organ_name) = 1 
            THEN 'ALL DIMENSIONS'
        WHEN GROUPING(d.district_name) = 0 AND GROUPING(COALESCE(p.party_acronym, co.coalition_acronym)) = 1 AND GROUPING(eo.organ_name) = 1 
            THEN 'By District Only'
        WHEN GROUPING(d.district_name) = 1 AND GROUPING(COALESCE(p.party_acronym, co.coalition_acronym)) = 0 AND GROUPING(eo.organ_name) = 1 
            THEN 'By Party Only'
        WHEN GROUPING(d.district_name) = 1 AND GROUPING(COALESCE(p.party_acronym, co.coalition_acronym)) = 1 AND GROUPING(eo.organ_name) = 0 
            THEN 'By Organ Only'
        WHEN GROUPING(d.district_name) = 0 AND GROUPING(COALESCE(p.party_acronym, co.coalition_acronym)) = 0 AND GROUPING(eo.organ_name) = 1 
            THEN 'By District × Party'
        WHEN GROUPING(d.district_name) = 0 AND GROUPING(COALESCE(p.party_acronym, co.coalition_acronym)) = 1 AND GROUPING(eo.organ_name) = 0 
            THEN 'By District × Organ'
        WHEN GROUPING(d.district_name) = 1 AND GROUPING(COALESCE(p.party_acronym, co.coalition_acronym)) = 0 AND GROUPING(eo.organ_name) = 0 
            THEN 'By Party × Organ'
        ELSE 'Detail'
    END as cube_dimension

FROM candidacy c
JOIN election e ON c.election_id = e.election_id
JOIN municipality m ON c.municipality_id = m.municipality_id
JOIN district d ON m.district_id = d.district_id
JOIN electoral_organ eo ON c.organ_id = eo.organ_id
LEFT JOIN party p ON c.party_id = p.party_id
LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
LEFT JOIN seat_result sr ON c.candidacy_id = sr.candidacy_id
WHERE e.election_type_id = (SELECT election_type_id FROM election_type WHERE type_code = 'AUT')

GROUP BY CUBE(e.election_year, d.district_name, COALESCE(p.party_acronym, co.coalition_acronym), eo.organ_name)
ORDER BY cube_dimension, e.election_year NULLS LAST, d.district_name NULLS LAST, party NULLS LAST, eo.organ_name NULLS LAST;

COMMENT ON VIEW analytical_query_5_cube_multidimensional IS 
'CUBE: Multi-dimensional analysis across district, party, and organ';

-- ============================================================================
-- ADVANCED AGGREGATES
-- ============================================================================

-- Query 6: Advanced aggregates - STRING_AGG, ARRAY_AGG, JSON aggregation, FILTER
CREATE OR REPLACE VIEW analytical_query_6_advanced_aggregates AS
SELECT 
    e.election_year,
    eo.organ_code,
    m.municipality_name,
    d.district_name,
    
    -- Count different types of results using FILTER
    COUNT(*) FILTER (WHERE vr.votes_obtained > 1000) as parties_over_1000_votes,
    COUNT(*) FILTER (WHERE vr.is_winner = true) as winning_parties,
    COUNT(*) FILTER (WHERE sr.seats_obtained > 0) as parties_with_seats,
    
    -- String aggregation of all parties
    STRING_AGG(
        COALESCE(p.party_acronym, co.coalition_acronym), 
        ', ' 
        ORDER BY vr.votes_obtained DESC
    ) as parties_by_votes,
    
    -- Array of top 3 parties
    ARRAY_AGG(
        COALESCE(p.party_acronym, co.coalition_acronym) 
        ORDER BY vr.votes_obtained DESC
    ) FILTER (WHERE vr.ranking_position <= 3) as top_3_parties,
    
    -- JSON aggregation of all results
    JSON_AGG(
        JSON_BUILD_OBJECT(
            'party', COALESCE(p.party_acronym, co.coalition_acronym),
            'votes', vr.votes_obtained,
            'percentage', vr.vote_percentage,
            'seats', COALESCE(sr.seats_obtained, 0),
            'is_winner', vr.is_winner
        )
        ORDER BY vr.votes_obtained DESC
    ) as complete_results_json,
    
    -- Aggregate statistics
    SUM(vr.votes_obtained) as total_votes,
    MAX(vr.votes_obtained) as max_votes,
    MIN(vr.votes_obtained) as min_votes,
    ROUND(STDDEV(vr.votes_obtained), 2) as vote_stddev,
    
    -- Turnout info
    MAX(t.turnout_percentage) as turnout_pct

FROM candidacy c
JOIN election e ON c.election_id = e.election_id
JOIN electoral_organ eo ON c.organ_id = eo.organ_id
JOIN municipality m ON c.municipality_id = m.municipality_id
JOIN district d ON m.district_id = d.district_id
LEFT JOIN party p ON c.party_id = p.party_id
LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
LEFT JOIN seat_result sr ON c.candidacy_id = sr.candidacy_id
LEFT JOIN turnout t ON (
    t.election_id = c.election_id AND
    t.organ_id = c.organ_id AND
    t.municipality_id = c.municipality_id
)
WHERE e.election_type_id = (SELECT election_type_id FROM election_type WHERE type_code = 'AUT')

GROUP BY e.election_year, eo.organ_code, m.municipality_name, d.district_name
ORDER BY total_votes DESC;

COMMENT ON VIEW analytical_query_6_advanced_aggregates IS 
'Advanced Aggregates: STRING_AGG, ARRAY_AGG, JSON_AGG, FILTER clause';

-- ============================================================================
-- D'HONDT METHOD IMPLEMENTATION (as analytical query)
-- ============================================================================

-- Query 7: D'Hondt quotients ranked (course ex10.sql pattern — divisors + top-N)
DROP FUNCTION IF EXISTS demonstrate_dhondt(character varying, integer);
DROP FUNCTION IF EXISTS demonstrate_dhondt(character varying, integer, integer);

CREATE OR REPLACE FUNCTION demonstrate_dhondt(
    p_municipality_name VARCHAR,
    p_election_year INTEGER DEFAULT NULL,
    p_total_seats INTEGER DEFAULT 7
) RETURNS TABLE (
    seat_rank INTEGER,
    party VARCHAR,
    votes INTEGER,
    divisor INTEGER,
    quotient NUMERIC,
    gets_seat BOOLEAN
) AS $$
DECLARE
    v_municipality_id INTEGER;
    v_election_id INTEGER;
    v_organ_id INTEGER;
BEGIN
    SELECT m.municipality_id INTO v_municipality_id
    FROM municipality m
    WHERE m.municipality_name = p_municipality_name
    LIMIT 1;

    SELECT election_id INTO v_election_id
    FROM election
    WHERE election_type_id = (SELECT election_type_id FROM election_type WHERE type_code = 'AUT')
        AND (p_election_year IS NULL OR election_year = p_election_year)
    ORDER BY election_year DESC
    LIMIT 1;

    SELECT organ_id INTO v_organ_id
    FROM electoral_organ
    WHERE organ_code = 'CM';

    RETURN QUERY
    WITH party_votes AS (
        SELECT
            COALESCE(p.party_acronym, co.coalition_acronym)::VARCHAR AS party_name,
            vr.votes_obtained AS votes,
            c.candidacy_id
        FROM candidacy c
        JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
        LEFT JOIN party p ON c.party_id = p.party_id
        LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
        WHERE c.election_id = v_election_id
            AND c.organ_id = v_organ_id
            AND c.municipality_id = v_municipality_id
            AND vr.votes_obtained > 0
    ),
    divisors AS (
        SELECT generate_series(1, p_total_seats) AS divisor
    ),
    quotients AS (
        SELECT
            pv.party_name,
            pv.votes,
            d.divisor,
            pv.votes::NUMERIC / d.divisor AS quotient,
            pv.candidacy_id
        FROM party_votes pv
        CROSS JOIN divisors d
    ),
    ranked AS (
        SELECT
            ROW_NUMBER() OVER (ORDER BY q.quotient DESC, q.candidacy_id) AS seat_rank,
            q.party_name,
            q.votes,
            q.divisor,
            ROUND(q.quotient, 2) AS quotient,
            q.candidacy_id
        FROM quotients q
    )
    SELECT
        r.seat_rank::INTEGER,
        r.party_name::VARCHAR,
        r.votes::INTEGER,
        r.divisor::INTEGER,
        r.quotient,
        (r.seat_rank <= p_total_seats) AS gets_seat
    FROM ranked r
    ORDER BY r.seat_rank;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION demonstrate_dhondt IS
'D''Hondt demo: all votes/divisor quotients ranked; top p_total_seats rows win a seat (ex10.sql)';

-- ============================================================================
-- COMPLEX COMPARATIVE QUERIES
-- ============================================================================

-- Query 8: Party performance comparison across districts with rankings
CREATE OR REPLACE VIEW analytical_query_8_cross_district_comparison AS
WITH party_district_summary AS (
    SELECT 
        e.election_year,
        d.district_name,
        COALESCE(p.party_acronym, co.coalition_acronym) as party,
        SUM(vr.votes_obtained) as total_votes,
        ROUND(AVG(vr.vote_percentage), 2) as avg_percentage,
        SUM(COALESCE(sr.seats_obtained, 0)) as total_seats,
        COUNT(DISTINCT CASE WHEN vr.is_winner THEN c.municipality_id END) as municipalities_won
    FROM candidacy c
    JOIN election e ON c.election_id = e.election_id
    JOIN municipality m ON c.municipality_id = m.municipality_id
    JOIN district d ON m.district_id = d.district_id
    LEFT JOIN party p ON c.party_id = p.party_id
    LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
    JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
    LEFT JOIN seat_result sr ON c.candidacy_id = sr.candidacy_id
    WHERE e.election_type_id = (SELECT election_type_id FROM election_type WHERE type_code = 'AUT')
    GROUP BY e.election_year, d.district_name, COALESCE(p.party_acronym, co.coalition_acronym)
)
SELECT 
    election_year,
    district_name,
    party,
    total_votes,
    avg_percentage,
    total_seats,
    municipalities_won,
    
    -- Rank party within district
    RANK() OVER (PARTITION BY election_year, district_name ORDER BY total_votes DESC) as district_rank,
    
    -- Compare to national average for this party
    ROUND(avg_percentage - AVG(avg_percentage) OVER (PARTITION BY election_year, party), 2) as diff_from_national_avg,
    
    -- Quartile within party nationally
    NTILE(4) OVER (PARTITION BY election_year, party ORDER BY avg_percentage) as performance_quartile
    
FROM party_district_summary
ORDER BY election_year, district_name, district_rank;

COMMENT ON VIEW analytical_query_8_cross_district_comparison IS 
'Complex query: Cross-district party comparison with multiple analytics';

-- ============================================================================
-- EXPORT QUERIES TO CSV (for documentation/testing)
-- ============================================================================

-- These queries can be run to export analytical results for verification.