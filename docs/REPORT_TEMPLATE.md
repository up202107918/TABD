# Technical Report: Election Analytics Platform for Portugal
## Advanced Topics in Databases - Practical Assignment

**Course**: Advanced Topics in Databases  
**Academic Year**: 2025/26  
**Institution**: FCUP (Faculdade de Ciências da Universidade do Porto)  
**Instructor**: Prof. Michel Ferreira  

**Group Members**:
- [Student 1 Name] - [Student Number] - [Contribution %]
- [Student 2 Name] - [Student Number] - [Contribution %]
- [Student 3 Name] - [Student Number] - [Contribution %]

**Date**: June 2026

---

## Abstract

A comprehensive database-backed system for analyzing Portuguese local elections, demonstrating advanced database concepts including normalized schemas, data warehousing, ETL pipelines, PL/pgSQL programming, PostGIS spatial integration, and web-based visualization.

**Keywords**: Election Analytics, PostgreSQL, PostGIS, Data Warehouse, ETL, D'Hondt Method, Spatial Databases, Flask

---

## 1. Introduction and Scope

### 1.1 Problem Statement

The goal of this project is to design and implement a database system capable of powering a comprehensive election analysis website for Portugal. The system must handle the complexity of Portuguese electoral data while providing efficient querying capabilities for analytical purposes.

### 1.2 Chosen Datasets

**Primary Dataset**: Autárquicas 2021 (Local Elections)
- Source: CNE (Comissão Nacional de Eleições)
- Coverage: 308 municipalities across 18 districts
- Electoral Organs: Câmara Municipal, Assembleia Municipal, Junta de Freguesia
- URL: https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip

**Spatial Dataset**: CAOP 2021 (Administrative Boundaries)
- Source: DGT (Direção-Geral do Território)
- Format: Shapefile (SHP)
- Projection: ETRS89/PT-TM06 (EPSG:3763)
- URL: https://www.dgterritorio.gov.pt/.../CAOP2021_SHP_AAD-ETRS89.zip

### 1.3 Scope Boundaries

**In Scope**:
- Complete 2021 local elections data
- District and municipality-level analysis
- Câmara Municipal results (primary focus)
- PostGIS spatial visualization
- D'Hondt seat allocation method
- Web-based interactive interface

**Out of Scope** (for this iteration):
- Historical multi-election comparison
- Detailed parish-level analysis for all parishes
- Real-time election night updates
- User authentication and personalization

---

## 2. Operational Schema Design

### 2.1 Design Rationale

The operational schema follows a fully normalized relational design (3NF) to:
1. Eliminate data redundancy
2. Ensure referential integrity
3. Support flexible territorial hierarchies
4. Accommodate future election types

### 2.2 Entity-Relationship Model

[INSERT ER DIAGRAM HERE]

**Key Design Decisions**:

1. **Territorial Hierarchy**:
   - Three-level hierarchy: District → Municipality → Parish
   - PostGIS geometry columns for spatial queries
   - Official INE codes as business keys

2. **Political Entities**:
   - Separate entities for parties and coalitions
   - Bridge table (coalition_member) for many-to-many relationship
   - Support for independent candidacies

3. **Candidacies as Central Entity**:
   - Links election, organ, territory, and political entity
   - Enables proper normalization of results
   - Supports queries at multiple territorial levels

4. **Results Separation**:
   - vote_result: Vote counts and percentages
   - seat_result: Mandate allocation
   - turnout: Participation statistics
   - Allows independent analysis of different metrics

### 2.3 Key Tables

**Core Tables**:
- `district`, `municipality`, `parish`: Geographic hierarchy with PostGIS geometries
- `election`, `election_type`, `electoral_organ`: Election structure
- `party`, `coalition`, `coalition_member`: Political entities
- `candidacy`: Central linking entity
- `vote_result`, `seat_result`, `turnout`: Election outcomes

**Summary Tables**:
- `party_municipality_summary`: Pre-computed aggregates

**Audit**:
- `audit_log`: Change tracking for critical operations

### 2.4 Constraints and Indexing

**Primary Keys**: Surrogate keys (SERIAL) for all entities

**Foreign Keys**: Strict referential integrity enforced

**Unique Constraints**:
- District/municipality/parish codes
- Party acronyms
- (election, organ, territory, party) combinations in candidacy

**Check Constraints**:
- votes_cast ≤ registered_voters
- valid_votes + blank_votes + null_votes = votes_cast
- Geographic level consistency (one of district/municipality/parish NOT NULL)

**Indexes**:
- B-tree indexes on all foreign keys
- GiST indexes on geometry columns
- Composite indexes for common join patterns
- Functional indexes on computed values

---

## 3. Data Warehouse Design

### 3.1 Dimensional Modeling Approach

The warehouse uses a **star schema** design optimized for OLAP queries and business intelligence.

### 3.2 Star Schema Diagram

[INSERT STAR SCHEMA DIAGRAM HERE]

### 3.3 Dimension Tables

**dim_time**: Temporal dimension (2000-2030)
- Grain: Daily
- Attributes: year, quarter, month, day, is_weekend

**dim_election**: Election characteristics
- Grain: Individual election event
- Attributes: type, date, year, description

**dim_organ**: Electoral organs
- Grain: Organ type
- Attributes: code, name, territorial_level

**Geographic Dimensions** (snowflake sub-schema):
- dim_district
- dim_municipality (references dim_district)
- dim_parish (references dim_municipality)
- Denormalized attributes for query performance

**dim_party**: Political entities
- Grain: Party or coalition
- Attributes: acronym, name, is_coalition, member_parties
- Denormalizes coalition membership for easier querying

### 3.4 Fact Tables

**fact_election_result** (main fact table)
- Grain: One row per candidacy (party × territory × organ × election)
- Measures: votes_obtained, vote_percentage, seats_obtained
- Derived measures: vote_seat_ratio, is_winner, ranking_position

**fact_turnout**
- Grain: One row per electoral contest (territory × organ × election)
- Measures: registered_voters, votes_cast, abstentions
- Derived measures: turnout_percentage, abstention_percentage

### 3.5 Aggregate Tables

**agg_municipality_party_results**
- Pre-computed municipality-level summaries
- Significantly faster than on-the-fly aggregation
- Refreshed via stored procedure

**agg_district_results**
- District-level roll-ups
- Supports drill-down navigation

### 3.6 Design Trade-offs

**Denormalization Decisions**:
- District/municipality names replicated in geographic dimensions
- Coalition member parties stored as text in dim_party
- Trade: Storage space vs. query performance
- Benefit: Eliminates joins for common queries

**Slowly Changing Dimensions**:
- Type 1 (overwrite): Party names, territory names
- Type 2 (historical): Not implemented (single election scope)
- Future: Add effective_date, expiry_date for multi-election support

---

## 4. ETL Pipeline

### 4.1 Architecture

**Three-Layer Approach**:
1. **Staging Layer**: Raw data landing zone
2. **Operational Layer**: Normalized relational schema
3. **Warehouse Layer**: Dimensional model

### 4.2 Staging Schema

**Tables**:
- `stg_election_results`: Raw vote and seat data
- `stg_turnout_data`: Participation statistics
- `stg_geographic_boundaries`: CAOP shapefiles
- `stg_party_mapping`: Name standardization

**Metadata Columns**:
- source_file: Traceability
- loaded_at: Timestamp
- processed: ETL status flag
- error_message: Quality issue tracking

### 4.3 Extract Phase

**Data Sources**:
1. CNE Official Spreadsheets (ZIP archive)
   - Format: Excel/CSV
   - Extraction: zipfile module, pandas
   
2. CAOP Shapefiles (ZIP archive)
   - Format: SHP + supporting files
   - Extraction: zipfile, Shapely/Fiona

**Challenges**:
- Large file downloads (100MB+)
- Encoding issues (UTF-8 vs. Windows-1252)
- Multiple file formats in single archive

**Solutions**:
- Resumable downloads with progress tracking
- Explicit encoding specification
- File type detection and routing

### 4.4 Transform Phase

**Data Cleaning Operations**:

1. **Name Standardization**:
   - Problem: "Porto" vs "PORTO" vs "Porto   "
   - Solution: `normalize_municipality_name()` function
   - Approach: TRIM, INITCAP, regex whitespace collapse

2. **Code Reconciliation**:
   - Problem: Election data uses names, CAOP uses codes
   - Solution: Mapping table + fuzzy matching
   - Approach: Levenshtein distance for close matches

3. **Missing Value Handling**:
   - Votes: Default to 0 (genuine no votes)
   - Percentages: Calculate from totals
   - Geography: Flag for manual review

4. **Party Name Mapping**:
   - Problem: "PPD/PSD" vs "PSD" vs "Partido Social Democrata"
   - Solution: stg_party_mapping lookup table
   - Approach: Manual curation + pattern matching

5. **Coalition Detection**:
   - Pattern: Names containing "/" or "-"
   - Parsing: Split into constituent parties
   - Creation: coalition + coalition_member entries

**Validation Rules**:
- votes_cast = valid + blank + null
- Percentage totals = 100% (within tolerance)
- All municipalities exist in CAOP
- No orphan candidacies

### 4.5 Load Phase

**Dependency Resolution**:
```
1. Districts (no dependencies)
2. Municipalities (→ districts)
3. Parishes (→ municipalities)
4. Parties (no dependencies)
5. Elections, Organs (no dependencies)
6. Coalitions (→ elections)
7. Coalition Members (→ coalitions, parties)
8. Candidacies (→ all of the above)
9. Results (→ candidacies)
```

**Transaction Management**:
- Batch commits (1000 rows)
- Savepoints for rollback
- Foreign key constraint deferred until commit

**Performance Optimizations**:
- COPY instead of INSERT for bulk data
- Temporary indexes disabled during load
- ANALYZE after major loads

### 4.6 Warehouse Population

**Dimension Population**:
- Extract-Load from operational schema
- Denormalize as needed
- Generate surrogate keys

**Fact Population**:
- Join operational tables
- Calculate derived measures
- Assign dimension foreign keys

**Refresh Strategy**:
- Full refresh (truncate and reload)
- Future: Incremental updates via change tracking

### 4.7 Data Quality Monitoring

**stg_data_quality_issues Table**:
- Issue type: missing_value, format_error, orphan_record
- Severity: warning, error, critical
- Auto-detected during transform
- Manual review interface (not implemented)

**ETL Run Logging**:
- stg_etl_run_log: Complete audit trail
- Metrics: rows extracted/staged/transformed/loaded/rejected
- Error capture with stack traces
- Performance timing

---

## 5. SQL Functions, PL/pgSQL, and Triggers

### 5.1 SQL Functions

**Function 1: calculate_vote_percentage**
```sql
FUNCTION calculate_vote_percentage(p_candidacy_id INTEGER) RETURNS NUMERIC
```
- Purpose: Calculate vote percentage for a candidacy
- Logic: (candidacy votes / total valid votes) × 100
- Usage: Data validation, ad-hoc queries

**Function 2: get_party_performance_in_municipality**
```sql
FUNCTION get_party_performance_in_municipality(...) 
    RETURNS TABLE (party_name, total_votes, avg_percentage, ...)
```
- Purpose: Comprehensive party metrics for a municipality
- Returns: Aggregated statistics across all organs
- Usage: Municipality detail page, party comparison

**Function 3: get_top_parties**
```sql
FUNCTION get_top_parties(...) 
    RETURNS TABLE (ranking, party_acronym, votes, ...)
```
- Purpose: Top N parties by votes in a territory
- Features: Configurable limit, multiple ranking methods
- Usage: Result summaries, leaderboards

### 5.2 PL/pgSQL Routines

**Routine 1: allocate_seats_dhondt**
```sql
FUNCTION allocate_seats_dhondt(
    p_election_id, p_organ_id, p_municipality_id, p_total_seats
) RETURNS TABLE (candidacy_id, party_name, votes, seats_allocated)
```

**Purpose**: Implement the D'Hondt method for proportional seat allocation

**Algorithm**:
1. Initialize all parties with 0 seats
2. Calculate quotient for each party: votes / (seats + 1)
3. Assign seat to party with highest quotient
4. Recalculate quotients with updated seat counts
5. Repeat until all seats allocated

**Complexity**: O(seats × parties)

**Validation**: Results match official CNE seat allocations

**Example Output**:
```
party_name       votes   seats_allocated
PS               12,450  4
PSD              10,230  3
CDU              3,120   1
Others           2,500   0
```

**Routine 2: refresh_party_municipality_summary**
```sql
PROCEDURE refresh_party_municipality_summary(p_election_id)
```

**Purpose**: Update pre-computed summary tables

**Logic**:
1. Delete existing summaries for election
2. Aggregate votes/seats from candidacy + results
3. Insert into party_municipality_summary
4. COMMIT transaction

**Benefits**:
- 10x faster queries for common aggregations
- Reduced load on operational tables
- Simplified application queries

**Usage**: Run after ETL completion or result updates

### 5.3 Triggers

**Trigger 1: trg_turnout_percentages**
```sql
CREATE TRIGGER trg_turnout_percentages
    BEFORE INSERT OR UPDATE ON turnout
    FOR EACH ROW
    EXECUTE FUNCTION trg_calculate_turnout()
```

**Purpose**: Automatically calculate turnout percentages

**Logic**:
- turnout_% = (votes_cast / registered_voters) × 100
- abstention_% = 100 - turnout_%
- blank_% = (blank_votes / votes_cast) × 100
- null_% = (null_votes / votes_cast) × 100

**Benefit**: Eliminates manual calculation, ensures consistency

**Trigger 2: trg_vote_percentages**
```sql
CREATE TRIGGER trg_vote_percentages
    BEFORE INSERT OR UPDATE ON vote_result
    FOR EACH ROW
    EXECUTE FUNCTION trg_calculate_vote_percentage()
```

**Purpose**: Auto-calculate vote percentages

**Dependency**: Requires corresponding turnout record

**Trigger 3: trg_audit_candidacy / trg_audit_vote_result**
```sql
CREATE TRIGGER trg_audit_*
    AFTER INSERT OR UPDATE OR DELETE ON *
    FOR EACH ROW
    EXECUTE FUNCTION trg_audit_log()
```

**Purpose**: Comprehensive audit trail

**Captured Data**:
- Operation type (INSERT/UPDATE/DELETE)
- Timestamp
- Old and new values (JSONB)
- User (if available)

**Uses**: Compliance, debugging, data lineage

---

## 6. Analytical SQL Queries

### 6.1 Window Functions

[Include actual query examples and explanations]

**Query 1: Party Rankings with Running Totals**
- Window functions: ROW_NUMBER(), RANK(), SUM() OVER, PERCENT_RANK()
- Use case: Ranking parties within municipalities
- Key insight: [Describe findings]

**Query 2: District Comparison with LAG/LEAD**
- Window functions: AVG() OVER, LAG(), LEAD()
- Use case: Compare municipality to district average
- Key insight: [Describe findings]

**Query 3: Turnout Analysis with NTILE**
- Window functions: DENSE_RANK(), NTILE(), Moving AVG
- Use case: Quartile analysis of turnout
- Key insight: [Describe findings]

### 6.2 GROUP BY ROLLUP

**Query 4: Hierarchical Aggregation**
- Hierarchy: District → Municipality → Party
- Subtotals at each level
- Use case: Drill-down reports
- Key insight: [Describe findings]

### 6.3 GROUP BY CUBE

**Query 5: Multi-dimensional Analysis**
- Dimensions: District × Party × Organ
- All combinations of aggregations
- Use case: Pivot table-style analysis
- Key insight: [Describe findings]

### 6.4 Advanced Aggregates

**Query 6: Complex Aggregations**
- Techniques: STRING_AGG, ARRAY_AGG, JSON_AGG, FILTER
- Use case: Flexible result formatting
- Key insight: [Describe findings]

### 6.5 D'Hondt Method Implementation

[Include query example and validation]

---

## 7. Frontend Implementation

### 7.1 Technology Stack

- **Backend**: Flask (Python 3.9+)
- **Database Driver**: psycopg2
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **Maps**: Leaflet.js + OpenStreetMap tiles
- **Charts**: Chart.js
- **Geometry**: PostGIS ST_AsGeoJSON()

### 7.2 Application Architecture

**Routes**:
- `/` - Homepage with statistics and national map
- `/districts` - List all districts
- `/district/<id>` - District detail with municipalities
- `/municipality/<id>` - Detailed results with charts
- `/analytics` - Dashboard with comparisons
- `/api/map/*` - GeoJSON endpoints
- `/api/charts/*` - Chart data endpoints

### 7.3 Database Integration

**Query Pattern**:
```python
def execute_query(query: str, params: tuple = None) -> List[Dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]
```

**Key Features**:
- Connection pooling (future enhancement)
- Parameterized queries (SQL injection prevention)
- RealDictCursor for easy JSON serialization
- Error handling with logging

### 7.4 Spatial Visualization

**Map Integration**:
1. Query: ST_AsGeoJSON(geometry) from PostGIS
2. API: JSON endpoint with GeoJSON FeatureCollection
3. Frontend: Leaflet.js renders GeoJSON
4. Interaction: Click → drill down to next level

**Choropleth Coloring**:
- Metric: Average turnout percentage
- Scale: 6-color gradient (red to green)
- Interactivity: Hover tooltips, click navigation

### 7.5 Visualizations

**Chart Types**:
1. **Pie Chart**: Vote distribution by party
2. **Bar Chart**: Vote comparison across parties
3. **Progress Bars**: Visual vote percentages

**Data Flow**:
1. Flask route queries database
2. Results passed to template as JSON
3. JavaScript extracts data
4. Chart.js renders visualization

---

## 8. Key Findings and Insights

### 8.1 Turnout Analysis

[Add actual findings from data]

### 8.2 Party Performance

[Add actual findings from data]

### 8.3 Geographic Patterns

[Add actual findings from data]

### 8.4 D'Hondt Impact

[Analyze proportionality vs. majoritarian outcomes]

---

## 9. Known Limitations

### 9.1 Data Completeness

- Parish-level data partially implemented
- Single election year (no historical comparison)
- Some coalition member data missing

### 9.2 Performance

- Large geometries slow map rendering
- No query result caching
- Warehouse queries could use materialized views

### 9.3 Functionality

- No authentication/authorization
- Limited export capabilities
- Manual ETL execution (no scheduling)

---

## 10. Future Enhancements

### 10.1 Short Term

1. Complete parish-level implementation
2. Add materialized views for complex queries
3. Implement query result caching
4. Add CSV export functionality

### 10.2 Long Term

1. Multi-election support with historical trends
2. Predictive modeling with machine learning
3. Real-time updates during election night
4. Mobile-optimized responsive design
5. API documentation with Swagger
6. Advanced spatial queries (nearest neighbor, clustering)

---

## 11. Team Contributions

### Individual Contributions

**[Student 1 Name]**:
- Database schema design (operational + warehouse)
- SQL functions and PL/pgSQL implementation
- Documentation and report writing
- Contribution: [X]%

**[Student 2 Name]**:
- ETL pipeline implementation
- Data cleaning and validation
- Testing and quality assurance
- Contribution: [Y]%

**[Student 3 Name]**:
- Web application development
- Frontend design and visualizations
- PostGIS integration
- Contribution: [Z]%

### Collaboration Methods

- Version control: Git with feature branches
- Communication: [Slack/Teams/WhatsApp]
- Meetings: [Weekly/Bi-weekly] sessions
- Task tracking: [Trello/GitHub Issues]

---

## 12. Conclusion

This project successfully demonstrates the application of advanced database concepts to a real-world problem. The system effectively combines normalized relational design, dimensional modeling, complex SQL, spatial databases, and web visualization to create a comprehensive election analytics platform.

**Key Achievements**:
- ✅ Fully normalized operational schema with referential integrity
- ✅ Star schema warehouse optimized for analytics
- ✅ Rerunnable ETL pipeline with data quality monitoring
- ✅ D'Hondt method correctly implemented and validated
- ✅ Advanced SQL: window functions, ROLLUP, CUBE, aggregates
- ✅ PostGIS integration with interactive maps
- ✅ Functional web application with visualizations

**Learning Outcomes**:
- Deep understanding of database design trade-offs
- Practical experience with ETL challenges
- Proficiency in advanced SQL constructs
- Integration of spatial and relational databases
- Full-stack development with database focus

---

## References

1. Comissão Nacional de Eleições. (2021). *Eleições Autárquicas 2021 - Resultados Oficiais*. Retrieved from https://www.cne.pt/

2. Direção-Geral do Território. (2021). *Carta Administrativa Oficial de Portugal (CAOP)*. Retrieved from https://www.dgterritorio.gov.pt/

3. PostgreSQL Global Development Group. (2024). *PostgreSQL 16 Documentation*. https://www.postgresql.org/docs/16/

4. PostGIS Project Steering Committee. (2024). *PostGIS 3.4 Manual*. https://postgis.net/docs/manual-3.4/

5. D'Hondt, V. (1882). *Système pratique et raisonné de représentation proportionnelle*. Brussels.

6. Kimball, R., & Ross, M. (2013). *The Data Warehouse Toolkit* (3rd ed.). Wiley.

7. Elmasri, R., & Navathe, S.B. (2015). *Fundamentals of Database Systems* (7th ed.). Pearson.

---

## Appendices

### Appendix A: Complete ER Diagrams

[INSERT OPERATIONAL SCHEMA ER DIAGRAM]

[INSERT WAREHOUSE STAR SCHEMA DIAGRAM]

### Appendix B: Sample SQL Queries

[Include complete text of key analytical queries]

### Appendix C: API Documentation

[Document REST endpoints]

### Appendix D: Installation Guide

[Detailed step-by-step installation instructions]

### Appendix E: Screenshots

[Include application screenshots]

---

**End of Report**
