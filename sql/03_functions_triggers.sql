-- ============================================================================
-- SQL FUNCTIONS, PL/pgSQL ROUTINES, AND TRIGGERS
-- Advanced Topics in Databases - Practical Assignment
-- ============================================================================

SET search_path TO operational, warehouse, public;

-- ============================================================================
-- SQL FUNCTIONS AND VIEWS
-- ============================================================================

-- Function 1: Calculate vote percentage for a candidacy
CREATE OR REPLACE FUNCTION calculate_vote_percentage(
    p_candidacy_id INTEGER
) RETURNS NUMERIC(5,2) AS $$
DECLARE
    v_votes INTEGER;
    v_total_valid_votes INTEGER;
    v_percentage NUMERIC(5,2);
BEGIN
    -- Get votes for this candidacy
    SELECT votes_obtained INTO v_votes
    FROM vote_result
    WHERE candidacy_id = p_candidacy_id;
    
    IF v_votes IS NULL THEN
        RETURN NULL;
    END IF;
    
    -- Get total valid votes for the same contest
    SELECT t.valid_votes INTO v_total_valid_votes
    FROM candidacy c
    JOIN turnout t ON (
        t.election_id = c.election_id AND
        t.organ_id = c.organ_id AND
        COALESCE(t.district_id, -1) = COALESCE(c.district_id, -1) AND
        COALESCE(t.municipality_id, -1) = COALESCE(c.municipality_id, -1) AND
        COALESCE(t.parish_id, -1) = COALESCE(c.parish_id, -1)
    )
    WHERE c.candidacy_id = p_candidacy_id;
    
    IF v_total_valid_votes IS NULL OR v_total_valid_votes = 0 THEN
        RETURN NULL;
    END IF;
    
    v_percentage := (v_votes::NUMERIC / v_total_valid_votes) * 100;
    
    RETURN ROUND(v_percentage, 2);
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION calculate_vote_percentage IS 
'Calculate the percentage of valid votes obtained by a candidacy';

-- Function 2: Get party performance summary for a municipality
CREATE OR REPLACE FUNCTION get_party_performance_in_municipality(
    p_election_id INTEGER,
    p_municipality_id INTEGER,
    p_party_acronym VARCHAR
) RETURNS TABLE (
    party_name VARCHAR,
    total_votes BIGINT,
    avg_percentage NUMERIC,
    total_seats BIGINT,
    organs_contested BIGINT,
    organs_won BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.party_name::VARCHAR,
        SUM(vr.votes_obtained) as total_votes,
        ROUND(AVG(vr.vote_percentage), 2) as avg_percentage,
        SUM(COALESCE(sr.seats_obtained, 0)) as total_seats,
        COUNT(DISTINCT c.organ_id) as organs_contested,
        COUNT(DISTINCT CASE WHEN vr.is_winner THEN c.organ_id END) as organs_won
    FROM candidacy c
    JOIN party p ON c.party_id = p.party_id
    LEFT JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
    LEFT JOIN seat_result sr ON c.candidacy_id = sr.candidacy_id
    WHERE c.election_id = p_election_id
        AND c.municipality_id = p_municipality_id
        AND p.party_acronym = p_party_acronym
    GROUP BY p.party_name;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_party_performance_in_municipality IS 
'Get comprehensive performance metrics for a party in a specific municipality';

-- Function 3: Get top N parties by votes in a territory
CREATE OR REPLACE FUNCTION get_top_parties(
    p_election_id INTEGER,
    p_municipality_id INTEGER,
    p_organ_id INTEGER,
    p_limit INTEGER DEFAULT 5
) RETURNS TABLE (
    ranking INTEGER,
    party_acronym VARCHAR,
    party_name VARCHAR,
    votes BIGINT,
    percentage NUMERIC,
    seats INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ROW_NUMBER() OVER (ORDER BY SUM(vr.votes_obtained) DESC)::INTEGER as ranking,
        COALESCE(p.party_acronym, co.coalition_acronym)::VARCHAR as party_acronym,
        COALESCE(p.party_name, co.coalition_name)::VARCHAR as party_name,
        SUM(vr.votes_obtained) as votes,
        ROUND(AVG(vr.vote_percentage), 2) as percentage,
        SUM(COALESCE(sr.seats_obtained, 0))::INTEGER as seats
    FROM candidacy c
    LEFT JOIN party p ON c.party_id = p.party_id
    LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
    LEFT JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
    LEFT JOIN seat_result sr ON c.candidacy_id = sr.candidacy_id
    WHERE c.election_id = p_election_id
        AND c.municipality_id = p_municipality_id
        AND c.organ_id = p_organ_id
    GROUP BY p.party_acronym, p.party_name, co.coalition_acronym, co.coalition_name
    ORDER BY votes DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_top_parties IS 
'Get top N parties/coalitions by votes for a specific electoral contest';

-- View 1: Complete candidacy information (joins all related tables)
CREATE OR REPLACE VIEW vw_candidacy_details AS
SELECT 
    c.candidacy_id,
    e.election_year,
    e.description as election_description,
    eo.organ_name,
    d.district_name,
    m.municipality_name,
    par.parish_name,
    COALESCE(p.party_acronym, co.coalition_acronym) as political_entity,
    COALESCE(p.party_name, co.coalition_name) as entity_full_name,
    c.is_independent,
    c.candidate_name,
    vr.votes_obtained,
    vr.vote_percentage,
    vr.is_winner,
    vr.ranking_position,
    sr.seats_obtained
FROM candidacy c
JOIN election e ON c.election_id = e.election_id
JOIN electoral_organ eo ON c.organ_id = eo.organ_id
LEFT JOIN district d ON c.district_id = d.district_id
LEFT JOIN municipality m ON c.municipality_id = m.municipality_id
LEFT JOIN parish par ON c.parish_id = par.parish_id
LEFT JOIN party p ON c.party_id = p.party_id
LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
LEFT JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
LEFT JOIN seat_result sr ON c.candidacy_id = sr.candidacy_id;

COMMENT ON VIEW vw_candidacy_details IS 
'Complete denormalized view of candidacy information with results';

-- View 2: Municipality election summary
CREATE OR REPLACE VIEW vw_municipality_summary AS
SELECT 
    e.election_year,
    m.municipality_name,
    d.district_name,
    eo.organ_name,
    COUNT(DISTINCT c.candidacy_id) as total_candidacies,
    SUM(vr.votes_obtained) as total_votes,
    MAX(CASE WHEN vr.is_winner THEN COALESCE(p.party_acronym, co.coalition_acronym) END) as winner,
    t.registered_voters,
    t.votes_cast,
    t.turnout_percentage
FROM candidacy c
JOIN election e ON c.election_id = e.election_id
JOIN electoral_organ eo ON c.organ_id = eo.organ_id
JOIN municipality m ON c.municipality_id = m.municipality_id
JOIN district d ON m.district_id = d.district_id
LEFT JOIN party p ON c.party_id = p.party_id
LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
LEFT JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
LEFT JOIN turnout t ON (
    t.election_id = c.election_id AND 
    t.organ_id = c.organ_id AND 
    COALESCE(t.district_id, -1) = COALESCE(c.district_id, -1) AND
    t.municipality_id = c.municipality_id
)
GROUP BY e.election_year, m.municipality_name, d.district_name, eo.organ_name,
         t.registered_voters, t.votes_cast, t.turnout_percentage;

COMMENT ON VIEW vw_municipality_summary IS 
'Summary of election results by municipality and organ';

-- ============================================================================
-- PL/pgSQL ROUTINES
-- ============================================================================

-- PL/pgSQL Routine 1: D'Hondt Method for Seat Allocation
CREATE OR REPLACE FUNCTION allocate_seats_dhondt(
    p_election_id INTEGER,
    p_organ_id INTEGER,
    p_municipality_id INTEGER,
    p_total_seats INTEGER
) RETURNS TABLE (
    candidacy_id INTEGER,
    party_name VARCHAR,
    votes INTEGER,
    seats_allocated INTEGER
) AS $$
DECLARE
    v_candidacy RECORD;
    v_quotient NUMERIC;
    v_max_quotient NUMERIC;
    v_winner_candidacy_id INTEGER;
    v_seats_remaining INTEGER := p_total_seats;
    v_temp_seats JSONB := '{}'::JSONB;
BEGIN
    -- Initialize seat counts for all candidacies
    FOR v_candidacy IN 
        SELECT c.candidacy_id, vr.votes_obtained
        FROM candidacy c
        JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
        WHERE c.election_id = p_election_id
            AND c.organ_id = p_organ_id
            AND c.municipality_id = p_municipality_id
            AND vr.votes_obtained > 0
    LOOP
        v_temp_seats := jsonb_set(v_temp_seats, 
                                  ARRAY[v_candidacy.candidacy_id::TEXT], 
                                  '0'::JSONB);
    END LOOP;
    
    -- Allocate seats one by one using D'Hondt method
    WHILE v_seats_remaining > 0 LOOP
        v_max_quotient := 0;
        v_winner_candidacy_id := NULL;
        
        -- Find candidacy with highest quotient
        FOR v_candidacy IN 
            SELECT c.candidacy_id, vr.votes_obtained
            FROM candidacy c
            JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
            WHERE c.election_id = p_election_id
                AND c.organ_id = p_organ_id
                AND c.municipality_id = p_municipality_id
                AND vr.votes_obtained > 0
        LOOP
            -- Calculate quotient: votes / (seats_won + 1)
            v_quotient := v_candidacy.votes_obtained::NUMERIC / 
                         ((v_temp_seats->>v_candidacy.candidacy_id::TEXT)::INTEGER + 1);
            
            IF v_quotient > v_max_quotient THEN
                v_max_quotient := v_quotient;
                v_winner_candidacy_id := v_candidacy.candidacy_id;
            END IF;
        END LOOP;
        
        -- Allocate seat to winner
        IF v_winner_candidacy_id IS NOT NULL THEN
            v_temp_seats := jsonb_set(
                v_temp_seats,
                ARRAY[v_winner_candidacy_id::TEXT],
                ((v_temp_seats->>v_winner_candidacy_id::TEXT)::INTEGER + 1)::TEXT::JSONB
            );
            v_seats_remaining := v_seats_remaining - 1;
        ELSE
            -- No more candidates to allocate to
            EXIT;
        END IF;
    END LOOP;
    
    -- Return results
    RETURN QUERY
    SELECT 
        c.candidacy_id,
        COALESCE(p.party_name, co.coalition_name)::VARCHAR as party_name,
        vr.votes_obtained::INTEGER,
        (v_temp_seats->>c.candidacy_id::TEXT)::INTEGER as seats_allocated
    FROM candidacy c
    JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
    LEFT JOIN party p ON c.party_id = p.party_id
    LEFT JOIN coalition co ON c.coalition_id = co.coalition_id
    WHERE c.election_id = p_election_id
        AND c.organ_id = p_organ_id
        AND c.municipality_id = p_municipality_id
    ORDER BY seats_allocated DESC, vr.votes_obtained DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION allocate_seats_dhondt IS 
'Allocate seats using D''Hondt method for a specific electoral contest';

-- PL/pgSQL Routine 2: Update summary tables after result changes
CREATE OR REPLACE PROCEDURE refresh_party_municipality_summary(
    p_election_id INTEGER DEFAULT NULL
) AS $$
DECLARE
    v_election_id INTEGER;
BEGIN
    -- If election_id provided, refresh only that election
    -- Otherwise refresh all elections
    FOR v_election_id IN 
        SELECT DISTINCT election_id 
        FROM election 
        WHERE p_election_id IS NULL OR election_id = p_election_id
    LOOP
        -- Delete existing summary for this election
        DELETE FROM party_municipality_summary
        WHERE election_id = v_election_id;
        
        -- Rebuild summary
        INSERT INTO party_municipality_summary 
            (election_id, municipality_id, party_id, total_votes, total_seats, organs_won)
        SELECT 
            c.election_id,
            c.municipality_id,
            c.party_id,
            SUM(vr.votes_obtained) as total_votes,
            SUM(COALESCE(sr.seats_obtained, 0)) as total_seats,
            COUNT(DISTINCT CASE WHEN vr.is_winner THEN c.organ_id END) as organs_won
        FROM candidacy c
        LEFT JOIN vote_result vr ON c.candidacy_id = vr.candidacy_id
        LEFT JOIN seat_result sr ON c.candidacy_id = sr.candidacy_id
        WHERE c.election_id = v_election_id
            AND c.party_id IS NOT NULL  -- Only single parties, not coalitions
            AND c.municipality_id IS NOT NULL
        GROUP BY c.election_id, c.municipality_id, c.party_id;
        
        RAISE NOTICE 'Refreshed summary for election %', v_election_id;
    END LOOP;
    
    COMMIT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON PROCEDURE refresh_party_municipality_summary IS 
'Refresh pre-computed party performance summaries by municipality';

-- PL/pgSQL Routine 3: Calculate and update all turnout percentages
CREATE OR REPLACE FUNCTION calculate_turnout_percentages()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
BEGIN
    UPDATE turnout
    SET 
        turnout_percentage = CASE 
            WHEN registered_voters > 0 
            THEN ROUND((votes_cast::NUMERIC / registered_voters) * 100, 2)
            ELSE NULL 
        END,
        abstention_percentage = CASE 
            WHEN registered_voters > 0 
            THEN ROUND(((registered_voters - votes_cast)::NUMERIC / registered_voters) * 100, 2)
            ELSE NULL 
        END,
        blank_percentage = CASE 
            WHEN votes_cast > 0 
            THEN ROUND((blank_votes::NUMERIC / votes_cast) * 100, 2)
            ELSE NULL 
        END,
        null_percentage = CASE 
            WHEN votes_cast > 0 
            THEN ROUND((null_votes::NUMERIC / votes_cast) * 100, 2)
            ELSE NULL 
        END
    WHERE turnout_percentage IS NULL 
        OR abstention_percentage IS NULL
        OR blank_percentage IS NULL
        OR null_percentage IS NULL;
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_turnout_percentages IS 
'Calculate and update all missing turnout percentages';

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger 1: Automatically calculate turnout percentages on INSERT/UPDATE
CREATE OR REPLACE FUNCTION trg_calculate_turnout()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate turnout percentage
    IF NEW.registered_voters > 0 THEN
        NEW.turnout_percentage := ROUND((NEW.votes_cast::NUMERIC / NEW.registered_voters) * 100, 2);
        NEW.abstention_percentage := ROUND(((NEW.registered_voters - NEW.votes_cast)::NUMERIC / NEW.registered_voters) * 100, 2);
    END IF;
    
    -- Calculate blank and null percentages
    IF NEW.votes_cast > 0 THEN
        NEW.blank_percentage := ROUND((NEW.blank_votes::NUMERIC / NEW.votes_cast) * 100, 2);
        NEW.null_percentage := ROUND((NEW.null_votes::NUMERIC / NEW.votes_cast) * 100, 2);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_turnout_percentages
    BEFORE INSERT OR UPDATE ON turnout
    FOR EACH ROW
    EXECUTE FUNCTION trg_calculate_turnout();

COMMENT ON TRIGGER trg_turnout_percentages ON turnout IS 
'Automatically calculate turnout percentages before insert/update';

-- Trigger 2: Automatically calculate vote percentages on INSERT/UPDATE
CREATE OR REPLACE FUNCTION trg_calculate_vote_percentage()
RETURNS TRIGGER AS $$
DECLARE
    v_total_valid_votes INTEGER;
BEGIN
    -- Get total valid votes for the same contest
    SELECT t.valid_votes INTO v_total_valid_votes
    FROM candidacy c
    JOIN turnout t ON (
        t.election_id = c.election_id AND
        t.organ_id = c.organ_id AND
        COALESCE(t.district_id, -1) = COALESCE(c.district_id, -1) AND
        COALESCE(t.municipality_id, -1) = COALESCE(c.municipality_id, -1) AND
        COALESCE(t.parish_id, -1) = COALESCE(c.parish_id, -1)
    )
    WHERE c.candidacy_id = NEW.candidacy_id;
    
    -- Calculate percentage
    IF v_total_valid_votes IS NOT NULL AND v_total_valid_votes > 0 THEN
        NEW.vote_percentage := ROUND((NEW.votes_obtained::NUMERIC / v_total_valid_votes) * 100, 2);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vote_percentages
    BEFORE INSERT OR UPDATE ON vote_result
    FOR EACH ROW
    EXECUTE FUNCTION trg_calculate_vote_percentage();

COMMENT ON TRIGGER trg_vote_percentages ON vote_result IS 
'Automatically calculate vote percentages before insert/update';

-- Trigger 3: Audit log for important table changes
CREATE OR REPLACE FUNCTION trg_audit_log()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_values)
        VALUES (TG_TABLE_NAME, TG_OP, OLD.candidacy_id, row_to_json(OLD)::JSONB);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
        VALUES (TG_TABLE_NAME, TG_OP, NEW.candidacy_id, row_to_json(OLD)::JSONB, row_to_json(NEW)::JSONB);
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation, record_id, new_values)
        VALUES (TG_TABLE_NAME, TG_OP, NEW.candidacy_id, row_to_json(NEW)::JSONB);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_candidacy
    AFTER INSERT OR UPDATE OR DELETE ON candidacy
    FOR EACH ROW
    EXECUTE FUNCTION trg_audit_log();

CREATE TRIGGER trg_audit_vote_result
    AFTER INSERT OR UPDATE OR DELETE ON vote_result
    FOR EACH ROW
    EXECUTE FUNCTION trg_audit_log();

COMMENT ON FUNCTION trg_audit_log IS 
'Generic audit logging function for tracking changes to critical tables';

-- ============================================================================
-- HELPER FUNCTIONS FOR ETL
-- ============================================================================

-- Function to get or create a party (useful for ETL)
CREATE OR REPLACE FUNCTION get_or_create_party(
    p_party_acronym VARCHAR,
    p_party_name VARCHAR DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_party_id INTEGER;
BEGIN
    -- Try to find existing party
    SELECT party_id INTO v_party_id
    FROM party
    WHERE party_acronym = p_party_acronym;
    
    -- If not found, create it
    IF v_party_id IS NULL THEN
        INSERT INTO party (party_acronym, party_name)
        VALUES (p_party_acronym, COALESCE(p_party_name, p_party_acronym))
        RETURNING party_id INTO v_party_id;
    END IF;
    
    RETURN v_party_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_or_create_party IS 
'Get existing party or create new one if not exists (ETL helper)';
