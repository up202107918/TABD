# Reproducibility guide (§9)

End-to-end procedure to rebuild the **Election Analytics Platform** from an empty PostgreSQL database.  
Use this section in the technical report and for oral demo preparation.

**Estimated time:** 15–25 minutes (excluding CNE data download).

---

## 1. Prerequisites

| Requirement | Version / notes |
|-------------|-----------------|
| PostgreSQL | 14+ |
| PostGIS | `CREATE EXTENSION postgis` on the target database |
| Python | 3.9+ |
| `psql` | On `PATH` (for schema load and smoke SQL) |
| CNE data | Folder `etl/data/2021al_mapa_oficial/` (Excel mapas). Not in Git if large — see [README.md](../README.md) and [etl/data/README.md](../etl/data/README.md) |
| Git clone | Repository root = `TABD/` |

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

---

## 2. Environment variables

Set once per shell session (or edit `etl/config.py`):

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="election_analytics"
$env:DB_USER="postgres"
$env:DB_PASSWORD="your_password"
$env:PGCLIENTENCODING="UTF8"
```

The Flask app and ETL both read `DB_CONFIG` from `etl/config.py`.

---

## 3. Database creation

```powershell
createdb -U postgres -h localhost election_analytics
psql -U postgres -h localhost -d election_analytics -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

---

## 4. Schema load (order matters)

From repository root:

```powershell
psql -U postgres -h localhost -d election_analytics -v ON_ERROR_STOP=1 -f sql/01_operational_schema.sql
psql -U postgres -h localhost -d election_analytics -v ON_ERROR_STOP=1 -f sql/02_warehouse_schema.sql
psql -U postgres -h localhost -d election_analytics -v ON_ERROR_STOP=1 -f sql/03_functions_triggers.sql
psql -U postgres -h localhost -d election_analytics -v ON_ERROR_STOP=1 -f sql/05_staging_schema.sql
```

| File | Purpose |
|------|---------|
| `01_operational_schema.sql` | Normalized model + PostGIS columns |
| `02_warehouse_schema.sql` | Star schema (`dim_*`, `fact_*`) |
| `03_functions_triggers.sql` | Functions, PL/pgSQL, triggers |
| `05_staging_schema.sql` | Staging tables + `stg_etl_run_log` |

**Not loaded in this step:**

- `sql/04_analytical_queries.sql` — analytical views/functions (run after ETL, step 6).
- `sql/06_sample_data.sql` — ad-hoc validation only, **not** seed data.
- `sql/07_demo_queries.sql` — report/oral demo queries (step 6).
- `sql/08_smoke_checks.sql` — post-load verification (step 5).

---

## 5. ETL full load (2021, CM, municipality)

```powershell
cd etl

# Boundaries (GeoJSON fallback or official CAOP ZIP if available)
..\.venv\Scripts\python.exe -m pipeline.download_caop

# Full pipeline: extract → operational → geo → seat_result → warehouse → summaries
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2021 --mode full
```

**Phases inside `--mode full`:**

1. Truncate staging; load CNE Excel (`mapa_1`) → `staging.stg_*`
2. Transform → `operational.*` (votes, turnout, territories)
3. CAOP geometries → `district.geometry`, `municipality.geometry`
4. CNE `mapa_2` mandate columns → `operational.seat_result`
5. Load `warehouse.fact_election_result`, `fact_turnout`
6. Refresh `party_municipality_summary`

Run log: `staging.stg_etl_run_log` (`status = completed`).

### Optional: second election year (analytics compare)

```powershell
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2017 --mode full
```

Enables cross-year charts on `/analytics` when both years exist.

---

## 6. Verification (smoke checks)

**Option A — SQL file:**

```powershell
cd ..   # repo root
psql -U postgres -h localhost -d election_analytics -f sql/08_smoke_checks.sql
```

**Option B — Python script (exit code 0 = pass):**

```powershell
.\.venv\Scripts\python.exe scripts\smoke_check.py
```

### Expected order of magnitude (aut_2021 full load)

| Check | Approximate count |
|-------|-------------------|
| `staging.stg_election_results` | ≥ 1 000 |
| `staging.stg_turnout_data` | ≥ 250 |
| `operational.municipality` | ≥ 250 |
| Districts with geometry | ~18 (continent fallback) |
| Municipalities with geometry | ~280+ |
| `vote_result` rows (2021) | ≥ 1 000 |
| `seat_result` rows with seats (2021) | ≥ 400 |
| `warehouse.fact_election_result` | ≥ 1 000 |
| `warehouse.fact_turnout` | ≥ 250 |

**Sample sanity (Lisboa 2021, CM):** parties **A** and **B** with **7** seats each, **CDU** 2, **BE** 1 (17-seat council; CNE `mapa_2`, `allocation_method = CNE mapa_2`).

Validation document: [etl/docs/validation_samples_2021.md](../etl/docs/validation_samples_2021.md).

---

## 7. Analytical SQL + demo outputs (report)

```powershell
.\.venv\Scripts\python.exe scripts\run_sql_demos.py
```

Produces:

- `docs/sql_outputs/demo_results.txt` — `sql/03` + `sql/04` sample output
- `docs/sql_outputs/_apply_log.txt` — view/function apply log

---

## 8. Web application

```powershell
cd app
..\.venv\Scripts\python.exe app.py
```

Open **http://localhost:8000** · select election in navbar · drill-down: districts → municipality → **Analytics**.

**Matplotlib PNG export (report figures):**

```powershell
cd ..
.\.venv\Scripts\python.exe scripts\export_charts.py
```

Writes `docs/screenshots/matplotlib_analytics_*.png`.

---

## 9. Data not in repository

| Item | How to obtain |
|------|----------------|
| CNE Autárquicas 2021 ZIP | [cne.pt — 2021 mapa oficial](https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip) → unpack to `etl/data/2021al_mapa_oficial/` |
| CAOP boundaries (optional full islands) | [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) or `python -m pipeline.download_caop` (continent fallback) |

Territorial reconciliation: [etl_reconciliation.md](etl_reconciliation.md).

---

## 10. Known limitations (state honestly in report)

- MVP organ: **CM** only; municipality level (no parishes in ETL).
- ~50 CNE municipalities may appear in `mapa_2` but not in `mapa_1` extract (no votes in DB).
- Default CAOP fallback: **continent**; Azores/Madeira may lack polygons.
- `warehouse.agg_*` tables exist but are **not** populated after ETL.

---

## 11. One-page checklist (copy for report §9)

```
[ ] venv + pip install -r requirements.txt
[ ] createdb election_analytics + PostGIS
[ ] sql/01 → 02 → 03 → 05
[ ] etl: download_caop + run_etl.py --dataset aut_2021 --mode full
[ ] smoke: scripts/smoke_check.py OR sql/08_smoke_checks.sql
[ ] demos: scripts/run_sql_demos.py
[ ] app: python app/app.py → http://localhost:8000
```

---

*Last updated: June 2026*
