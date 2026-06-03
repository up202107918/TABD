-- Drop analytical views before sql/04 (PostgreSQL cannot rename columns via CREATE OR REPLACE VIEW).
SET search_path TO operational, warehouse, public;

DROP VIEW IF EXISTS analytical_query_8_cross_district_comparison CASCADE;
DROP VIEW IF EXISTS analytical_query_6_advanced_aggregates CASCADE;
DROP VIEW IF EXISTS analytical_query_5_cube_multidimensional CASCADE;
DROP VIEW IF EXISTS analytical_query_4_rollup_hierarchical CASCADE;
DROP VIEW IF EXISTS analytical_query_3_turnout_analysis CASCADE;
DROP VIEW IF EXISTS analytical_query_2_district_comparison CASCADE;
DROP VIEW IF EXISTS analytical_query_1_party_rankings CASCADE;
