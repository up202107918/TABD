-- ============================================================================
-- STAGING SCHEMA FOR ETL PIPELINE
-- Advanced Topics in Databases - Practical Assignment
-- ============================================================================
-- This schema serves as a landing zone for raw data before transformation
-- and loading into the operational schema
-- ============================================================================

DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;

SET search_path TO staging, public;

-- ============================================================================
-- STAGING TABLES (Raw data as extracted from CSV files)
-- ============================================================================

-- Staging table for raw election results
CREATE TABLE stg_election_results (
    row_id SERIAL PRIMARY KEY,
    distrito VARCHAR(100),
    concelho VARCHAR(100),
    freguesia VARCHAR(200),
    orgao VARCHAR(100),  -- CM, AM, JF
    candidatura VARCHAR(200),  -- Party/Coalition name
    votos INTEGER,
    mandatos INTEGER,
    percentagem NUMERIC(5,2),
    
    -- Additional fields from official data
    numero_candidatura INTEGER,
    nome_candidato VARCHAR(200),
    lista_completa TEXT,
    
    -- ETL metadata
    source_file VARCHAR(500),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT false,
    error_message TEXT
);

CREATE INDEX idx_stg_results_distrito ON stg_election_results(distrito);
CREATE INDEX idx_stg_results_concelho ON stg_election_results(concelho);
CREATE INDEX idx_stg_results_processed ON stg_election_results(processed);

COMMENT ON TABLE stg_election_results IS 'Staging table for raw election results from CSV';

-- Staging table for turnout data
CREATE TABLE stg_turnout_data (
    row_id SERIAL PRIMARY KEY,
    distrito VARCHAR(100),
    concelho VARCHAR(100),
    freguesia VARCHAR(200),
    orgao VARCHAR(100),
    eleitores_inscritos INTEGER,
    votantes INTEGER,
    votos_validos INTEGER,
    votos_brancos INTEGER,
    votos_nulos INTEGER,
    
    -- ETL metadata
    source_file VARCHAR(500),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT false,
    error_message TEXT
);

CREATE INDEX idx_stg_turnout_distrito ON stg_turnout_data(distrito);
CREATE INDEX idx_stg_turnout_concelho ON stg_turnout_data(concelho);
CREATE INDEX idx_stg_turnout_processed ON stg_turnout_data(processed);

COMMENT ON TABLE stg_turnout_data IS 'Staging table for turnout/participation data';

-- Staging table for geographic boundaries (before loading into PostGIS)
CREATE TABLE stg_geographic_boundaries (
    row_id SERIAL PRIMARY KEY,
    boundary_type VARCHAR(20),  -- 'district', 'municipality', 'parish'
    code VARCHAR(10),
    name VARCHAR(200),
    parent_code VARCHAR(10),  -- For hierarchy
    geojson_data TEXT,  -- Raw GeoJSON before conversion to PostGIS geometry
    
    source_file VARCHAR(500),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT false,
    error_message TEXT
);

CREATE INDEX idx_stg_geo_type ON stg_geographic_boundaries(boundary_type);
CREATE INDEX idx_stg_geo_code ON stg_geographic_boundaries(code);
CREATE INDEX idx_stg_geo_processed ON stg_geographic_boundaries(processed);

COMMENT ON TABLE stg_geographic_boundaries IS 'Staging table for CAOP geographic boundaries';

-- Staging table for party/coalition mappings
CREATE TABLE stg_party_mapping (
    row_id SERIAL PRIMARY KEY,
    raw_name VARCHAR(200),  -- As appears in source data
    normalized_acronym VARCHAR(20),  -- Standardized acronym
    normalized_name VARCHAR(200),  -- Standardized full name
    is_coalition BOOLEAN DEFAULT false,
    coalition_members TEXT,  -- Comma-separated list if coalition
    
    manual_mapping BOOLEAN DEFAULT false,  -- true if manually added
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(raw_name)
);

CREATE INDEX idx_stg_party_raw_name ON stg_party_mapping(raw_name);

COMMENT ON TABLE stg_party_mapping IS 'Mapping table for normalizing party/coalition names';

-- ============================================================================
-- DATA QUALITY TABLES
-- ============================================================================

-- Table to track data quality issues
CREATE TABLE stg_data_quality_issues (
    issue_id SERIAL PRIMARY KEY,
    issue_type VARCHAR(50),  -- 'missing_value', 'invalid_format', 'orphan_record', etc.
    severity VARCHAR(20),  -- 'warning', 'error', 'critical'
    table_name VARCHAR(100),
    row_id INTEGER,
    column_name VARCHAR(100),
    issue_description TEXT,
    raw_value TEXT,
    suggested_fix TEXT,
    resolved BOOLEAN DEFAULT false,
    
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_note TEXT
);

CREATE INDEX idx_dq_severity ON stg_data_quality_issues(severity);
CREATE INDEX idx_dq_resolved ON stg_data_quality_issues(resolved);

COMMENT ON TABLE stg_data_quality_issues IS 'Tracks data quality issues found during ETL';

-- Table to track ETL runs
CREATE TABLE stg_etl_run_log (
    run_id SERIAL PRIMARY KEY,
    run_name VARCHAR(200),
    run_type VARCHAR(50),  -- 'full_load', 'incremental', 'refresh'
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20),  -- 'running', 'completed', 'failed'
    
    rows_extracted INTEGER,
    rows_staged INTEGER,
    rows_transformed INTEGER,
    rows_loaded INTEGER,
    rows_rejected INTEGER,
    
    error_message TEXT,
    notes TEXT
);

CREATE INDEX idx_etl_run_status ON stg_etl_run_log(status);
CREATE INDEX idx_etl_run_time ON stg_etl_run_log(start_time);

COMMENT ON TABLE stg_etl_run_log IS 'Logs all ETL pipeline executions';

-- ============================================================================
-- STAGING FUNCTIONS
-- ============================================================================

-- Function to clean and normalize municipality names
CREATE OR REPLACE FUNCTION normalize_municipality_name(raw_name VARCHAR)
RETURNS VARCHAR AS $$
BEGIN
    -- Remove extra spaces, standardize case
    RETURN TRIM(REGEXP_REPLACE(INITCAP(raw_name), '\s+', ' ', 'g'));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to extract district code from various formats
CREATE OR REPLACE FUNCTION extract_district_code(distrito_name VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    district_mapping JSONB := '{
        "Aveiro": "01",
        "Beja": "02",
        "Braga": "03",
        "Bragança": "04",
        "Castelo Branco": "05",
        "Coimbra": "06",
        "Évora": "07",
        "Faro": "08",
        "Guarda": "09",
        "Leiria": "10",
        "Lisboa": "11",
        "Portalegre": "12",
        "Porto": "13",
        "Santarém": "14",
        "Setúbal": "15",
        "Viana do Castelo": "16",
        "Vila Real": "17",
        "Viseu": "18",
        "Açores": "20",
        "Madeira": "30"
    }'::JSONB;
BEGIN
    RETURN district_mapping->>normalize_municipality_name(distrito_name);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- STAGING VALIDATION VIEWS
-- ============================================================================

-- View to identify records with missing required fields
CREATE OR REPLACE VIEW vw_stg_missing_data AS
SELECT 
    'stg_election_results' as table_name,
    row_id,
    CASE 
        WHEN distrito IS NULL THEN 'distrito'
        WHEN concelho IS NULL THEN 'concelho'
        WHEN candidatura IS NULL THEN 'candidatura'
        WHEN votos IS NULL THEN 'votos'
    END as missing_field
FROM stg_election_results
WHERE distrito IS NULL 
    OR concelho IS NULL 
    OR candidatura IS NULL 
    OR votos IS NULL;

COMMENT ON VIEW vw_stg_missing_data IS 'Identifies staging records with missing required fields';

-- View to identify potential duplicates
CREATE OR REPLACE VIEW vw_stg_potential_duplicates AS
SELECT 
    distrito,
    concelho,
    freguesia,
    orgao,
    candidatura,
    COUNT(*) as duplicate_count
FROM stg_election_results
GROUP BY distrito, concelho, freguesia, orgao, candidatura
HAVING COUNT(*) > 1;

COMMENT ON VIEW vw_stg_potential_duplicates IS 'Identifies potential duplicate records in staging';

COMMENT ON SCHEMA staging IS 'Staging area for ETL pipeline - raw data before transformation';
