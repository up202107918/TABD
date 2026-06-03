# Election Analytics Platform for Portugal

Advanced Topics in Databases — practical assignment (FCUP).  
Database-centred system for Portuguese local election analysis: PostgreSQL/PostGIS, staging ETL, star-schema warehouse, analytical SQL, and a thin Flask frontend.

**Team:** Amos Ehiomone Uwamusi, Sérgio Teixeira Cardoso, Kamil Tasarz

---

## Current status (June 2026)

| Area | Status |
|------|--------|
| DB schemas (`sql/01`–`05`) | Ready |
| ETL MVP (Autárquicas 2021, CM, municipality) | **Done** — [etl/README.md](etl/README.md) |
| Web app (maps, tables, charts, election selector) | **Done** — [app/](app/) |
| Warehouse facts + operational load | **Done** |
| Report, slides, ER diagrams, ETL reconciliation doc | **Open** — [todo.md](todo.md) |

Backlog and optional ETL extensions: **[todo.md](todo.md)**.

---

## Architecture

```
TABD/
├── sql/                 # Schemas, functions/triggers, analytical queries
├── etl/                 # ETL pipeline (run_etl.py, pipeline/)
├── app/                 # Flask + templates (psycopg2, Leaflet, Chart.js)
├── docs/                # Report, ER diagrams (deliverables)
└── todo.md              # Project backlog
```

---

## Prerequisites

- PostgreSQL **14+** with **PostGIS**
- Python **3.9+**
- Virtual environment recommended (`.venv`)

---

## Setup

### 1. Database

```powershell
createdb election_analytics
psql -U postgres -d election_analytics -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

Load schemas (order matters):

```powershell
psql -U postgres -d election_analytics -f sql/01_operational_schema.sql
psql -U postgres -d election_analytics -f sql/02_warehouse_schema.sql
psql -U postgres -d election_analytics -f sql/03_functions_triggers.sql
psql -U postgres -d election_analytics -f sql/05_staging_schema.sql
```

- `sql/04_analytical_queries.sql` — run manually for demos / report (not part of ETL).
- `sql/06_sample_data.sql` — **validation queries only**, not seed data.

### 2. Python

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### 3. Connection

Set environment variables (or edit `etl/config.py`):

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="election_analytics"
$env:DB_USER="postgres"
$env:DB_PASSWORD="your_password"
```

`app/app.py` imports `DB_CONFIG` from `etl/config.py`.

### 4. ETL (full load)

See **[etl/README.md](etl/README.md)** for details.

```powershell
cd etl
..\.venv\Scripts\python.exe -m pipeline.download_caop
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2021 --mode full
```

### 5. Web application

```powershell
cd app
..\.venv\Scripts\python.exe app.py
```

Open **http://localhost:8000** (default port from `PORT` env or 8000).

Use the navbar to select **election** and **municipality**; URLs carry `?election_id=...`.

---

## Database overview

### Operational (`operational`)

Normalized model: territories, elections, organs, parties/coalitions, candidacies, vote results, turnout, optional `seat_result`, PostGIS geometries.

### Staging (`staging`)

`stg_election_results`, `stg_turnout_data`, `stg_etl_run_log`, quality-issue table (for future use).

### Warehouse (`warehouse`)

Star schema: `dim_*`, `fact_election_result`, `fact_turnout`. Aggregate tables `agg_*` exist in schema but are **not populated** in the MVP load (see [todo.md](todo.md)).

### SQL programming

Functions, PL/pgSQL, and triggers in `sql/03_functions_triggers.sql` (e.g. D'Hondt, turnout percentages, summary refresh). Analytical examples in `sql/04_analytical_queries.sql`.

---

## Web application

- **Stack:** Flask, psycopg2 (explicit SQL, no ORM), Bootstrap 5, Leaflet, Chart.js  
- **Routes:** home map, districts, municipality detail, analytics dashboard  
- **API:** GeoJSON districts/municipalities, party comparison JSON  
- **Requirement:** election + territorial unit selection — implemented via query string and navbar selectors  

---

## Data sources

| Source | Use |
|--------|-----|
| [CNE Autárquicas 2021](https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip) | Election results (in `etl/data/2021al_mapa_oficial/`) |
| [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) | Boundaries (`etl/data/caop/`, auto-download helper) |

---

## Documentation map

| File | Purpose |
|------|---------|
| [README.md](README.md) | This file — project setup |
| [etl/README.md](etl/README.md) | ETL pipeline, modes, sanity SQL |
| [etl/data/README.md](etl/data/README.md) | Data folder layout |
| [etl/data/caop/README.md](etl/data/caop/README.md) | Boundary files |
| [etl/docs/source_inventory_2021.md](etl/docs/source_inventory_2021.md) | Which CNE files are parsed |
| [todo.md](todo.md) | Remaining work (ETL extensions, report, etc.) |

---

## Known MVP limitations

- Single configured dataset: **2021** local elections, organ **CM**, **municipality** level (no parishes in ETL).  
- **seat_result** and **warehouse agg_*** not loaded.  
- CAOP fallback GeoJSON covers **continent**; islands may lack geometry until official shapefiles are added.  
- No authentication; batch ETL only (not live election night).  

Details and future tasks: **[todo.md](todo.md)**.

---

## Assignment deliverables (checklist)

- [ ] `docs/report.pdf`  
- [ ] `docs/er_diagrams/`  
- [ ] `slides/`  
- [ ] `docs/etl_reconciliation.md` (CNE ↔ CAOP)  

---

**Last updated:** June 2026
