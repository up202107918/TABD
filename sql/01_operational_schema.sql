-- ============================================================================
-- OPERATIONAL SCHEMA FOR ELECTION ANALYTICS PLATFORM
-- Advanced Topics in Databases - Practical Assignment
-- ============================================================================
-- This schema represents the normalized operational database for Portuguese
-- election data, focusing on Autárquicas 2021 (Local Elections)
-- ============================================================================

-- Enable PostGIS extension for spatial data
CREATE EXTENSION IF NOT EXISTS postgis;

-- Drop existing schema if recreating
DROP SCHEMA IF EXISTS operational CASCADE;
CREATE SCHEMA operational;

SET search_path TO operational, public;

-- ============================================================================
-- TERRITORIAL HIERARCHY
-- ============================================================================

-- Districts (Distritos)
CREATE TABLE district (
    district_id SERIAL PRIMARY KEY,
    district_code VARCHAR(2) UNIQUE NOT NULL,  -- Official INE code
    district_name VARCHAR(100) NOT NULL,
    geometry GEOMETRY(MultiPolygon, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_district_code ON district(district_code);
CREATE INDEX idx_district_geom ON district USING GIST(geometry);

COMMENT ON TABLE district IS 'Portuguese districts (top administrative level)';
COMMENT ON COLUMN district.district_code IS 'Official INE district code (2 digits)';

-- Municipalities (Concelhos)
CREATE TABLE municipality (
    municipality_id SERIAL PRIMARY KEY,
    municipality_code VARCHAR(4) UNIQUE NOT NULL,  -- Official INE code (DDCC)
    municipality_name VARCHAR(100) NOT NULL,
    district_id INTEGER NOT NULL REFERENCES district(district_id),
    geometry GEOMETRY(MultiPolygon, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_municipality_code ON municipality(municipality_code);
CREATE INDEX idx_municipality_district ON municipality(district_id);
CREATE INDEX idx_municipality_geom ON municipality USING GIST(geometry);

COMMENT ON TABLE municipality IS 'Portuguese municipalities (concelhos)';
COMMENT ON COLUMN municipality.municipality_code IS 'Official INE municipality code (4 digits: DDCC)';

-- Parishes (Freguesias) - Optional but recommended
CREATE TABLE parish (
    parish_id SERIAL PRIMARY KEY,
    parish_code VARCHAR(6) UNIQUE NOT NULL,  -- Official INE code (DDCCFF)
    parish_name VARCHAR(200) NOT NULL,
    municipality_id INTEGER NOT NULL REFERENCES municipality(municipality_id),
    geometry GEOMETRY(MultiPolygon, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_parish_code ON parish(parish_code);
CREATE INDEX idx_parish_municipality ON parish(municipality_id);
CREATE INDEX idx_parish_geom ON parish USING GIST(geometry);

COMMENT ON TABLE parish IS 'Portuguese parishes (freguesias)';
COMMENT ON COLUMN parish.parish_code IS 'Official INE parish code (6 digits: DDCCFF)';

-- ============================================================================
-- ELECTION STRUCTURE
-- ============================================================================

-- Election Types (e.g., Autárquicas, Legislativas, Presidenciais)
CREATE TABLE election_type (
    election_type_id SERIAL PRIMARY KEY,
    type_code VARCHAR(10) UNIQUE NOT NULL,
    type_name VARCHAR(100) NOT NULL,
    description TEXT
);

INSERT INTO election_type (type_code, type_name, description) VALUES
    ('AUT', 'Autárquicas', 'Local/Municipal Elections'),
    ('LEG', 'Legislativas', 'Legislative/Parliamentary Elections'),
    ('PRE', 'Presidenciais', 'Presidential Elections'),
    ('EUR', 'Europeias', 'European Parliament Elections');

-- Elections (Specific election events)
CREATE TABLE election (
    election_id SERIAL PRIMARY KEY,
    election_type_id INTEGER NOT NULL REFERENCES election_type(election_type_id),
    election_date DATE NOT NULL,
    election_year INTEGER NOT NULL,
    description VARCHAR(200),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(election_type_id, election_date)
);

CREATE INDEX idx_election_date ON election(election_date);
CREATE INDEX idx_election_year ON election(election_year);

COMMENT ON TABLE election IS 'Specific election events (e.g., Autárquicas 2021)';

-- Electoral Organs/Offices (e.g., Câmara Municipal, Assembleia Municipal, Junta de Freguesia)
CREATE TABLE electoral_organ (
    organ_id SERIAL PRIMARY KEY,
    organ_code VARCHAR(10) UNIQUE NOT NULL,
    organ_name VARCHAR(100) NOT NULL,
    description TEXT,
    territorial_level VARCHAR(20) CHECK (territorial_level IN ('district', 'municipality', 'parish'))
);

INSERT INTO electoral_organ (organ_code, organ_name, description, territorial_level) VALUES
    ('CM', 'Câmara Municipal', 'Municipal Council/Chamber', 'municipality'),
    ('AM', 'Assembleia Municipal', 'Municipal Assembly', 'municipality'),
    ('JF', 'Junta de Freguesia', 'Parish Council', 'parish');

COMMENT ON TABLE electoral_organ IS 'Electoral organs/offices being elected (e.g., Câmara Municipal)';

-- ============================================================================
-- POLITICAL ENTITIES
-- ============================================================================

-- Political Parties
CREATE TABLE party (
    party_id SERIAL PRIMARY KEY,
    party_acronym VARCHAR(20) UNIQUE NOT NULL,
    party_name VARCHAR(200) NOT NULL,
    party_code VARCHAR(10),  -- Official CNE code if available
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_party_acronym ON party(party_acronym);

COMMENT ON TABLE party IS 'Political parties participating in elections';

-- Coalitions (when multiple parties run together)
CREATE TABLE coalition (
    coalition_id SERIAL PRIMARY KEY,
    coalition_acronym VARCHAR(50) UNIQUE NOT NULL,
    coalition_name VARCHAR(200),
    election_id INTEGER REFERENCES election(election_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_coalition_election ON coalition(election_id);

COMMENT ON TABLE coalition IS 'Electoral coalitions formed by multiple parties';

-- Coalition membership (which parties form which coalitions)
CREATE TABLE coalition_member (
    coalition_member_id SERIAL PRIMARY KEY,
    coalition_id INTEGER NOT NULL REFERENCES coalition(coalition_id) ON DELETE CASCADE,
    party_id INTEGER NOT NULL REFERENCES party(party_id),
    is_lead_party BOOLEAN DEFAULT false,
    UNIQUE(coalition_id, party_id)
);

CREATE INDEX idx_coalition_member_coalition ON coalition_member(coalition_id);
CREATE INDEX idx_coalition_member_party ON coalition_member(party_id);

COMMENT ON TABLE coalition_member IS 'Parties that form coalitions';

-- ============================================================================
-- CANDIDACIES
-- ============================================================================

-- Candidacies (a party or coalition running for a specific organ in a specific territory)
CREATE TABLE candidacy (
    candidacy_id SERIAL PRIMARY KEY,
    election_id INTEGER NOT NULL REFERENCES election(election_id),
    organ_id INTEGER NOT NULL REFERENCES electoral_organ(organ_id),
    
    -- Territorial context (one of these should be NOT NULL based on organ level)
    district_id INTEGER REFERENCES district(district_id),
    municipality_id INTEGER REFERENCES municipality(municipality_id),
    parish_id INTEGER REFERENCES parish(parish_id),
    
    -- Political entity (either party OR coalition, not both)
    party_id INTEGER REFERENCES party(party_id),
    coalition_id INTEGER REFERENCES coalition(coalition_id),
    
    -- Candidate list details
    candidate_name VARCHAR(200),  -- Lead candidate name
    candidate_list_number INTEGER,  -- Official list number
    
    is_independent BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (
        (party_id IS NOT NULL AND coalition_id IS NULL) OR
        (party_id IS NULL AND coalition_id IS NOT NULL)
    )
    -- Note: Territorial level validation moved to trigger (PostgreSQL doesn't allow subqueries in CHECK)
);

CREATE INDEX idx_candidacy_election ON candidacy(election_id);
CREATE INDEX idx_candidacy_organ ON candidacy(organ_id);
CREATE INDEX idx_candidacy_municipality ON candidacy(municipality_id);
CREATE INDEX idx_candidacy_party ON candidacy(party_id);
CREATE INDEX idx_candidacy_coalition ON candidacy(coalition_id);

COMMENT ON TABLE candidacy IS 'Specific candidacies: party/coalition running for organ in territory';

-- ============================================================================
-- ELECTORAL RESULTS
-- ============================================================================

-- Vote Results (raw vote counts for each candidacy)
CREATE TABLE vote_result (
    vote_result_id SERIAL PRIMARY KEY,
    candidacy_id INTEGER NOT NULL REFERENCES candidacy(candidacy_id),
    
    votes_obtained INTEGER NOT NULL CHECK (votes_obtained >= 0),
    vote_percentage NUMERIC(5,2),  -- Percentage of valid votes
    
    -- Metadata
    is_winner BOOLEAN DEFAULT false,
    ranking_position INTEGER,  -- Position in ranking (1st, 2nd, 3rd, etc.)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(candidacy_id)
);

CREATE INDEX idx_vote_result_candidacy ON vote_result(candidacy_id);
CREATE INDEX idx_vote_result_votes ON vote_result(votes_obtained DESC);

COMMENT ON TABLE vote_result IS 'Vote counts for each candidacy';

-- Seat Results (mandates/seats won by each candidacy)
CREATE TABLE seat_result (
    seat_result_id SERIAL PRIMARY KEY,
    candidacy_id INTEGER NOT NULL REFERENCES candidacy(candidacy_id),
    
    seats_obtained INTEGER NOT NULL CHECK (seats_obtained >= 0),
    total_seats_available INTEGER,  -- Total seats for this organ/territory
    
    allocation_method VARCHAR(50) DEFAULT 'D''Hondt',  -- Seat allocation method used
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(candidacy_id)
);

CREATE INDEX idx_seat_result_candidacy ON seat_result(candidacy_id);

COMMENT ON TABLE seat_result IS 'Seats/mandates won by each candidacy';

-- Turnout Information (aggregated by territory and election)
CREATE TABLE turnout (
    turnout_id SERIAL PRIMARY KEY,
    election_id INTEGER NOT NULL REFERENCES election(election_id),
    organ_id INTEGER NOT NULL REFERENCES electoral_organ(organ_id),
    
    -- Territorial context
    district_id INTEGER REFERENCES district(district_id),
    municipality_id INTEGER REFERENCES municipality(municipality_id),
    parish_id INTEGER REFERENCES parish(parish_id),
    
    -- Turnout statistics
    registered_voters INTEGER NOT NULL CHECK (registered_voters >= 0),
    votes_cast INTEGER NOT NULL CHECK (votes_cast >= 0),
    valid_votes INTEGER NOT NULL CHECK (valid_votes >= 0),
    blank_votes INTEGER DEFAULT 0 CHECK (blank_votes >= 0),
    null_votes INTEGER DEFAULT 0 CHECK (null_votes >= 0),
    
    -- Computed metrics (can be calculated by trigger)
    turnout_percentage NUMERIC(5,2),
    abstention_percentage NUMERIC(5,2),
    blank_percentage NUMERIC(5,2),
    null_percentage NUMERIC(5,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (votes_cast <= registered_voters),
    CHECK (valid_votes + blank_votes + null_votes = votes_cast),
    
    UNIQUE(election_id, organ_id, district_id, municipality_id, parish_id)
);

CREATE INDEX idx_turnout_election ON turnout(election_id);
CREATE INDEX idx_turnout_municipality ON turnout(municipality_id);
CREATE INDEX idx_turnout_percentage ON turnout(turnout_percentage);

COMMENT ON TABLE turnout IS 'Voter turnout statistics for each electoral contest';

-- ============================================================================
-- SUMMARY TABLES (for performance)
-- ============================================================================

-- Party performance summary by municipality (materialized for quick access)
CREATE TABLE party_municipality_summary (
    summary_id SERIAL PRIMARY KEY,
    election_id INTEGER NOT NULL REFERENCES election(election_id),
    municipality_id INTEGER NOT NULL REFERENCES municipality(municipality_id),
    party_id INTEGER NOT NULL REFERENCES party(party_id),
    
    total_votes INTEGER DEFAULT 0,
    total_seats INTEGER DEFAULT 0,
    organs_won INTEGER DEFAULT 0,  -- Number of organs where party won
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(election_id, municipality_id, party_id)
);

CREATE INDEX idx_party_muni_summary_election ON party_municipality_summary(election_id);
CREATE INDEX idx_party_muni_summary_municipality ON party_municipality_summary(municipality_id);
CREATE INDEX idx_party_muni_summary_party ON party_municipality_summary(party_id);

COMMENT ON TABLE party_municipality_summary IS 'Pre-computed party performance by municipality';

-- ============================================================================
-- AUDIT TRAIL
-- ============================================================================

CREATE TABLE audit_log (
    audit_id SERIAL PRIMARY KEY,
    table_name VARCHAR(100),
    operation VARCHAR(10),  -- INSERT, UPDATE, DELETE
    record_id INTEGER,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    old_values JSONB,
    new_values JSONB
);

CREATE INDEX idx_audit_log_table ON audit_log(table_name);
CREATE INDEX idx_audit_log_timestamp ON audit_log(changed_at);

COMMENT ON TABLE audit_log IS 'Audit trail for data changes';

-- ============================================================================
-- INITIAL DATA SETUP
-- ============================================================================

-- Add 2021 Local Elections
INSERT INTO election (election_type_id, election_date, election_year, description)
VALUES (
    (SELECT election_type_id FROM election_type WHERE type_code = 'AUT'),
    '2021-09-26',
    2021,
    'Eleições Autárquicas 2021'
);

-- ============================================================================
-- GRANT PERMISSIONS (adjust based on your setup)
-- ============================================================================

-- Grant read access to application user
-- GRANT USAGE ON SCHEMA operational TO election_app_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA operational TO election_app_user;
-- GRANT SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA operational TO election_app_user;

COMMENT ON SCHEMA operational IS 'Operational schema for normalized election data';
