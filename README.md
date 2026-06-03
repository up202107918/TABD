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
| Cross-election compare (2017 vs 2021 on `/analytics`) | **Done** — `/api/charts/election_comparison` |
| Warehouse facts + operational load | **Done** |
| Report, slides | **Open** — [todo.md](todo.md) |
| ETL reconciliation (`docs/etl_reconciliation.md`) | **Done** |
| Reproducibility guide (`docs/reproducibility.md`) | **Done** |
| ER diagrams (`docs/er_diagrams/`) | **Done** |

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

**Two election years (e.g. 2017 + 2021):** load both via ETL ([etl/README.md](etl/README.md)), then open **/analytics** for the cross-year comparison chart, or call `GET /api/charts/election_comparison?election_id_a=…&election_id_b=…`.

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

- **Stack:** Flask, psycopg2 (explicit SQL, no ORM), Bootstrap 5, Leaflet, Chart.js, **Matplotlib** (server PNG)  
- **Routes:** home map, districts, municipality detail, analytics dashboard  
- **API:** GeoJSON districts/municipalities; `party_comparison` (one year); `election_comparison` (two years, CM national totals)  
- **Matplotlib:** `GET /analytics/chart.png?metric=votes|seats&election_id=…` — SQL → PNG; export: `python scripts/export_charts.py`  
- **Requirement:** election + territorial unit selection — navbar + query string; cross-year compare on `/analytics` when ≥2 elections in DB  

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
| [docs/etl_reconciliation.md](docs/etl_reconciliation.md) | CNE ↔ CAOP reconciliation (§5.2) |
| [docs/reproducibility.md](docs/reproducibility.md) | End-to-end rebuild guide (§9) |
| [docs/cross_election_comparison.md](docs/cross_election_comparison.md) | 2017 vs 2021 API and `/analytics` UI |
| [docs/sql_outputs/README.md](docs/sql_outputs/README.md) | Regenerate analytical demo outputs |
| [todo.md](todo.md) | Remaining work (ETL extensions, report, etc.) |

---

## Known MVP limitations

- ETL MVP: local elections **2017 / 2021** (`aut_2017`, `aut_2021`), organ **CM**, **municipality** level (no parishes in ETL).  
- **warehouse agg_*** not populated after load.  
- ~50 municipalities in CNE mapa_2 may be absent from mapa_1 ETL (no votes / seats in DB).  
- CAOP fallback GeoJSON covers **continent**; islands may lack geometry until official shapefiles are added.  
- If turnout shows **0% / N/A** after an older ETL run: `python scripts/fix_turnout_percentages.py` (or re-run `run_etl.py --mode reload-operational`). Bulk load skips triggers, so percentages must be computed explicitly.  
- No authentication; batch ETL only (not live election night).  

Details and future tasks: **[todo.md](todo.md)**.

---

## Assignment deliverables (checklist)

- [ ] `docs/report.pdf`  
- [x] `docs/er_diagrams/` — operational + warehouse PNG (pgAdmin ERD)  
- [ ] `slides/`  
- [x] `docs/etl_reconciliation.md` (CNE ↔ CAOP)  

---

**Last updated:** June 2026
