# ETL data directory

Election workbooks used by `run_etl.py` (dataset folders listed in `config.py`). The extract step scans configured subdirectories and loads `.xls` / `.xlsx` files.

## Layout


| Path                                                                              | In Git?              | Purpose                                          |
| --------------------------------------------------------------------------------- | -------------------- | ------------------------------------------------ |
| `2021al_mapa_oficial/`, `2025al-mapa-oficial_retificado/`, `al2013_*`, `al2017_*` | Yes                  | Official CNE mapas (source datasets for staging) |
| `downloads/`                                                                      | No (`.gitkeep` only) | Optional: raw ZIP archives from CNE              |
| `extracted/`                                                                      | No (`.gitkeep` only) | Optional: unpacked ZIP contents                  |
| `processed/`                                                                      | No                   | Intermediate outputs (if added later)            |
| `logs/`                                                                           | No                   | `etl_pipeline.log` from local runs               |


## Mapa files (CNE autárquicas)

Each election year folder typically contains:

- **mapa_1** / **Parte1** — results (votes, lists, mandates)
- **mapa_2** / **Parte2** — percentage of mandates
- **mapa_3** / **Parte3** — elected officials
- **mapa_anexo** / **Parte4** — annex / supplementary tables

The ETL reads **Excel** (`.xls`, `.xlsx`). `.ods` files in the ZIP are kept for reference but are not loaded. MVP uses **mapa_1** (votes + CM turnout), **mapa_2** (seats → `seat_result`); **mapa_anexo** and **mapa_3** are not loaded — see [docs/etl_reconciliation.md](../../docs/etl_reconciliation.md) and `etl/docs/source_inventory_2021.md`.

## Official download URLs

If you need to refresh data locally (not required when cloned datasets are present):


| Dataset          | Source | URL                                                                                                                                    |
| ---------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| Autárquicas 2021 | CNE    | [https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip](https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip) |


After download, either:

1. Unzip into `etl/data/2021al_mapa_oficial/` (recommended — same layout as in the repository), or
2. Place the ZIP in `downloads/` and unpack to `extracted/autarquicas_2021/`, then copy or symlink the `.xlsx` files into a dataset folder the pipeline scans.

Historical datasets in this repo (2013, 2017, 2025) were added manually from CNE publications; obtain updated ZIPs from [cne.pt](https://www.cne.pt/) if you need newer revisions.

## Run ETL

Requires PostgreSQL (`DB_*` env vars — see [../README.md](../README.md)) and schemas `sql/01`, `02`, `03`, `05`.

**PowerShell** (from repository root, env vars set):

```powershell
cd etl
..\.venv\Scripts\python.exe -m pipeline.download_caop
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2017 --mode full
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2021 --mode full
```

**Linux / macOS:**

```bash
cd etl
python -m pipeline.download_caop
python run_etl.py --dataset aut_2017 --mode full
python run_etl.py --dataset aut_2021 --mode full
```

Always use `--mode full` for the web app. `staging-only` loads Excel into staging tables only (maps and charts stay empty).