# Election Analytics Platform for Portugal

**Advanced Topics in Databases** · FCUP · 2025/26 · Prof. Michel Ferreira

**Amos Ehiomone Uwamusi** (up202502075) · **Kamil Tasarz** (up202512958) · **Sérgio Teixeira Cardoso** (up202107918)

June 2026

---

## Abstract

We implemented a PostgreSQL/PostGIS database system for Portuguese local (*Autárquicas*) elections: CNE official Excel results, DGT administrative boundaries, a Python ETL through staging into a normalized operational model and a star-schema warehouse, PL/pgSQL logic and analytical SQL (including D'Hondt), and a Flask web client with maps and charts. The load covers **Câmara Municipal** results at **municipality** level for **2017 and 2021**, with sample validation against CNE for Lisboa, Porto, and Barrancos (see [etl/docs/validation_samples_2021.md](../etl/docs/validation_samples_2021.md)).

---

## Problem scope and chosen election datasets

Portuguese local election results are distributed as multi-sheet CNE workbooks (*mapas*). Lists are often identified by **local codes** (e.g. A, B in Lisboa 2021), not only national party acronyms. Vote counts, turnout, and mandates appear in different sheets; boundary files use another naming scheme. The project goal is a **database-centred** application: store data in a normalized schema and a warehouse, load it through a rerunnable ETL, expose non-trivial SQL (D'Hondt, window functions, `ROLLUP`, `CUBE`), and serve a thin web UI that queries PostgreSQL with **psycopg2** (no ORM).

**Datasets used**

- **CNE Autárquicas 2021** — primary source for votes and turnout via `mapa_1` (wide Excel layout). Data layout: [etl/data/README.md](../etl/data/README.md).
- **CNE Autárquicas 2017** — second election year for cross-year comparison ([docs/cross_election_comparison.md](cross_election_comparison.md)).
- **CNE `mapa_2`** — official seat counts per list (`M` columns), loaded into `seat_result` (see [docs/etl_reconciliation.md](etl_reconciliation.md) §3).
- **DGT CAOP 2021** — district and municipality polygons; fallback download: [etl/data/caop/README.md](../etl/data/caop/README.md).

**Scope of the load:** organ **Câmara Municipal (CM)** only; **municipality** rows (no parish-level ETL). Not loaded: `mapa_3` (elected persons), Assembleia Municipal, Junta de Freguesia.

Setup, schema load order, and recommended **2017 + 2021** full load: [README.md](../README.md) § Setup.

---

## Operational schema and warehouse design rationale

The system uses three PostgreSQL schemas: **staging** (`sql/05_staging_schema.sql`), **operational** (`sql/01_operational_schema.sql`), and **warehouse** (`sql/02_warehouse_schema.sql`).

**Operational model.** Territories form a hierarchy (`district` → `municipality`; `parish` exists in DDL but is not populated by ETL). Elections link to `election_type` and `electoral_organ`. Political entities are `party` and `coalition` (with `coalition_member`). **`candidacy`** is the hub: one row per list in a given election, organ, and municipality. Results are split into **`vote_result`**, **`seat_result`**, and **`turnout`**. PostGIS `geometry` on district and municipality supports map APIs; GiST indexes support spatial filters.

Territorial matching uses **CNE names**, not a single official concelho code end-to-end: districts use fixed INE-style codes; municipality codes are **generated** per district from distinct CNE pairs ([docs/etl_reconciliation.md](etl_reconciliation.md) §4). The same territory rows are reused across election years; facts are scoped by `election_id`.

**Indexing.** Composite indexes on `candidacy` (election, organ, municipality) and `vote_result` (candidacy, votes descending) match the usual filter paths. `party_municipality_summary` is refreshed after ETL via `refresh_party_municipality_summary()` in `sql/03_functions_triggers.sql`.

**Warehouse.** Facts: `fact_election_result`, `fact_turnout`. Dimensions: time, election, organ, district, municipality, party. Views `vw_complete_results` and `vw_turnout_analysis` support reporting. Tables `agg_*` are defined but **not filled** in the current pipeline ([README.md](../README.md) — Known limitations).

**Insert figure 1** — `docs/er_diagrams/operational_schema_er.png`  
*Caption: Normalized operational schema (pgAdmin ERD export).*

**Insert figure 2** — `docs/er_diagrams/warehouse_star_schema.png`  
*Caption: Warehouse star schema — facts and dimensions.*

---

## ETL pipeline and data cleaning decisions

The ETL is described in [etl/README.md](../etl/README.md). Orchestration: `etl/run_etl.py --mode full`.

| Phase | Module | Output |
|-------|--------|--------|
| Extract | `pipeline/extract.py` | `staging.stg_election_results`, `stg_turnout_data` |
| Operational | `pipeline/transform_operational.py` | parties, candidacies, votes, turnout |
| Geometries | `pipeline/transform_geo.py` | CAOP → district/municipality `geometry` |
| Seats | `pipeline/load_seats.py` | `seat_result` from `mapa_2` |
| Warehouse | `pipeline/load_warehouse.py` | `dim_*`, `fact_*` |
| Post-load | `pipeline/post_load.py` | summaries, turnout percentages |

**Cleaning:** wide sheets unpivoted to one row per party column; integer vote coercion; party mapping and `get_or_create_party`; title-cased territory names; CM rows only (empty `freguesia`). Runs are **rerunnable** per `election_id` (`staging.stg_etl_run_log`).

**CNE ↔ CAOP:** Full reconciliation narrative in [docs/etl_reconciliation.md](etl_reconciliation.md). Validation samples (Lisboa, Porto, Barrancos): **zero mismatches** for votes, turnout, %, and seats. ~50 municipalities in `mapa_2` without `mapa_1` rows remain without votes in the DB (documented source gap).

Bulk load uses `session_replication_role = replica` (audit triggers off); percentages recomputed in post-load.

---

## Functions, PL/pgSQL routines, and triggers

All objects live in `sql/03_functions_triggers.sql`.

**Functions:** `calculate_vote_percentage`, `get_party_performance_in_municipality`, `get_top_parties`, `get_or_create_party`.

**PL/pgSQL:** `allocate_seats_dhondt` (D'Hondt); `calculate_turnout_percentages` (batch after ETL). **Procedure:** `refresh_party_municipality_summary`.

**Views:** `vw_candidacy_details`, `vw_municipality_summary`. **Warehouse views:** `vw_complete_results`, `vw_turnout_analysis` (`sql/02`).

**Triggers:** `trg_vote_percentages`, `trg_turnout_percentages`; audit on candidacy and vote_result → `audit_log`.

**Sample check (Lisboa 2021, CM):** list **A** at 35.35% (function matches stored %). CNE mandates: A 7, B 7, CDU 2, BE 1 (`allocation_method = CNE mapa_2`). `allocate_seats_dhondt` with **7** seats is a course demo (3+3+1), not the full 17-seat council.

Demo output: [docs/sql_outputs/demo_results.txt](sql_outputs/demo_results.txt) (regenerate: [docs/sql_outputs/README.md](sql_outputs/README.md)).

**Insert figure 3 (optional, ~¼ page)** — screenshot of psql or pgAdmin running `allocate_seats_dhondt` or top rows of `demonstrate_dhondt`  
*Suggested file: `docs/screenshots/dhondt_query.png` (capture locally; not in repo yet).*

---

## Analytical queries and key findings

Views and `demonstrate_dhondt` in `sql/04_analytical_queries.sql`. Apply after ETL; sample results in [docs/sql_outputs/demo_results.txt](sql_outputs/demo_results.txt).

| View / function | Technique |
|-----------------|-----------|
| `analytical_query_1_party_rankings` | `RANK`, running totals |
| `analytical_query_2_district_comparison` | Party % vs district average |
| `analytical_query_3_turnout_analysis` | `NTILE`, quartiles |
| `analytical_query_4_rollup_hierarchical` | `GROUP BY ROLLUP` |
| `analytical_query_5_cube_multidimensional` | `GROUP BY CUBE` |
| `analytical_query_6_advanced_aggregates` | `FILTER`, `STRING_AGG`, `ARRAY_AGG` |
| `analytical_query_8_cross_district_comparison` | Cross-district ranks |
| `demonstrate_dhondt` | Ranked quotients (ex10-style) |

**Key findings**

1. **Lisboa CM 2021:** **A** (35.35%) and **B** (34.38%) dominate over a single national-party reading.
2. **Cross-year Lisboa:** 2017 winner **PS** (43.89%) vs 2021 winner **A** (35.35%).
3. **District contrast (2021):** Lisboa list **A** +14.87 pp vs district average; **PSD** −20.74 pp (`analytical_query_2`).
4. **Porto D'Hondt demo (7 seats):** PS 5, B 2.
5. **Warehouse:** ~1 256 `fact_election_result` and ~281 `fact_turnout` rows after full load (see demo output tail).

**Insert figure 4 (optional)** — truncated table from `demo_results.txt` (e.g. `analytical_query_1` for Lisboa)  
*Can be a screenshot: `docs/screenshots/window_function.png` or pasted as a small table in LaTeX.*

---

## Frontend overview and visualizations

Stack and routes: [README.md](../README.md) § Web application. Flask + **psycopg2**; election and territory via navbar (`election_id` query param).

- **Maps:** Leaflet + `/api/map/districts`, `/api/map/municipalities/<id>` — click navigates to district/municipality pages.
- **Charts:** Chart.js (`party_comparison`, `election_comparison` for 2017 vs 2021 — [docs/cross_election_comparison.md](cross_election_comparison.md)).
- **Matplotlib:** `/analytics/chart.png`; export via `scripts/export_charts.py`.

**Insert figure 5** — `docs/screenshots/matplotlib_analytics_votes.png`  
*Caption: Top CM vote shares (Matplotlib, SQL-driven).*

**Insert figure 6** — `docs/screenshots/matplotlib_analytics_seats.png`  
*Caption: Seat distribution chart (requires `seat_result` loaded).*

**Insert figure 7 (recommended for PDF)** — `docs/screenshots/homepage.png`  
*Capture: `http://localhost:8000/` — national map + election selector. Not in repo yet; see [docs/screenshots/README.md](screenshots/README.md).*

**Insert figure 8 (recommended for PDF)** — `docs/screenshots/municipality_detail.png`  
*Capture: any municipality page — results table + Chart.js bars.*

**Insert figure 9 (optional)** — `docs/screenshots/analytics_dashboard.png`  
*Capture: `/analytics` — cross-year comparison + Matplotlib embeds.*

---

## Known limitations and possible extensions

As summarized in [README.md](../README.md) (Known MVP limitations) and [todo.md](../todo.md):

- CM and municipality only; no parish / AM / JF in ETL.
- CAOP fallback: **continent**; islands may lack geometry.
- ~50 `mapa_2`-only municipalities without votes; cross-year party codes not comparable nationally (local list codes).
- `warehouse.agg_*` not populated; turnout % needs post-load refresh on older runs (`scripts/fix_turnout_percentages.py`).
- No authentication; batch ETL only.

**Extensions:** `agg_*` load, AM/JF, full CAOP islands, parish level, AJAX map panel, Plotly.

**Reproducibility (evaluator):** step-by-step [docs/reproducibility.md](reproducibility.md) — schemas `01→02→03→05`, `run_etl.py` for `aut_2017` and `aut_2021`, `scripts/smoke_check.py`, `scripts/run_sql_demos.py`, Flask on port 8000.

**External data:** CNE results; DGT CAOP; GeoJSON fallback [nmota/caop_GeoJSON](https://github.com/nmota/caop_GeoJSON) when the official ZIP is unavailable.

---

## Contribution of each group member

*Based on `git log --no-merges` in this repository (36 commits; authors: Kamil Tasarz, Sérgio Cardoso, Amos via `binaryonline` / `Don Binary`).*

**Amos Ehiomone Uwamusi (up202502075)** — **Initial platform** (*Initial commit: Complete election analytics platform*, `binaryonline`): operational, warehouse, and staging SQL (`sql/01`–`06`), functions/triggers and analytical queries (`sql/03`, `sql/04`), Flask application and templates (`app/`), monolithic `etl/etl_pipeline.py` and `etl/config.py`, project README and report template skeleton. Later fix: `PERCENT_RANK` type casting in `sql/04_analytical_queries.sql`.

**Kamil Tasarz (up202512958)** — **Majority of implementation commits (21):** modular ETL (`etl/pipeline/*`, `run_etl.py`, staging → operational → warehouse), `mapa_2` seat loading (`load_seats.py`, `mapa2_seats.py`), Autárquicas **2017** extract and cross-year app/API, CNE validation scripts and [etl/docs/validation_samples_2021.md](../etl/docs/validation_samples_2021.md), [docs/etl_reconciliation.md](etl_reconciliation.md), ER diagram PNG exports, SQL demo pipeline (`sql/07`, [docs/sql_outputs/demo_results.txt](sql_outputs/demo_results.txt)), [docs/reproducibility.md](reproducibility.md) and smoke checks, Matplotlib charts (`app/charts.py`, `export_charts.py`), turnout/seat/chart bugfixes, README/todo consolidation.

**Sérgio Teixeira Cardoso (up202107918)** — **Data and deliverables (11 commits):** CNE election archives under `etl/data/` (2017, 2021, and related folders), early `etl/config.py` and pipeline edits, SQL schema files bundled with data setup, `requirements.txt`, **LaTeX report** (`docs/report/*.tex`, `Report.pdf`) and **Beamer slides** (`slides/Presentation.tex`), ongoing report/slides updates.

---

### Figure checklist (PDF / LaTeX)

| # | File path | Section | In repo? |
|---|-----------|---------|----------|
| 1 | `docs/er_diagrams/operational_schema_er.png` | Operational schema | ✅ |
| 2 | `docs/er_diagrams/warehouse_star_schema.png` | Warehouse | ✅ |
| 3 | `docs/screenshots/dhondt_query.png` | Functions / SQL | ❌ capture |
| 4 | `docs/screenshots/window_function.png` | Analytical (optional) | ❌ capture |
| 5 | `docs/screenshots/matplotlib_analytics_votes.png` | Frontend | ✅ |
| 6 | `docs/screenshots/matplotlib_analytics_seats.png` | Frontend | ✅ |
| 7 | `docs/screenshots/homepage.png` | Frontend | ❌ capture |
| 8 | `docs/screenshots/municipality_detail.png` | Frontend | ❌ capture |
| 9 | `docs/screenshots/analytics_dashboard.png` | Frontend (optional) | ❌ capture |
