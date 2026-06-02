-- ============================================================================
-- POST-LOAD VALIDATION QUERIES - Election Analytics Platform
-- ============================================================================
-- This script validates and samples the data imported by the ETL pipeline.
-- Run this AFTER loading schemas (01-05) and executing the Excel-based ETL.
-- ============================================================================

SET search_path TO operational, public;

-- ============================================================================
-- ETL LOAD STATUS
-- ============================================================================

SELECT
    e.election_year,
    e.election_date,
    e.description,
    COUNT(DISTINCT c.candidacy_id) AS candidacies_loaded,
    COUNT(DISTINCT vr.candidacy_id) AS vote_results_loaded,
    COUNT(DISTINCT t.turnout_id) AS turnout_rows_loaded
FROM election e
LEFT JOIN candidacy c ON c.election_id = e.election_id
LEFT JOIN vote_result vr ON vr.candidacy_id = c.candidacy_id
LEFT JOIN turnout t ON t.election_id = e.election_id
GROUP BY e.election_year, e.election_date, e.description
ORDER BY e.election_year DESC;

DO $$
DECLARE
    v_election_count INTEGER;
    v_candidacy_count INTEGER;
    v_vote_result_count INTEGER;
    v_turnout_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_election_count FROM election;
    SELECT COUNT(*) INTO v_candidacy_count FROM candidacy;
    SELECT COUNT(*) INTO v_vote_result_count FROM vote_result;
    SELECT COUNT(*) INTO v_turnout_count FROM turnout;

    IF v_election_count = 0 THEN
        RAISE NOTICE 'No elections are available yet. 01_operational_schema.sql only creates schema objects; load elections/results via ETL first.';
    ELSIF v_candidacy_count = 0 OR v_vote_result_count = 0 THEN
        RAISE NOTICE 'No operational election results found. Run the Excel-based ETL before using this script.';
    ELSE
        RAISE NOTICE 'Operational data detected: % elections, % candidacies, % vote results, % turnout rows.',
            v_election_count, v_candidacy_count, v_vote_result_count, v_turnout_count;
    END IF;
END $$;

-- ============================================================================
-- TABLE COUNTS
-- ============================================================================

SELECT 
    'Parties' as table_name,
    COUNT(*) as row_count
FROM party
UNION ALL
SELECT 'Districts', COUNT(*) FROM district
UNION ALL
SELECT 'Municipalities', COUNT(*) FROM municipality
UNION ALL
SELECT 'Candidacies', COUNT(*) FROM candidacy
UNION ALL
SELECT 'Vote Results', COUNT(*) FROM vote_result
UNION ALL
SELECT 'Seat Results', COUNT(*) FROM seat_result
UNION ALL
SELECT 'Turnout Records', COUNT(*) FROM turnout;

-- ============================================================================
-- SAMPLE RESULTS FROM IMPORTED DATA
-- ============================================================================

SELECT 
    e.election_year,
    eo.organ_code,
    d.district_name,
    m.municipality_name,
    COALESCE(p.party_acronym, co.coalition_acronym, 'IND') as party,
    c.candidate_name,
    vr.votes_obtained,
    vr.vote_percentage,
    sr.seats_obtained
FROM candidacy c
JOIN election e ON c.election_id = e.election_id
JOIN electoral_organ eo ON c.organ_id = eo.organ_id
JOIN municipality m ON c.municipality_id = m.municipality_id
JOIN district d ON m.district_id = d.district_id
LEFT JOIN party p ON c.party_id = p.party_id
LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
LEFT JOIN seat_result sr ON c.candidacy_id = sr.candidacy_id
ORDER BY e.election_year DESC, m.municipality_name, vr.votes_obtained DESC
LIMIT 25;

-- ============================================================================
-- SAMPLE TURNOUT SNAPSHOT
-- ============================================================================

SELECT
    e.election_year,
    eo.organ_code,
    d.district_name,
    m.municipality_name,
    t.registered_voters,
    t.votes_cast,
    t.valid_votes,
    t.blank_votes,
    t.null_votes,
    t.turnout_percentage
FROM turnout t
JOIN election e ON t.election_id = e.election_id
JOIN electoral_organ eo ON t.organ_id = eo.organ_id
LEFT JOIN district d ON t.district_id = d.district_id
LEFT JOIN municipality m ON t.municipality_id = m.municipality_id
ORDER BY e.election_year DESC, t.votes_cast DESC
LIMIT 25;
