-- ============================================================================
-- SAMPLE DATA FOR TESTING - Election Analytics Platform
-- ============================================================================
-- This script loads minimal sample data to test the application
-- Run this AFTER loading all schemas (01-05)
-- ============================================================================

SET search_path TO operational, public;

-- ============================================================================
-- SAMPLE DATA: Basic Election Results for Testing
-- ============================================================================

-- Verify election exists (should have been created by schema)
-- If not, this will show you what's there
SELECT * FROM election;

-- Get the election_id for 2021
DO $$
DECLARE
    v_election_id INTEGER;
    v_cm_organ_id INTEGER;
    v_am_organ_id INTEGER;
    v_porto_district_id INTEGER;
    v_lisboa_district_id INTEGER;
    v_porto_muni_id INTEGER;
    v_lisboa_muni_id INTEGER;
    v_ps_id INTEGER;
    v_psd_id INTEGER;
    v_be_id INTEGER;
    v_cdu_id INTEGER;
    v_cds_id INTEGER;
BEGIN
    -- Get IDs
    SELECT election_id INTO v_election_id FROM election WHERE election_year = 2021 LIMIT 1;
    SELECT organ_id INTO v_cm_organ_id FROM electoral_organ WHERE organ_code = 'CM';
    SELECT organ_id INTO v_am_organ_id FROM electoral_organ WHERE organ_code = 'AM';
    
    -- Insert sample districts if not exist
    INSERT INTO district (district_code, district_name) VALUES ('13', 'Porto')
        ON CONFLICT (district_code) DO NOTHING;
    INSERT INTO district (district_code, district_name) VALUES ('11', 'Lisboa')
        ON CONFLICT (district_code) DO NOTHING;
    
    SELECT district_id INTO v_porto_district_id FROM district WHERE district_code = '13';
    SELECT district_id INTO v_lisboa_district_id FROM district WHERE district_code = '11';
    
    -- Insert sample municipalities
    INSERT INTO municipality (municipality_code, municipality_name, district_id)
        VALUES ('1302', 'Porto', v_porto_district_id)
        ON CONFLICT (municipality_code) DO NOTHING;
    INSERT INTO municipality (municipality_code, municipality_name, district_id)
        VALUES ('1106', 'Lisboa', v_lisboa_district_id)
        ON CONFLICT (municipality_code) DO NOTHING;
    
    SELECT municipality_id INTO v_porto_muni_id FROM municipality WHERE municipality_code = '1302';
    SELECT municipality_id INTO v_lisboa_muni_id FROM municipality WHERE municipality_code = '1106';
    
    -- Insert sample parties
    INSERT INTO party (party_acronym, party_name) VALUES ('PS', 'Partido Socialista')
        ON CONFLICT (party_acronym) DO NOTHING;
    INSERT INTO party (party_acronym, party_name) VALUES ('PSD', 'Partido Social Democrata')
        ON CONFLICT (party_acronym) DO NOTHING;
    INSERT INTO party (party_acronym, party_name) VALUES ('BE', 'Bloco de Esquerda')
        ON CONFLICT (party_acronym) DO NOTHING;
    INSERT INTO party (party_acronym, party_name) VALUES ('CDU', 'Coligação Democrática Unitária')
        ON CONFLICT (party_acronym) DO NOTHING;
    INSERT INTO party (party_acronym, party_name) VALUES ('CDS-PP', 'CDS - Partido Popular')
        ON CONFLICT (party_acronym) DO NOTHING;
    INSERT INTO party (party_acronym, party_name) VALUES ('PAN', 'Pessoas-Animais-Natureza')
        ON CONFLICT (party_acronym) DO NOTHING;
    INSERT INTO party (party_acronym, party_name) VALUES ('CH', 'Chega')
        ON CONFLICT (party_acronym) DO NOTHING;
    INSERT INTO party (party_acronym, party_name) VALUES ('IL', 'Iniciativa Liberal')
        ON CONFLICT (party_acronym) DO NOTHING;
    
    SELECT party_id INTO v_ps_id FROM party WHERE party_acronym = 'PS';
    SELECT party_id INTO v_psd_id FROM party WHERE party_acronym = 'PSD';
    SELECT party_id INTO v_be_id FROM party WHERE party_acronym = 'BE';
    SELECT party_id INTO v_cdu_id FROM party WHERE party_acronym = 'CDU';
    SELECT party_id INTO v_cds_id FROM party WHERE party_acronym = 'CDS-PP';
    
    -- Insert turnout data for Porto
    INSERT INTO turnout (
        election_id, organ_id, municipality_id,
        registered_voters, votes_cast, valid_votes, blank_votes, null_votes
    ) VALUES (
        v_election_id, v_cm_organ_id, v_porto_muni_id,
        190000, 95000, 92000, 2000, 1000
    ) ON CONFLICT DO NOTHING;
    
    -- Insert turnout data for Lisboa
    INSERT INTO turnout (
        election_id, organ_id, municipality_id,
        registered_voters, votes_cast, valid_votes, blank_votes, null_votes
    ) VALUES (
        v_election_id, v_cm_organ_id, v_lisboa_muni_id,
        420000, 210000, 205000, 3500, 1500
    ) ON CONFLICT DO NOTHING;
    
    -- Insert candidacies and results for PORTO
    
    -- PS in Porto
    INSERT INTO candidacy (election_id, organ_id, municipality_id, party_id, candidate_name)
        VALUES (v_election_id, v_cm_organ_id, v_porto_muni_id, v_ps_id, 'Rui Moreira')
        ON CONFLICT DO NOTHING;
    INSERT INTO vote_result (candidacy_id, votes_obtained, is_winner, ranking_position)
        SELECT candidacy_id, 35000, true, 1
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_porto_muni_id AND party_id = v_ps_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    INSERT INTO seat_result (candidacy_id, seats_obtained, total_seats_available)
        SELECT candidacy_id, 5, 13
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_porto_muni_id AND party_id = v_ps_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    
    -- PSD in Porto
    INSERT INTO candidacy (election_id, organ_id, municipality_id, party_id, candidate_name)
        VALUES (v_election_id, v_cm_organ_id, v_porto_muni_id, v_psd_id, 'Vladimiro Feliz')
        ON CONFLICT DO NOTHING;
    INSERT INTO vote_result (candidacy_id, votes_obtained, is_winner, ranking_position)
        SELECT candidacy_id, 28000, false, 2
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_porto_muni_id AND party_id = v_psd_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    INSERT INTO seat_result (candidacy_id, seats_obtained, total_seats_available)
        SELECT candidacy_id, 4, 13
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_porto_muni_id AND party_id = v_psd_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    
    -- BE in Porto
    INSERT INTO candidacy (election_id, organ_id, municipality_id, party_id)
        VALUES (v_election_id, v_cm_organ_id, v_porto_muni_id, v_be_id)
        ON CONFLICT DO NOTHING;
    INSERT INTO vote_result (candidacy_id, votes_obtained, is_winner, ranking_position)
        SELECT candidacy_id, 12000, false, 3
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_porto_muni_id AND party_id = v_be_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    INSERT INTO seat_result (candidacy_id, seats_obtained, total_seats_available)
        SELECT candidacy_id, 2, 13
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_porto_muni_id AND party_id = v_be_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    
    -- CDU in Porto
    INSERT INTO candidacy (election_id, organ_id, municipality_id, party_id)
        VALUES (v_election_id, v_cm_organ_id, v_porto_muni_id, v_cdu_id)
        ON CONFLICT DO NOTHING;
    INSERT INTO vote_result (candidacy_id, votes_obtained, is_winner, ranking_position)
        SELECT candidacy_id, 8500, false, 4
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_porto_muni_id AND party_id = v_cdu_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    INSERT INTO seat_result (candidacy_id, seats_obtained, total_seats_available)
        SELECT candidacy_id, 1, 13
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_porto_muni_id AND party_id = v_cdu_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    
    -- CDS-PP in Porto
    INSERT INTO candidacy (election_id, organ_id, municipality_id, party_id)
        VALUES (v_election_id, v_cm_organ_id, v_porto_muni_id, v_cds_id)
        ON CONFLICT DO NOTHING;
    INSERT INTO vote_result (candidacy_id, votes_obtained, is_winner, ranking_position)
        SELECT candidacy_id, 8500, false, 5
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_porto_muni_id AND party_id = v_cds_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    INSERT INTO seat_result (candidacy_id, seats_obtained, total_seats_available)
        SELECT candidacy_id, 1, 13
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_porto_muni_id AND party_id = v_cds_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    
    -- Insert candidacies and results for LISBOA
    
    -- PS in Lisboa
    INSERT INTO candidacy (election_id, organ_id, municipality_id, party_id, candidate_name)
        VALUES (v_election_id, v_cm_organ_id, v_lisboa_muni_id, v_ps_id, 'Carlos Moedas')
        ON CONFLICT DO NOTHING;
    INSERT INTO vote_result (candidacy_id, votes_obtained, is_winner, ranking_position)
        SELECT candidacy_id, 75000, true, 1
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_lisboa_muni_id AND party_id = v_ps_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    INSERT INTO seat_result (candidacy_id, seats_obtained, total_seats_available)
        SELECT candidacy_id, 8, 17
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_lisboa_muni_id AND party_id = v_ps_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    
    -- PSD in Lisboa
    INSERT INTO candidacy (election_id, organ_id, municipality_id, party_id)
        VALUES (v_election_id, v_cm_organ_id, v_lisboa_muni_id, v_psd_id)
        ON CONFLICT DO NOTHING;
    INSERT INTO vote_result (candidacy_id, votes_obtained, is_winner, ranking_position)
        SELECT candidacy_id, 65000, false, 2
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_lisboa_muni_id AND party_id = v_psd_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    INSERT INTO seat_result (candidacy_id, seats_obtained, total_seats_available)
        SELECT candidacy_id, 6, 17
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_lisboa_muni_id AND party_id = v_psd_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    
    -- BE in Lisboa
    INSERT INTO candidacy (election_id, organ_id, municipality_id, party_id)
        VALUES (v_election_id, v_cm_organ_id, v_lisboa_muni_id, v_be_id)
        ON CONFLICT DO NOTHING;
    INSERT INTO vote_result (candidacy_id, votes_obtained, is_winner, ranking_position)
        SELECT candidacy_id, 25000, false, 3
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_lisboa_muni_id AND party_id = v_be_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    INSERT INTO seat_result (candidacy_id, seats_obtained, total_seats_available)
        SELECT candidacy_id, 2, 17
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_lisboa_muni_id AND party_id = v_be_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    
    -- CDU in Lisboa
    INSERT INTO candidacy (election_id, organ_id, municipality_id, party_id)
        VALUES (v_election_id, v_cm_organ_id, v_lisboa_muni_id, v_cdu_id)
        ON CONFLICT DO NOTHING;
    INSERT INTO vote_result (candidacy_id, votes_obtained, is_winner, ranking_position)
        SELECT candidacy_id, 20000, false, 4
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_lisboa_muni_id AND party_id = v_cdu_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    INSERT INTO seat_result (candidacy_id, seats_obtained, total_seats_available)
        SELECT candidacy_id, 1, 17
        FROM candidacy WHERE election_id = v_election_id AND municipality_id = v_lisboa_muni_id AND party_id = v_cdu_id
        ON CONFLICT (candidacy_id) DO NOTHING;
    
    RAISE NOTICE 'Sample data loaded successfully!';
    RAISE NOTICE 'Porto municipality: % results loaded', (SELECT COUNT(*) FROM candidacy WHERE municipality_id = v_porto_muni_id);
    RAISE NOTICE 'Lisboa municipality: % results loaded', (SELECT COUNT(*) FROM candidacy WHERE municipality_id = v_lisboa_muni_id);
END $$;

-- Verify data was loaded
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

-- Show sample results
SELECT 
    m.municipality_name,
    COALESCE(p.party_acronym, 'N/A') as party,
    vr.votes_obtained,
    vr.vote_percentage,
    sr.seats_obtained
FROM candidacy c
JOIN municipality m ON c.municipality_id = m.municipality_id
LEFT JOIN party p ON c.party_id = p.party_id
JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
LEFT JOIN seat_result sr ON c.candidacy_id = sr.candidacy_id
ORDER BY m.municipality_name, vr.votes_obtained DESC;

RAISE NOTICE 'Sample data loading complete!';
RAISE NOTICE 'Now refresh your browser at http://localhost:8000/analytics';
