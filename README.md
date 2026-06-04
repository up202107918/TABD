# Election Analytics Platform for Portugal

Advanced Topics in Databases — practical assignment (FCUP).  
Database-centred system for Portuguese local election analysis: PostgreSQL/PostGIS, staging ETL, star-schema warehouse, analytical SQL, and a thin Flask frontend.

**Team:** Amos Uwamusi, Sérgio Cardoso, Kamil Tasarz

> **Recommended setup:** load **Autárquicas 2017 and 2021** (`aut_2017`, then `aut_2021` — order optional). Data is already under `etl/data/`. This unlocks the election selector, cross-year charts on `/analytics`, and the comparison API. See [Setup → ETL](#4-etl-full-load--recommended-2017--2021).

---

## Architecture

```
TABD/
├── sql/                 # Schemas, functions/triggers, analytical queries
├── etl/                 # ETL pipeline (run_etl.py, pipeline/)
├── app/                 # Flask + templates (psycopg2, Leaflet, Chart.js)
├── docs/                # Report, ER diagrams, screenshots (deliverables)
├── slides/              # Oral presentation (LaTeX / PDF)
└── scripts/             # Maintenance and demo helpers
```

---

## Prerequisites

- PostgreSQL **14+** with **PostGIS**
- Python **3.11 or 3.12** (64-bit, from [python.org](https://www.python.org/downloads/) or Microsoft Store) — **not** MSYS2 / Git-Bash Python
- Virtual environment in `.venv` (see step 2)

---

## Setup

> **Working directory:** open PowerShell in the **repository root** (`TABD/`).  
> **One shell session:** set env vars in step 3 and keep that window open for ETL (step 4) and the app (step 5).

### 1. Database

```powershell
createdb -U postgres -h localhost election_analytics
psql -U postgres -h localhost -d election_analytics -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

Load schemas (order matters):

```powershell
psql -U postgres -h localhost -d election_analytics -f sql/01_operational_schema.sql
psql -U postgres -h localhost -d election_analytics -f sql/02_warehouse_schema.sql
psql -U postgres -h localhost -d election_analytics -f sql/03_functions_triggers.sql
psql -U postgres -h localhost -d election_analytics -f sql/05_staging_schema.sql
```

- `sql/04_analytical_queries.sql` — run manually for demos / report (not part of ETL).
- `sql/06_sample_data.sql` — **validation queries only**, not seed data.

### 2. Python

Use the **python.org** interpreter (see Prerequisites). From repository root:

```powershell
# Create venv (3.11 also works)
py -3.12 -m venv .venv

# Install dependencies — always use python -m pip (not pip.exe directly)
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Connection

Set environment variables **in the same PowerShell window** (or edit `etl/config.py`):

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="election_analytics"
$env:DB_USER="postgres"
$env:PGCLIENTENCODING="UTF8"
$env:DB_PASSWORD="your_password"
```

Required before ETL and the Flask app. `app/app.py` imports `DB_CONFIG` from `etl/config.py`.

### 4. ETL (full load) — **required for maps, charts, and turnout**

> **Without this step the app starts but is empty:** no map polygons, no charts, turnout 0%.  
> Schemas alone do not load CNE results — you must run ETL with `--mode full`.

Load **both** election years so the navbar election selector and **/analytics** cross-year comparison work out of the box. Each `run_etl.py` run only replaces data for that `election_id`; order does not matter. Source folders are already in the repo under `etl/data/` (`al2017_mapaoficial_retif02_01out2018`, `2021al_mapa_oficial`).

**Use the same PowerShell window as step 3** (`$env:DB_PASSWORD` must still be set).

See **[etl/README.md](etl/README.md)** for modes, sanity SQL, and troubleshooting.

```powershell
cd etl
..\.venv\Scripts\python.exe -m pipeline.download_caop

# Full load (not staging-only)
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2017 --mode full
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2021 --mode full
```

### 5. Web application

**Set step 3 env vars in this same PowerShell window** (especially `$env:DB_PASSWORD`). A new terminal does not inherit them — `fe_sendauth: no password supplied` means `DB_PASSWORD` is empty.

From repository root (after ETL, if you are still in `etl/` run `cd ..` first):

```powershell
# Quick check before starting Flask
$env:DB_PASSWORD   # must not be empty

cd app
..\.venv\Scripts\python.exe app.py
```

Open **[http://localhost:8000](http://localhost:8000)** (default port from `PORT` env or 8000).

Use the navbar to select **election** and **municipality**; URLs carry `?election_id=...`.

After the **recommended 2017 + 2021** load (step 4), open **/analytics** for the side-by-side comparison chart, or `GET /api/charts/election_comparison?election_id_a=…&election_id_b=…` — details in [docs/cross_election_comparison.md](docs/cross_election_comparison.md).

---

## Database overview

### Operational (`operational`)

Normalized model: territories, elections, organs, parties/coalitions, candidacies, vote results, turnout, optional `seat_result`, PostGIS geometries.

### Staging (`staging`)

`stg_election_results`, `stg_turnout_data`, `stg_etl_run_log`, quality-issue table (for future use).

### Warehouse (`warehouse`)

Star schema: `dim_*`, `fact_election_result`, `fact_turnout`. Aggregate tables `agg_*` exist in schema but are **not populated** in the MVP load.

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


| Source                                                                                       | Use                                                                                       |
| -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| CNE Autárquicas **2017** (mapa oficial, retificado)                                          | `etl/data/al2017_mapaoficial_retif02_01out2018/` — `**aut_2017`** (recommended with 2021) |
| [CNE Autárquicas 2021](https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip)    | `etl/data/2021al_mapa_oficial/` — `**aut_2021`**                                          |
| [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) | Boundaries (`etl/data/caop/`, auto-download helper)                                       |


---

## Documentation map


| File                                                                   | Purpose                              |
| ---------------------------------------------------------------------- | ------------------------------------ |
| [README.md](README.md)                                                 | This file — project setup            |
| [etl/README.md](etl/README.md)                                         | ETL pipeline, modes, sanity SQL      |
| [etl/data/README.md](etl/data/README.md)                               | Data folder layout                   |
| [etl/data/caop/README.md](etl/data/caop/README.md)                     | Boundary files                       |
| [etl/docs/source_inventory_2021.md](etl/docs/source_inventory_2021.md) | Which CNE files are parsed           |
| [docs/etl_reconciliation.md](docs/etl_reconciliation.md)               | CNE ↔ CAOP reconciliation (§5.2)     |
| [docs/reproducibility.md](docs/reproducibility.md)                     | End-to-end rebuild guide (§9)        |
| [docs/cross_election_comparison.md](docs/cross_election_comparison.md) | 2017 vs 2021 API and `/analytics` UI |
| [docs/sql_outputs/README.md](docs/sql_outputs/README.md)               | Regenerate analytical demo outputs   |
| [slides/README.md](slides/README.md)                                   | Oral presentation                    |


---

## Known MVP limitations

- ETL MVP: local elections **2017 / 2021** (`aut_2017`, `aut_2021`), organ **CM**, **municipality** level (no parishes in ETL).  
- **warehouse agg_*** not populated after load.  
- ~50 municipalities in CNE mapa_2 may be absent from mapa_1 ETL (no votes / seats in DB).  
- CAOP fallback GeoJSON covers **continent**; islands may lack geometry until official shapefiles are added.  
- If turnout shows **0% / N/A** after an older ETL run: `.\.venv\Scripts\python.exe scripts\fix_turnout_percentages.py` (or re-run `run_etl.py --mode reload-operational`). Bulk load skips triggers, so percentages must be computed explicitly.  
- If **seats charts are empty**: load CNE mapa_2 into `seat_result` — `.\.venv\Scripts\python.exe scripts\load_seats.py --dataset aut_2021` (after operational votes exist).  
- No authentication; batch ETL only (not live election night).

---

## Deliverables


| Deliverable           | Location                                                                     |
| --------------------- | ---------------------------------------------------------------------------- |
| Report (PDF)          | [docs/report.pdf](docs/report.pdf) — sources in [docs/report/](docs/report/) |
| ER diagrams           | [docs/er_diagrams/](docs/er_diagrams/)                                       |
| ETL reconciliation    | [docs/etl_reconciliation.md](docs/etl_reconciliation.md)                     |
| Reproducibility guide | [docs/reproducibility.md](docs/reproducibility.md)                           |
| Presentation          | [slides/](slides/) (work in progress)                                        |
| Source code           | `sql/`, `etl/`, `app/`                                                       |


---

**Last updated:** June 2026