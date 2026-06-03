# ETL data directory

Election workbooks used by `etl/etl_pipeline.py`. The pipeline discovers **subdirectories** under this folder and loads all `.xls` / `.xlsx` files recursively.

## Layout

| Path | In Git? | Purpose |
|------|---------|---------|
| `2021al_mapa_oficial/`, `2025al-mapa-oficial_retificado/`, `al2013_*`, `al2017_*` | Yes | Official CNE mapas (source datasets for staging) |
| `downloads/` | No (`.gitkeep` only) | Optional: raw ZIP archives from CNE |
| `extracted/` | No (`.gitkeep` only) | Optional: unpacked ZIP contents |
| `processed/` | No | Intermediate outputs (if added later) |
| `logs/` | No | `etl_pipeline.log` from local runs |

## Mapa files (CNE autárquicas)

Each election year folder typically contains:

- **mapa_1** / **Parte1** — results (votes, lists, mandates)
- **mapa_2** / **Parte2** — percentage of mandates
- **mapa_3** / **Parte3** — elected officials
- **mapa_anexo** / **Parte4** — annex / supplementary tables

The ETL reads **Excel** (`.xls`, `.xlsx`). `.ods` files in the ZIP are kept for reference but are not loaded by the current pipeline.

## Official download URLs

If you need to refresh data locally (not required when cloned datasets are present):

| Dataset | Source | URL |
|---------|--------|-----|
| Autárquicas 2021 | CNE | https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip |

After download, either:

1. Unzip into `etl/data/2021al_mapa_oficial/` (recommended — same layout as in the repository), or  
2. Place the ZIP in `downloads/` and unpack to `extracted/autarquicas_2021/`, then copy or symlink the `.xlsx` files into a dataset folder the pipeline scans.

Historical datasets in this repo (2013, 2017, 2025) were added manually from CNE publications; obtain updated ZIPs from [cne.pt](https://www.cne.pt/) if you need newer revisions.

## Run ETL

```bash
cd etl
# Full pipeline (extract + operational + warehouse):
python run_etl.py --dataset aut_2021 --mode full

# Staging only (Excel to staging tables):
python run_etl.py --dataset aut_2021 --mode staging-only

# Legacy wrapper (same as staging-only for aut_2021):
python etl_pipeline.py
```

Requires PostgreSQL in `etl/config.py` (or `DB_*` env vars) and `sql/05_staging_schema.sql` applied.
