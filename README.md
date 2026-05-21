# Election Analytics Platform for Portugal
## Advanced Topics in Databases - Practical Assignment

A comprehensive database-backed system for analyzing Portuguese local elections (Autárquicas 2021), featuring PostgreSQL/PostGIS, data warehousing, ETL pipelines, and an interactive web frontend.

---

## 📋 Project Overview

This project implements a complete election analytics platform with:

- **Normalized operational database** for election data storage
- **Star schema data warehouse** for analytical queries
- **ETL pipeline** for loading and cleaning official datasets
- **Advanced SQL** including D'Hondt method, window functions, ROLLUP, and CUBE
- **PostGIS integration** for spatial data and visualization
- **Flask web application** with interactive maps and charts

---

## 🏗️ Architecture

```
election_analytics_platform/
├── sql/                          # Database schemas and queries
│   ├── 01_operational_schema.sql # Normalized operational schema
│   ├── 02_warehouse_schema.sql   # Star schema data warehouse
│   ├── 03_functions_triggers.sql # SQL functions, PL/pgSQL, triggers
│   ├── 04_analytical_queries.sql # Advanced analytical queries
│   └── 05_staging_schema.sql     # ETL staging area
├── etl/                          # ETL pipeline
│   ├── config.py                 # Configuration settings
│   └── etl_pipeline.py           # Main ETL orchestration
├── app/                          # Flask web application
│   ├── app.py                    # Main Flask application
│   ├── templates/                # HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── municipality_detail.html
│   │   └── ...
│   └── static/                   # Static assets (CSS, JS, images)
├── docs/                         # Documentation
│   ├── report.pdf                # Technical report
│   └── er_diagrams/              # Entity-relationship diagrams
├── data/                         # Data directory (created by ETL)
│   ├── downloads/                # Downloaded source data
│   ├── extracted/                # Extracted datasets
│   └── logs/                     # ETL logs
└── README.md                     # This file
```

---



### Prerequisites

- **PostgreSQL 14+** with PostGIS extension
- **Python 3.9+**
- **Git** (for cloning the repository)

### Installation

1. **Clone the repository** (or extract the submission archive)
   ```bash
   cd tabd
   ```

2. **Create PostgreSQL database**
   ```bash
   createdb election_analytics
   psql election_analytics -c "CREATE EXTENSION IF NOT EXISTS postgis;"
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure database connection**
   
   Edit `etl/config.py` or set environment variables:
   ```bash
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_NAME=election_analytics
   export DB_USER=postgres
   export DB_PASSWORD=your_password
   ```

5. **Initialize database schemas**
   ```bash
   psql election_analytics < sql/01_operational_schema.sql
   psql election_analytics < sql/02_warehouse_schema.sql
   psql election_analytics < sql/03_functions_triggers.sql
   psql election_analytics < sql/04_analytical_queries.sql
   psql election_analytics < sql/05_staging_schema.sql
   psql election_analytics < sql/06_sample_data.sql
   ```

6. **Run ETL pipeline**
   ```bash
   cd etl
   python etl_pipeline.py
   ```

7. **Launch web application**
   ```bash
   cd app
   python app.py
   ```

8. **Open browser**
   
   Navigate to: `http://localhost:5000`

---

## 📊 Database Schemas

### Operational Schema

Normalized relational design covering:

- **Territorial hierarchy**: Districts → Municipalities → Parishes
- **Elections and electoral organs**: Election types, specific elections, organs being elected
- **Political entities**: Parties, coalitions, coalition membership
- **Candidacies**: Party/coalition candidacies for specific organs in specific territories
- **Results**: Vote counts, seat allocations, turnout statistics

**Key tables:**
- `district`, `municipality`, `parish` (with PostGIS geometries)
- `election`, `electoral_organ`
- `party`, `coalition`, `coalition_member`
- `candidacy`, `vote_result`, `seat_result`, `turnout`

### Data Warehouse Schema

Star schema optimized for analytics:

**Dimension tables:**
- `dim_time`: Temporal dimension for time-based analysis
- `dim_election`: Election characteristics
- `dim_organ`: Electoral organs/offices
- `dim_district`, `dim_municipality`, `dim_parish`: Geographic hierarchy
- `dim_party`: Political parties and coalitions (including denormalized coalition members)

**Fact tables:**
- `fact_election_result`: Election results by party/territory/organ
- `fact_turnout`: Voter turnout statistics

**Aggregate tables:**
- `agg_municipality_party_results`: Pre-computed municipality-level summaries
- `agg_district_results`: Pre-computed district-level summaries

---

## 🔧 SQL Functions & Triggers

### SQL Functions

1. **calculate_vote_percentage**: Computes vote percentage for a candidacy
2. **get_party_performance_in_municipality**: Returns comprehensive party metrics
3. **get_top_parties**: Gets top N parties by votes in a territory

### PL/pgSQL Routines

1. **allocate_seats_dhondt**: D'Hondt method for proportional seat allocation
2. **refresh_party_municipality_summary**: Updates pre-computed summary tables
3. **calculate_turnout_percentages**: Batch calculation of turnout statistics

### Triggers

1. **trg_turnout_percentages**: Auto-calculates turnout percentages on INSERT/UPDATE
2. **trg_vote_percentages**: Auto-calculates vote percentages
3. **trg_audit_candidacy/trg_audit_vote_result**: Audit logging for critical tables

---

## 📈 Analytical SQL Features

### Window Functions (3+ queries)

- **Query 1**: Party rankings with running totals and percentile ranks
- **Query 2**: District comparison with LAG/LEAD for sequential analysis
- **Query 3**: Turnout analysis with DENSE_RANK, NTILE, moving averages

### GROUP BY ROLLUP (1+ query)

- **Query 4**: Hierarchical aggregation (District → Municipality → Party)

### GROUP BY CUBE (1+ query)

- **Query 5**: Multi-dimensional analysis (District × Party × Organ)

### Advanced Aggregates (1+ query)

- **Query 6**: STRING_AGG, ARRAY_AGG, JSON_AGG, FILTER clause demonstrations

### D'Hondt Method

- **Function**: `allocate_seats_dhondt` - Full implementation
- **Demo Function**: `demonstrate_dhondt` - Step-by-step visualization

---

## 🗺️ PostGIS Integration

### Spatial Features

- Official CAOP administrative boundaries loaded as PostGIS geometries
- District, municipality, and parish-level geometries
- GeoJSON API endpoints for web map integration
- Interactive Leaflet maps with drill-down navigation

### Map Functionality

- **District-level map**: Colored by average turnout, clickable for details
- **Municipality drill-down**: Click district to see municipalities
- **Result integration**: Maps display election winners and key statistics

---

## 🌐 Web Application

### Technology Stack

- **Backend**: Flask (Python)
- **Database**: psycopg2 for PostgreSQL connectivity
- **Frontend**: Bootstrap 5, Leaflet.js, Chart.js
- **Maps**: Leaflet with OpenStreetMap tiles
- **Charts**: Chart.js for vote distribution and comparisons

### Features

1. **Homepage**: Overview statistics and national map
2. **District browsing**: List all districts with summary statistics
3. **District detail**: Municipality list and party performance
4. **Municipality detail**: Detailed results with tables and charts
5. **Analytics dashboard**: Comparative visualizations
6. **API endpoints**: GeoJSON for maps, JSON for charts

---

## 📦 Data Sources

### Official Sources

1. **CNE (Comissão Nacional de Eleições)**
   - Autárquicas 2021 official results
   - URL: https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip

2. **DGT (Direção-Geral do Território)**
   - CAOP 2021 administrative boundaries
   - URL: https://www.dgterritorio.gov.pt/...CAOP2021_SHP_AAD-ETRS89.zip

### ETL Process

1. **Extract**: Download and extract ZIP archives
2. **Stage**: Load raw CSV data into staging schema
3. **Transform**: Clean, normalize, validate data
4. **Load**: Insert into operational schema with referential integrity
5. **Warehouse**: Populate dimensional model from operational data

---

## 🧪 Testing & Validation

### Data Quality Checks

- Missing value detection in staging
- Duplicate record identification
- Referential integrity validation
- Geographic code reconciliation with CAOP

### Query Validation

- Compare D'Hondt results against official seat allocations
- Verify turnout calculations against source data
- Test window function rankings
- Validate ROLLUP/CUBE totals

---

## 📖 Documentation

### Report Contents

The technical report (`docs/report.pdf`) covers:

1. Problem scope and data sources
2. Operational schema design rationale
3. Data warehouse dimensional model
4. ETL pipeline and data cleaning decisions
5. Functions, PL/pgSQL routines, and triggers
6. Analytical queries and key findings
7. Frontend implementation and visualizations
8. Known limitations and future enhancements
9. Team contributions

### ER Diagrams

Entity-relationship diagrams available in `docs/er_diagrams/`:

- Operational schema ER diagram
- Data warehouse star schema
- ETL data flow diagram

---

## ⚙️ Configuration

### Database Settings

Edit `etl/config.py`:

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'election_analytics',
    'user': 'net',
    'password': 'your_password'
}
```

### ETL Settings

```python
ETL_CONFIG = {
    'batch_size': 1000,      # Batch insert size
    'max_retries': 3,        # Retry attempts for failures
    'log_level': 'INFO'      # Logging verbosity
}
```

### Flask Settings

In `app/app.py`:

```python
app.config['SECRET_KEY'] = 'change-in-production'
app.run(debug=True, host='0.0.0.0', port=5000)
```

---

## 🔍 Known Limitations

1. **Data Completeness**: Parish-level data not fully implemented (focus on district/municipality)
2. **Historical Comparison**: Single election year (2021) - framework supports multiple elections
3. **Geometry Optimization**: Large geometries may impact map performance
4. **Real-time Updates**: System designed for batch processing, not live updates
5. **Authentication**: No user authentication (demonstration system)

---

## 🎯 Future Enhancements

1. **Multi-election support**: Add historical elections for trend analysis
2. **Parish-level detail**: Complete parish data integration
3. **Materialized views**: Pre-compute complex aggregations
4. **Advanced visualizations**: Heat maps, flow diagrams, time-series
5. **Export functionality**: CSV/Excel export of query results
6. **API documentation**: RESTful API with Swagger/OpenAPI specs

---

## 👥 Team & Contributions

-  Amos Ehiomone Uwamusi
-  Sérgio Teixeira Cardoso


**Example:**
- **Member 1**: Database schema design, SQL functions, documentation
- **Member 2**: ETL pipeline implementation, data cleaning, testing
- **Member 3**: Web application development, frontend design, visualizations

---

## 📜 License & Attribution

**Academic Project**: FCUP Advanced Topics in Databases 2025/26

**Data Sources:**
- CNE - Comissão Nacional de Eleições
- DGT - Direção-Geral do Território

**Technologies:**
- PostgreSQL with PostGIS
- Python with Flask, psycopg2, pandas
- Bootstrap, Leaflet.js, Chart.js

---

## 📞 Support

For questions or issues:

1. Check the technical report in `docs/report.pdf`
2. Review SQL schema comments
3. Examine ETL logs in `data/logs/`
4. Contact the development team

---

## 🙏 Acknowledgments

- Prof. Michel Ferreira - Course instructor
- CNE and DGT - Official data providers
- PostgreSQL and PostGIS communities
- Flask and Python ecosystem contributors

---

**Last Updated**: June 2026  
**Version**: 1.0  
**Assignment**: Advanced Topics in Databases Practical Assignment
