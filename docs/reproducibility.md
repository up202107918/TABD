# Reproducibility guide (§9)

End-to-end procedure to rebuild the **Election Analytics Platform** from an empty PostgreSQL database.  
Use this section in the technical report and for oral demo preparation.

**Canonical setup:** [README.md](../README.md) (steps 1–5). This document adds verification, demo SQL, and a report checklist.

**Estimated time:** 20–30 minutes (CNE data is already under `etl/data/` in the repo).

---

## 1. Prerequisites

| Requirement | Version / notes |
|-------------|-----------------|
| PostgreSQL | 14+ |
| PostGIS | `CREATE EXTENSION postgis` on the target database |
| Python | **3.11 or 3.12** (64-bit, [python.org](https://www.python.org/downloads/)) — **not** MSYS2 / Git-Bash Python |
| `psql`, `createdb` | On `PATH` |
| CNE data | `etl/data/al2017_mapaoficial_retif02_01out2018/`, `etl/data/2021al_mapa_oficial/` (in Git) |
| Working directory | Repository root `TABD/` |

Check interpreters (Windows):

```powershell
py -0p
```

---

## 2. Python environment

From repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Verify: `.\.venv\Scripts\python.exe --version` → 3.11.x or 3.12.x, and `Test-Path .\.venv\Scripts\python.exe` → `True`.

If `.venv\bin\` exists instead of `.venv\Scripts\`, delete `.venv` and recreate with `py -3.12`.

---

## 3. Environment variables

Set **once per PowerShell session** (same window for ETL and the app), or edit `etl/config.py`:

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="election_analytics"
$env:DB_USER="postgres"
$env:DB_PASSWORD="your_password"
$env:PGCLIENTENCODING="UTF8"
```

Flask and ETL both read `DB_CONFIG` from `etl/config.py`.

---

## 4. Database creation

```powershell
createdb -U postgres -h localhost election_analytics
psql -U postgres -h localhost -d election_analytics -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

---

## 5. Schema load (order matters)

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

- `sql/04_analytical_queries.sql` — analytical views/functions (step 8).
- `sql/06_sample_data.sql` — ad-hoc validation only, **not** seed data.
- `sql/07_demo_queries.sql` — report/oral demo queries (step 8).
- `sql/08_smoke_checks.sql` — optional SQL smoke checks (step 7).

---

## 6. ETL full load — **required**

> Without `--mode full` the app starts but is empty (no map polygons, charts, or turnout).

**Keep `$env:DB_PASSWORD` set** from step 3.

```powershell
cd etl
..\.venv\Scripts\python.exe -m pipeline.download_caop

# Recommended: both years (~15–30 s each; wait for "Pipeline finished")
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2017 --mode full
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2021 --mode full
```

Each run must end with `Pipeline finished: dataset=aut_… mode=full`. If it stops after `Territories loaded`, check `staging.stg_etl_run_log` for `failed` or re-run.

**Phases inside `--mode full`:**

1. Truncate staging; load CNE Excel (`mapa_1`) → `staging.stg_*`
2. Transform → `operational.*` (votes, turnout, territories)
3. CAOP geometries → `district.geometry`, `municipality.geometry`
4. CNE `mapa_2` → `operational.seat_result`
5. Load `warehouse.fact_election_result`, `fact_turnout`
6. Refresh `party_municipality_summary`

Run log: `staging.stg_etl_run_log` (`status = completed`).

Optional — seat reload only (if charts empty after a successful full load):

```powershell
..\.venv\Scripts\python.exe ..\scripts\load_seats.py --dataset aut_2017
..\.venv\Scripts\python.exe ..\scripts\load_seats.py --dataset aut_2021
```

If turnout shows **0%** everywhere after load:

```powershell
cd ..
.\.venv\Scripts\python.exe scripts\fix_turnout_percentages.py
```

---

## 7. Verification (smoke checks)

From repository root (`cd ..` if still in `etl/`):

**Option A — Python (recommended, exit code 0 = pass):**

```powershell
.\.venv\Scripts\python.exe scripts\smoke_check.py
```

**Option B — SQL file:**

```powershell
psql -U postgres -h localhost -d election_analytics -f sql/08_smoke_checks.sql
```

### Expected order of magnitude (after **both** 2017 + 2021 loads)

| Check | Approximate count |
|-------|-------------------|
| `staging.stg_election_results` | ≥ 1 000 (last run’s staging) |
| `staging.stg_turnout_data` | ≥ 250 |
| `operational.municipality` | ≥ 250 |
| Districts with geometry | ~18 (continent fallback) |
| Municipalities with geometry | ~280+ |
| `vote_result` rows (2021) | ≥ 1 000 |
| `seat_result` rows with seats (2021) | ≥ 400 |
| `warehouse.fact_election_result` | ≥ 1 000 |
| `warehouse.fact_turnout` | ≥ 250 |

**Sample sanity (Lisboa 2021, CM):** parties **A** and **B** with **7** seats each, **CDU** 2, **BE** 1.

Validation document: [etl/docs/validation_samples_2021.md](../etl/docs/validation_samples_2021.md).

---

## 8. Analytical SQL + demo outputs (report)

```powershell
$env:DB_PASSWORD="your_password"   # if new shell
.\.venv\Scripts\python.exe scripts\run_sql_demos.py
```

Produces:

- `docs/sql_outputs/demo_results.txt` — `sql/07_demo_queries.sql` output
- `docs/sql_outputs/_apply_log.txt` — `sql/04` apply log

See [docs/sql_outputs/README.md](sql_outputs/README.md).

---

## 9. Web application

**Same PowerShell session as ETL** (`$env:DB_PASSWORD` still set):

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

## 10. Data not in repository

| Item | How to obtain |
|------|----------------|
| CNE Autárquicas 2021 ZIP | [cne.pt — 2021 mapa oficial](https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip) → `etl/data/2021al_mapa_oficial/` |
| CAOP boundaries (full islands) | [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) or `python -m pipeline.download_caop` (continent fallback) |

Territorial reconciliation: [etl_reconciliation.md](etl_reconciliation.md).

---

## 11. Known limitations (state honestly in report)

- MVP organ: **CM** only; municipality level (no parishes in ETL).
- ~50 CNE municipalities may appear in `mapa_2` but not in `mapa_1` extract (no votes in DB).
- Default CAOP fallback: **continent**; Azores/Madeira may lack polygons.
- `warehouse.agg_*` tables exist but are **not** populated after ETL.

---

## 12. One-page checklist (copy for report §9)

```
[ ] py -3.12 -m venv .venv + pip install -r requirements.txt
[ ] DB_* env vars set (same PowerShell session)
[ ] createdb -U postgres -h localhost election_analytics + PostGIS
[ ] sql/01 → 02 → 03 → 05
[ ] etl: download_caop + run_etl.py --dataset aut_2017 --mode full
[ ] etl: run_etl.py --dataset aut_2021 --mode full
[ ] smoke: scripts/smoke_check.py (exit 0)
[ ] demos: scripts/run_sql_demos.py
[ ] app: cd app && ..\.venv\Scripts\python.exe app.py → http://localhost:8000
```

---

*Last updated: June 2026*
