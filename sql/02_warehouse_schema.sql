-- ============================================================================
-- DATA WAREHOUSE SCHEMA FOR ELECTION ANALYTICS
-- Advanced Topics in Databases - Practical Assignment
-- ============================================================================
-- Star schema design optimized for analytical queries and OLAP operations
-- ============================================================================

DROP SCHEMA IF EXISTS warehouse CASCADE;
CREATE SCHEMA warehouse;

SET search_path TO warehouse, operational, public;

-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

-- Dimension: Time (for temporal analysis)
CREATE TABLE dim_time (
    time_key INTEGER PRIMARY KEY,  -- YYYYMMDD format
    full_date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20),
    day INTEGER NOT NULL,
    day_of_week INTEGER,
    day_name VARCHAR(20),
    is_weekend BOOLEAN
);

CREATE INDEX idx_dim_time_year ON dim_time(year);
CREATE INDEX idx_dim_time_quarter ON dim_time(year, quarter);
CREATE INDEX idx_dim_time_month ON dim_time(year, month);

COMMENT ON TABLE dim_time IS 'Time dimension for temporal analysis';

-- Dimension: Election
CREATE TABLE dim_election (
    election_key SERIAL PRIMARY KEY,
    election_id INTEGER UNIQUE NOT NULL,  -- FK to operational.election
    election_type_code VARCHAR(10),
    election_type_name VARCHAR(100),
    election_date DATE,
    election_year INTEGER,
    election_description VARCHAR(200)
);

CREATE INDEX idx_dim_election_year ON dim_election(election_year);
CREATE INDEX idx_dim_election_type ON dim_election(election_type_code);

COMMENT ON TABLE dim_election IS 'Election dimension with type and temporal info';

-- Dimension: Electoral Organ
CREATE TABLE dim_organ (
    organ_key SERIAL PRIMARY KEY,
    organ_id INTEGER UNIQUE NOT NULL,  -- FK to operational.electoral_organ
    organ_code VARCHAR(10),
    organ_name VARCHAR(100),
    organ_description TEXT,
    territorial_level VARCHAR(20)
);

CREATE INDEX idx_dim_organ_level ON dim_organ(territorial_level);

COMMENT ON TABLE dim_organ IS 'Electoral organ dimension';

-- Dimension: Geography/Territory (snowflake approach)
CREATE TABLE dim_district (
    district_key SERIAL PRIMARY KEY,
    district_id INTEGER UNIQUE NOT NULL,  -- FK to operational.district
    district_code VARCHAR(2),
    district_name VARCHAR(100),
    has_geometry BOOLEAN DEFAULT false
);

CREATE INDEX idx_dim_district_code ON dim_district(district_code);

CREATE TABLE dim_municipality (
    municipality_key SERIAL PRIMARY KEY,
    municipality_id INTEGER UNIQUE NOT NULL,  -- FK to operational.municipality
    municipality_code VARCHAR(4),
    municipality_name VARCHAR(100),
    district_key INTEGER REFERENCES dim_district(district_key),
    district_name VARCHAR(100),  -- Denormalized for query performance
    has_geometry BOOLEAN DEFAULT false
);

CREATE INDEX idx_dim_municipality_code ON dim_municipality(municipality_code);
CREATE INDEX idx_dim_municipality_district ON dim_municipality(district_key);

CREATE TABLE dim_parish (
    parish_key SERIAL PRIMARY KEY,
    parish_id INTEGER UNIQUE NOT NULL,  -- FK to operational.parish
    parish_code VARCHAR(6),
    parish_name VARCHAR(200),
    municipality_key INTEGER REFERENCES dim_municipality(municipality_key),
    municipality_name VARCHAR(100),  -- Denormalized
    district_key INTEGER REFERENCES dim_district(district_key),
    district_name VARCHAR(100),  -- Denormalized
    has_geometry BOOLEAN DEFAULT false
);

CREATE INDEX idx_dim_parish_code ON dim_parish(parish_code);
CREATE INDEX idx_dim_parish_municipality ON dim_parish(municipality_key);

COMMENT ON TABLE dim_district IS 'District dimension';
COMMENT ON TABLE dim_municipality IS 'Municipality dimension with district hierarchy';
COMMENT ON TABLE dim_parish IS 'Parish dimension with municipality and district hierarchy';

-- Dimension: Political Party
CREATE TABLE dim_party (
    party_key SERIAL PRIMARY KEY,
    party_id INTEGER,  -- FK to operational.party (nullable for coalitions)
    party_acronym VARCHAR(20),
    party_name VARCHAR(200),
    party_code VARCHAR(10),
    is_coalition BOOLEAN DEFAULT false,
    coalition_id INTEGER,  -- FK to operational.coalition if is_coalition = true
    coalition_member_parties TEXT,  -- Comma-separated list of party acronyms in coalition
    
    -- Classification for analytics
    political_spectrum VARCHAR(20),  -- e.g., 'left', 'center', 'right'
    party_size VARCHAR(20),  -- e.g., 'major', 'minor', 'independent'
    
    UNIQUE(party_id, coalition_id)
);

CREATE INDEX idx_dim_party_acronym ON dim_party(party_acronym);
CREATE INDEX idx_dim_party_coalition ON dim_party(is_coalition);
CREATE INDEX idx_dim_party_spectrum ON dim_party(political_spectrum);

COMMENT ON TABLE dim_party IS 'Party dimension including coalitions';

-- ============================================================================
-- FACT TABLES
-- ============================================================================

-- Fact: Election Results (main fact table)
CREATE TABLE fact_election_result (
    result_key BIGSERIAL PRIMARY KEY,
    
    -- Dimension foreign keys
    time_key INTEGER REFERENCES dim_time(time_key),
    election_key INTEGER NOT NULL REFERENCES dim_election(election_key),
    organ_key INTEGER NOT NULL REFERENCES dim_organ(organ_key),
    
    -- Geography keys (one will be NULL based on organ level)
    district_key INTEGER REFERENCES dim_district(district_key),
    municipality_key INTEGER REFERENCES dim_municipality(municipality_key),
    parish_key INTEGER REFERENCES dim_parish(parish_key),
    
    party_key INTEGER NOT NULL REFERENCES dim_party(party_key),
    
    -- Measures (facts)
    votes_obtained INTEGER NOT NULL DEFAULT 0,
    vote_percentage NUMERIC(5,2),
    seats_obtained INTEGER NOT NULL DEFAULT 0,
    
    -- Derived/computed measures
    is_winner BOOLEAN DEFAULT false,
    ranking_position INTEGER,
    vote_seat_ratio NUMERIC(10,4),  -- Votes per seat (for proportionality analysis)
    
    -- Additional context
    candidacy_id INTEGER,  -- Link back to operational for drill-through
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure proper geographic level
    CHECK (
        (district_key IS NOT NULL AND municipality_key IS NULL AND parish_key IS NULL) OR
        (municipality_key IS NOT NULL AND parish_key IS NULL) OR
        (parish_key IS NOT NULL)
    )
);

-- Indexes for common query patterns
CREATE INDEX idx_fact_result_election ON fact_election_result(election_key);
CREATE INDEX idx_fact_result_organ ON fact_election_result(organ_key);
CREATE INDEX idx_fact_result_party ON fact_election_result(party_key);
CREATE INDEX idx_fact_result_municipality ON fact_election_result(municipality_key);
CREATE INDEX idx_fact_result_district ON fact_election_result(district_key);
CREATE INDEX idx_fact_result_votes ON fact_election_result(votes_obtained DESC);
CREATE INDEX idx_fact_result_seats ON fact_election_result(seats_obtained DESC);

-- Composite indexes for common join patterns
CREATE INDEX idx_fact_result_election_muni ON fact_election_result(election_key, municipality_key);
CREATE INDEX idx_fact_result_election_party ON fact_election_result(election_key, party_key);

COMMENT ON TABLE fact_election_result IS 'Main fact table: election results by party/territory/organ';

-- Fact: Turnout (aggregated turnout statistics)
CREATE TABLE fact_turnout (
    turnout_key BIGSERIAL PRIMARY KEY,
    
    -- Dimension foreign keys
    time_key INTEGER REFERENCES dim_time(time_key),
    election_key INTEGER NOT NULL REFERENCES dim_election(election_key),
    organ_key INTEGER NOT NULL REFERENCES dim_organ(organ_key),
    
    -- Geography keys
    district_key INTEGER REFERENCES dim_district(district_key),
    municipality_key INTEGER REFERENCES dim_municipality(municipality_key),
    parish_key INTEGER REFERENCES dim_parish(parish_key),
    
    -- Measures
    registered_voters INTEGER NOT NULL,
    votes_cast INTEGER NOT NULL,
    valid_votes INTEGER NOT NULL,
    blank_votes INTEGER DEFAULT 0,
    null_votes INTEGER DEFAULT 0,
    abstentions INTEGER,  -- registered_voters - votes_cast
    
    -- Percentages (derived measures)
    turnout_percentage NUMERIC(5,2),
    abstention_percentage NUMERIC(5,2),
    blank_percentage NUMERIC(5,2),
    null_percentage NUMERIC(5,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (
        (district_key IS NOT NULL AND municipality_key IS NULL AND parish_key IS NULL) OR
        (municipality_key IS NOT NULL AND parish_key IS NULL) OR
        (parish_key IS NOT NULL)
    )
);

CREATE INDEX idx_fact_turnout_election ON fact_turnout(election_key);
CREATE INDEX idx_fact_turnout_municipality ON fact_turnout(municipality_key);
CREATE INDEX idx_fact_turnout_percentage ON fact_turnout(turnout_percentage);

COMMENT ON TABLE fact_turnout IS 'Fact table: voter turnout statistics';

-- ============================================================================
-- AGGREGATE TABLES (for performance optimization)
-- ============================================================================

-- Pre-aggregated results by municipality and party
CREATE TABLE agg_municipality_party_results (
    agg_id SERIAL PRIMARY KEY,
    election_key INTEGER NOT NULL REFERENCES dim_election(election_key),
    municipality_key INTEGER NOT NULL REFERENCES dim_municipality(municipality_key),
    party_key INTEGER NOT NULL REFERENCES dim_party(party_key),
    
    total_votes INTEGER DEFAULT 0,
    avg_vote_percentage NUMERIC(5,2),
    total_seats INTEGER DEFAULT 0,
    organs_contested INTEGER DEFAULT 0,
    organs_won INTEGER DEFAULT 0,
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(election_key, municipality_key, party_key)
);

CREATE INDEX idx_agg_muni_party_election ON agg_municipality_party_results(election_key);
CREATE INDEX idx_agg_muni_party_municipality ON agg_municipality_party_results(municipality_key);
CREATE INDEX idx_agg_muni_party_party ON agg_municipality_party_results(party_key);

COMMENT ON TABLE agg_municipality_party_results IS 'Pre-aggregated municipality-level party results';

-- Pre-aggregated district-level results
CREATE TABLE agg_district_results (
    agg_id SERIAL PRIMARY KEY,
    election_key INTEGER NOT NULL REFERENCES dim_election(election_key),
    district_key INTEGER NOT NULL REFERENCES dim_district(district_key),
    party_key INTEGER NOT NULL REFERENCES dim_party(party_key),
    
    total_votes INTEGER DEFAULT 0,
    total_seats INTEGER DEFAULT 0,
    vote_share NUMERIC(5,2),  -- Share of district votes
    municipalities_won INTEGER DEFAULT 0,
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(election_key, district_key, party_key)
);

CREATE INDEX idx_agg_dist_election ON agg_district_results(election_key);
CREATE INDEX idx_agg_dist_district ON agg_district_results(district_key);
CREATE INDEX idx_agg_dist_party ON agg_district_results(party_key);

COMMENT ON TABLE agg_district_results IS 'Pre-aggregated district-level results';

-- ============================================================================
-- BRIDGE TABLES (for many-to-many relationships in dimensions)
-- ============================================================================

-- Bridge table for coalition membership in dimensional model
CREATE TABLE bridge_coalition_party (
    bridge_id SERIAL PRIMARY KEY,
    coalition_party_key INTEGER NOT NULL REFERENCES dim_party(party_key),
    member_party_key INTEGER NOT NULL REFERENCES dim_party(party_key),
    is_lead_party BOOLEAN DEFAULT false,
    
    UNIQUE(coalition_party_key, member_party_key)
);

CREATE INDEX idx_bridge_coalition ON bridge_coalition_party(coalition_party_key);
CREATE INDEX idx_bridge_member ON bridge_coalition_party(member_party_key);

COMMENT ON TABLE bridge_coalition_party IS 'Bridge table for coalition-party relationships';

-- ============================================================================
-- VIEWS FOR COMMON ANALYTICAL QUERIES
-- ============================================================================

-- View: Complete result with all dimension attributes (denormalized for easy querying)
CREATE OR REPLACE VIEW vw_complete_results AS
SELECT 
    f.result_key,
    
    -- Election info
    e.election_year,
    e.election_type_name,
    e.election_date,
    e.election_description,
    
    -- Organ info
    o.organ_name,
    o.territorial_level,
    
    -- Geography info (coalesced for easy display)
    COALESCE(d.district_name, m.district_name, p.district_name) as district_name,
    COALESCE(m.municipality_name, p.municipality_name) as municipality_name,
    p.parish_name,
    
    -- Party info
    pt.party_acronym,
    pt.party_name,
    pt.is_coalition,
    pt.coalition_member_parties,
    
    -- Measures
    f.votes_obtained,
    f.vote_percentage,
    f.seats_obtained,
    f.is_winner,
    f.ranking_position
    
FROM fact_election_result f
JOIN dim_election e ON f.election_key = e.election_key
JOIN dim_organ o ON f.organ_key = o.organ_key
JOIN dim_party pt ON f.party_key = pt.party_key
LEFT JOIN dim_district d ON f.district_key = d.district_key
LEFT JOIN dim_municipality m ON f.municipality_key = m.municipality_key
LEFT JOIN dim_parish p ON f.parish_key = p.parish_key;

COMMENT ON VIEW vw_complete_results IS 'Denormalized view of results with all dimension attributes';

-- View: Turnout analysis
CREATE OR REPLACE VIEW vw_turnout_analysis AS
SELECT 
    t.turnout_key,
    e.election_year,
    e.election_type_name,
    o.organ_name,
    
    COALESCE(d.district_name, m.district_name, p.district_name) as district_name,
    COALESCE(m.municipality_name, p.municipality_name) as municipality_name,
    p.parish_name,
    
    t.registered_voters,
    t.votes_cast,
    t.abstentions,
    t.turnout_percentage,
    t.abstention_percentage,
    t.blank_percentage,
    t.null_percentage
    
FROM fact_turnout t
JOIN dim_election e ON t.election_key = e.election_key
JOIN dim_organ o ON t.organ_key = o.organ_key
LEFT JOIN dim_district d ON t.district_key = d.district_key
LEFT JOIN dim_municipality m ON t.municipality_key = m.municipality_key
LEFT JOIN dim_parish p ON t.parish_key = p.parish_key;

COMMENT ON VIEW vw_turnout_analysis IS 'Denormalized view of turnout statistics';

-- ============================================================================
-- POPULATE TIME DIMENSION
-- ============================================================================

-- Populate time dimension with dates from 2000 to 2030 (covers most elections)
INSERT INTO dim_time (time_key, full_date, year, quarter, month, month_name, 
                      day, day_of_week, day_name, is_weekend)
SELECT 
    TO_CHAR(d, 'YYYYMMDD')::INTEGER as time_key,
    d as full_date,
    EXTRACT(YEAR FROM d)::INTEGER as year,
    EXTRACT(QUARTER FROM d)::INTEGER as quarter,
    EXTRACT(MONTH FROM d)::INTEGER as month,
    TO_CHAR(d, 'Month') as month_name,
    EXTRACT(DAY FROM d)::INTEGER as day,
    EXTRACT(DOW FROM d)::INTEGER as day_of_week,
    TO_CHAR(d, 'Day') as day_name,
    CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) THEN true ELSE false END as is_weekend
FROM generate_series('2000-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) d;

COMMENT ON SCHEMA warehouse IS 'Data warehouse schema optimized for analytical queries';
