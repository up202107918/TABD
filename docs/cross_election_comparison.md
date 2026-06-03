# Cross-election comparison (Autárquicas 2017 vs 2021)

## Data prerequisite

Load each year separately (does not remove the other year):

```powershell
cd etl
python run_etl.py --dataset aut_2017 --mode full
python run_etl.py --dataset aut_2021 --mode full
```

Config: `etl/config.py` (`aut_2017`, `aut_2021`). Extractor supports 2017 header row (cod/conc on row 2) via `find_wide_mapa_header_row()` in `etl/pipeline/extract.py`.

## API

`GET /api/charts/election_comparison`

| Parameter | Description |
|-----------|-------------|
| `election_id_a`, `election_id_b` | Operational election IDs |
| `election_year_a`, `election_year_b` | Alternative to IDs |

Default (no params): two years in DB, ordered older → newer.

Response: `parties`, `datasets` (Chart.js), `rows` (vote % and Δ pp), `turnout` (average CM turnout per year).

## UI

**http://localhost:8000/analytics** — section *Compare local elections*: two dropdowns, grouped bar chart, turnout summary, delta table.

Query string preserved: `?election_id_a=2&election_id_b=1`.

## Report / defence notes

- National CM aggregation; party codes differ by municipality (e.g. Lisboa A/B in 2021 vs national PS/PSD) — mention as limitation.
- Territorial drill-down remains single-year (`/municipality/<id>?election_id=…`).
- Analytical SQL for territories/parties within one year: `sql/04_analytical_queries.sql`.
