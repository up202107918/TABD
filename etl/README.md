# ETL pipeline

Python ETL for **Autárquicas 2021** (MVP): CNE Excel → PostgreSQL staging → operational schema → warehouse star schema → post-load summaries and geometries.

**Status:** MVP complete and rerunnable. Optional improvements are listed in [../todo.md](../todo.md).

---

## Quick start (full load)

From the repository root, with PostgreSQL and schemas already applied (`sql/01`–`05`):

**PowerShell:**

```powershell
$env:DB_NAME="election_analytics"
$env:DB_USER="postgres"
$env:DB_PASSWORD="your_password"

# 1) Boundaries (optional but needed for maps)
cd etl
..\.venv\Scripts\python.exe -m pipeline.download_caop

# 2) Full pipeline
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2021 --mode full
```

**Linux / macOS:**

```bash
export DB_NAME=election_analytics DB_USER=postgres DB_PASSWORD=your_password
cd etl
python -m pipeline.download_caop
python run_etl.py --dataset aut_2021 --mode full
```

---

## CLI

| Command | Effect |
|---------|--------|
| `python run_etl.py --dataset aut_2021 --mode full` | Extract → operational → geo → warehouse facts → post-load |
| `python run_etl.py --dataset aut_2021 --mode staging-only` | Excel → `staging.stg_*` only |
| `python run_etl.py --dataset aut_2021 --mode reload-operational` | Staging + operational + geo + post-load (no warehouse truncate/reload) |
| `python -m pipeline.download_caop` | Download CAOP GeoJSON fallback (or official ZIP if URL works) |

Default `--mode` is `staging-only`; for a complete load always pass `--mode full`.

Configuration: `config.py` (`DATASETS`, `DB_*` env vars). Only `aut_2021` is wired in config; other year folders under `data/` are not loaded until added to `DATASETS`.

---

## Pipeline phases (`--mode full`)

```
Excel (mapa_1, mapa_anexo)
    → pipeline/extract.py          → staging.stg_election_results, stg_turnout_data
    → pipeline/transform_operational.py → operational.* (CM, concelho)
    → pipeline/transform_geo.py    → district/municipality geometries (CAOP)
    → pipeline/load_warehouse.py   → warehouse dimensions + fact_* 
    → pipeline/load_seats.py       → operational.seat_result (CNE mapa_2)
    → pipeline/post_load.py        → party_municipality_summary
```

Run metadata: `staging.stg_etl_run_log`.

**Bulk load note:** operational load sets `session_replication_role = replica` to skip audit triggers during insert; triggers apply on normal app writes.

---

## What is loaded (MVP)

| Area | Source | Target |
|------|--------|--------|
| Results & lists | `mapa_1_resultados` (wide Excel unpivot) | `candidacy`, `vote_result`, parties/coalitions |
| Turnout | `mapa_1` (wide sheet, CM rows) | `turnout` (organ CM) |
| Rankings / winner | Derived in transform | `vote_result.ranking_position`, `is_winner` |
| Territory dictionary | CNE names in staging | `district`, `municipality` |
| Geometry | `data/caop/*.geojson` or `.shp` | `district.geometry`, `municipality.geometry` |
| Warehouse | Operational join | `dim_*`, `fact_election_result`, `fact_turnout` |

**Validation (post-load):** `python scripts/validate_samples_2021.py` → [docs/validation_samples_2021.md](docs/validation_samples_2021.md) (mapa_1 vs DB; mapa_2 vote %; D'Hondt ex10 pattern).

**Multi-election:** `aut_2017` and `aut_2021` in [config.py](config.py). Load 2017 after 2021 (or vice versa); each run only replaces rows for that `election_id`:

```bash
python run_etl.py --dataset aut_2017 --mode full
python run_etl.py --dataset aut_2021 --mode full
```

**Seats:** `mapa_2` `M` columns → `operational.seat_result` (see [../docs/etl_reconciliation.md](../docs/etl_reconciliation.md)).

**Skipped in MVP (by design):**

- `mapa_3` not loaded — see [docs/source_inventory_2021.md](docs/source_inventory_2021.md)
- `warehouse.agg_*` pre-aggregation tables (not filled after truncate)

---

## Layout

```
etl/
├── config.py              # DB, DATASETS, CAOP URLs
├── run_etl.py             # CLI entry point
├── etl_pipeline.py        # Legacy wrapper → staging-only behaviour
├── pipeline/
│   ├── runner.py          # Orchestration + run log
│   ├── extract.py
│   ├── transform_operational.py
│   ├── transform_geo.py
│   ├── load_warehouse.py
│   ├── post_load.py
│   └── download_caop.py
├── data/                  # CNE workbooks — see data/README.md
├── data/caop/             # Boundaries — see data/caop/README.md
└── docs/
    └── source_inventory_2021.md
```

Logs: `etl/data/logs/etl_pipeline.log` (local, not in Git).

---

## Sanity checks (after `full`)

```sql
-- Staging
SELECT COUNT(*) FROM staging.stg_election_results;
SELECT COUNT(*) FROM staging.stg_turnout_data;

-- Operational (2021, CM)
SELECT COUNT(*) FROM operational.turnout t
JOIN operational.election e ON e.election_id = t.election_id
WHERE e.election_year = 2021;

SELECT COUNT(*) FROM operational.vote_result vr
JOIN operational.candidacy c ON c.candidacy_id = vr.candidacy_id
JOIN operational.election e ON e.election_id = c.election_id
WHERE e.election_year = 2021;

-- Geo
SELECT COUNT(*) FROM operational.district WHERE geometry IS NOT NULL;
SELECT COUNT(*) FROM operational.municipality WHERE geometry IS NOT NULL;

-- Warehouse
SELECT COUNT(*) FROM warehouse.fact_election_result;
SELECT COUNT(*) FROM warehouse.fact_turnout;

-- Last run
SELECT run_id, run_name, status, rows_staged, rows_loaded, end_time
FROM staging.stg_etl_run_log ORDER BY run_id DESC LIMIT 3;
```

Expected order of magnitude (approximate): ~1500+ staging results rows, ~300 turnout municipalities, ~18 districts / ~280+ municipalities with geometry (fallback GeoJSON), ~1500 fact result rows.

---

## Data sources

| Data | Provider | In repo / download |
|------|----------|-------------------|
| Autárquicas 2021 results | [CNE](https://www.cne.pt/content/eleicoes-autarquicas-2021) | `data/2021al_mapa_oficial/` |
| Administrative boundaries | [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) | `python -m pipeline.download_caop` → `data/caop/` |

Territorial reconciliation (CNE ↔ CAOP, mapa files, islands): **[../docs/etl_reconciliation.md](../docs/etl_reconciliation.md)**.

---

## Related documentation

- [data/README.md](data/README.md) — folder layout and mapa file types  
- [data/caop/README.md](data/caop/README.md) — boundary download  
- [docs/source_inventory_2021.md](docs/source_inventory_2021.md) — which Excel files are used  
- [../README.md](../README.md) — whole project setup and Flask app  
- [../todo.md](../todo.md) — backlog  
