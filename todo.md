# Project TODO — Election Analytics Platform

**Reference:** [advanced_topics_databases_practical_assignment.pdf](advanced_topics_databases_practical_assignment.pdf)  
**Deadlines:** Moodle submission **4 June 2026, 23:59** · Oral presentation **5 June 2026**

Legend: `[x]` done · `[~]` implemented, needs verification/demo · `[ ]` to do

Use this file as the single backlog. Technical ETL details: [etl/README.md](etl/README.md).

---

## Quick status (MVP codebase)

| Area | Code status | Submission-ready? |
|------|-------------|-------------------|
| Operational + staging + warehouse DDL | `[x]` `sql/01`–`05` | `[~]` justify indexes in report |
| ETL rerunnable (2021, CM, municipality) | `[x]` `run_etl.py --mode full` | `[~]` document + reconciliation doc |
| SQL functions / PL/pgSQL / triggers | `[x]` `sql/03` | `[~]` demo on fresh DB |
| Analytical SQL (D'Hondt, windows, ROLLUP, CUBE) | `[x]` `sql/04` | `[~]` run on DB; outputs in `docs/sql_outputs/demo_results.txt` |
| PostGIS + Flask maps | `[x]` | `[~]` islands geometry gap |
| Flask psycopg2 + selectors + tables + charts | `[x]` | `[x]` Chart.js + Matplotlib `/analytics/chart.png` |
| Deliverables (`docs/`, `slides/`) | `[ ]` | **blocking** |

---

## 1. MUST HAVE

Required by the assignment or Moodle submission. Without these, the project is incomplete or hard to defend.

### 1.1 Deliverables & reproducibility (§7, §9, rubric 10%)

| Status | Task | PDF / rubric |
|--------|------|----------------|
| `[x]` | `README.md` — setup, ETL, Flask, data download hints | §7 structure, §9 reproducibility |
| `[x]` | **`docs/report.pdf`** (9 pages with figures; sources in `docs/report/`) | §7.1 |
| `[ ]` | Report §7.1: problem scope, datasets (CNE + CAOP), limitations, extensions | §7.1 |
| `[ ]` | Report: operational + warehouse **design rationale**, PK/FK/**indexing strategy** | §5.1, rubric 20% |
| `[ ]` | Report: ETL pipeline, cleaning, transformations | §5.2, rubric 20% |
| `[ ]` | Report: functions, PL/pgSQL, triggers (purpose, not artificial) | §5.3, rubric 20% |
| `[ ]` | Report: analytical queries + **key findings** (screenshots or result tables) | §5.4, rubric 20% |
| `[ ]` | Report: frontend + visualizations | §5.5–5.6, rubric 10% |
| `[ ]` | Report: **contribution of each group member** (2–3 students) | §7.1, §10 |
| `[x]` | **`docs/er_diagrams/`** — `operational_schema_er.png`, `warehouse_star_schema.png` (+ `.pgerd` sources) | §7, rubric 20% |
| `[ ]` | **`docs/screenshots/`** — working UI (home map, district, municipality, analytics) | §7 |
| `[ ]` | **`slides/`** — architecture, schema, ETL, SQL demos, live frontend (10–15 slides) | §7.2 |
| `[x]` | **`docs/etl_reconciliation.md`** — CNE ↔ CAOP: IDs, names, missing values, mismatches | §5.2 (explicit) |
| `[ ]` | Moodle: repo/archive per group; raw data too large → download script/instructions documented | §7 note |
| `[ ]` | **Oral prep:** every member can explain schema, ETL, analytical SQL, Flask integration | §7.2, §10 |
| `[ ]` | Cite external resources (CAOP fallback, libraries, AI tools if used) | §10 |

### 1.2 Data & ETL (§4, §5.2, §6, rubric 20%)

| Status | Task | PDF / rubric |
|--------|------|----------------|
| `[x]` | Official **CNE Autárquicas 2021** loaded via Python ETL | §4, §6 minimum |
| `[x]` | **Staging schema** before operational load | §5.2 |
| `[x]` | **Rerunnable** pipeline (`run_etl.py`, run log) | §5.2 |
| `[x]` | **Warehouse**: ≥1 fact + multiple dimensions populated | §5.2, §6 |
| `[x]` | **`docs/etl_reconciliation.md`** — CNE ↔ CAOP, mapa_1/2, islands, validation | §4, §5.2 |
| `[x]` | **`seat_result` populated** for CM from CNE mapa_2 `M` columns (`load_seats.py`) | §5.1 minimum model lists seat results |
| `[x]` | **Validate subset vs CNE** (Lisboa, Porto, Barrancos) — `etl/docs/validation_samples_2021.md` | §9 good practice |
| `[x]` | End-to-end reproducibility: [docs/reproducibility.md](docs/reproducibility.md), `sql/08_smoke_checks.sql`, `scripts/smoke_check.py` | §9 reproducibility |

### 1.3 Operational model (§5.1, rubric 20%)

| Status | Task | PDF / rubric |
|--------|------|----------------|
| `[x]` | Normalized schema: elections, organs, territories, parties, coalitions, candidacies, votes, turnout | §5.1 |
| `[x]` | **seat_result** rows linked to candidacies (mapa_2 → ETL) | §5.1 |
| `[x]` | PostGIS geometries on district + municipality | §5.5 |
| `[ ]` | Report explains **keys, constraints, indexes** (why each important index exists) | §5.1 |
| `[x]` | Model supports territorial drill-down (district → municipality) | §5.1 |

### 1.4 SQL programming (§5.3, rubric 20%)

| Status | Task | PDF / rubric |
|--------|------|----------------|
| `[x]` | ≥3 SQL **functions or views** (`sql/03`: e.g. `calculate_vote_percentage`, `vw_*`, `get_top_parties`) | §5.3 |
| `[x]` | ≥2 **PL/pgSQL** routines (`allocate_seats_dhondt`, `refresh_party_municipality_summary`, `calculate_turnout_percentages`, …) | §5.3 |
| `[x]` | ≥2 **triggers** (`trg_turnout_percentages`, `trg_vote_percentages`, audit triggers) | §5.3 |
| `[~]` | **Apply & test** on submission DB: `sql/03` + explain in report/slides — demos in `sql/07_demo_queries.sql`, `docs/sql_outputs/` | §5.3 |
| `[~]` | Note in report: ETL bulk load uses `session_replication_role = replica` (audit triggers skipped during load) | §5.3 consistency |

### 1.5 Analytical SQL (§5.4, rubric 20%)

| Status | Task | PDF / rubric |
|--------|------|----------------|
| `[x]` | **D'Hondt** — `allocate_seats_dhondt` / `demonstrate_dhondt` in `sql/03`–`04` | §5.4 |
| `[x]` | ≥3 queries with **window functions** (`analytical_query_1`–`3`, `8` in `sql/04`) | §5.4 |
| `[x]` | ≥1 **GROUP BY ROLLUP** (`analytical_query_4_rollup_hierarchical`) | §5.4 |
| `[x]` | ≥1 **GROUP BY CUBE** (`analytical_query_5_cube_multidimensional`) | §5.4 |
| `[x]` | ≥1 **advanced aggregate** (FILTER, STRING_AGG, ARRAY_AGG, JSON — `analytical_query_6`) | §5.4 |
| `[~]` | **Execute** `sql/04_analytical_queries.sql` on loaded DB; sample outputs in `docs/sql_outputs/demo_results.txt` | §5.4, §9 |
| `[ ]` | Report/slides: comparisons across **territories, parties** (and elections if multi-year added) | §5.4 |
| `[ ]` | Cross-check **D'Hondt / mandates** vs official CNE for sample municipalities | §9 |

### 1.6 Spatial & frontend (§5.5–5.6, rubric 10%)

| Status | Task | PDF / rubric |
|--------|------|----------------|
| `[x]` | **PostGIS** boundaries loaded (CAOP or documented fallback) | §5.5 |
| `[x]` | **District + municipality** map / drill-down (Leaflet, GeoJSON API) | §5.5 |
| `[x]` | **Flask** + **psycopg2**, explicit SQL (no ORM business logic) | §3, §5.6 |
| `[x]` | User selects **election** + **territorial unit** (navbar + URLs) | §5.6 |
| `[x]` | **Results table** on municipality (and related) pages | §5.6 |
| `[x]` | ≥**2 meaningful visual outputs** per relevant page (Chart.js charts) | §5.6 |
| `[x]` | **Charts from DB via Python + Matplotlib** — `app/charts.py`, `/analytics/chart.png`, `scripts/export_charts.py` → `docs/screenshots/` | §3, §5.5 |
| `[~]` | **Map interacts with interface** — today: click → navigate. Confirm with instructor or add same-page update (district click → load municipality stats via API without full reload) | §5.6 |
| `[ ]` | Screenshots proving map + charts + table on same flow | §7 |

### 1.7 Technologies (§3)

| Status | Task | PDF |
|--------|------|-----|
| `[x]` | PostgreSQL + PostGIS + Python + psycopg2 | §3 mandatory |
| `[x]` | Leaflet for maps | §3 recommended |
| `[x]` | Matplotlib for charts (server-side `/analytics/chart.png` + export script) | §3 recommended, §5.5 |

---

## 2. High value add-ons (SHOULD)

Not strictly blocking minimum scope, but strong impact on grade (rubric) and presentation.

### 2.1 ETL & data quality

| Status | Task | Why |
|--------|------|-----|
| `[ ]` | Load **`warehouse.agg_municipality_party_results`** and **`agg_district_results`** after facts | Faster analytics; schema already exists |
| `[ ]` | Staging **`processed`** flags + `stg_data_quality_issues` for failed rows | ETL audit trail |
| `[ ]` | Normalise territory codes / party aliases in staging | Fewer join mismatches with CAOP |
| `[ ]` | Official **CAOP shapefiles** (incl. Azores, Madeira) instead of continent-only fallback | §5.5 completeness |
| `[ ]` | `python -m pipeline.download_caop` + manual DGT ZIP documented in reconciliation | §7 data instructions |

### 2.2 Multi-election & organs

| Status | Task | Why |
|--------|------|-----|
| `[x]` | Second dataset **`aut_2017`** in `config.py` + full load (`election_id` per year) | §5.4 cross-election comparison; §6 extension |
| `[ ]` | **Assembleia Municipal (AM)** or **Junta de Freguesia (JF)** in ETL filters | §5.1 organs coverage |
| `[x]` | Flask: compare two election years on analytics page (`/api/charts/election_comparison`) | §5.4 comparisons |

### 2.3 Application & UX

| Status | Task | Why |
|--------|------|-----|
| `[ ]` | Map **AJAX**: select district on home map → update side panel table/chart without leaving page | §5.6 interaction (safer than navigation-only) |
| `[ ]` | Analytics dashboard reads **`warehouse`** facts (not only operational) | Shows star schema in app |
| `[ ]` | Pre-select municipality in navbar on municipality page | UX |
| `[x]` | **Seats** charts use populated `seat_result` (re-run ETL after pull) | Avoid misleading zeros |

### 2.4 Documentation & defence

| Status | Task | Why |
|--------|------|-----|
| `[ ]` | ETL flow diagram in `docs/er_diagrams/etl_flow_diagram.png` | Slides + report clarity |
| `[ ]` | One-page **demo checklist** for oral (who runs what live) | §7.2 |
| `[ ]` | Update [docs/REPORT_TEMPLATE.md](docs/REPORT_TEMPLATE.md) member list (Kathleen / actual team) | §7.1 accuracy |
| `[ ]` | `sql/06_sample_data.sql` renamed or README note — **validation only**, not seed data | Avoid evaluator confusion |

---

## 3. Optional (NICE TO HAVE)

Extensions beyond minimum; do only if time remains.

### 3.1 ETL extensions

| Task | Notes |
|------|--------|
| Dataset **`aut_2025`** / **`aut_2013`** (folders already under `etl/data/`) | §6 |
| **Parish (freguesia)** level in schema + ETL | §5.5 stronger groups |
| Default `run_etl.py` mode → **`full`** instead of `staging-only` | Fewer user errors |
| `[x]` | Remove legacy **`etl_pipeline.py`** wrapper | Cleanup |
| Materialized views for heavy aggregates | §6 |
| Automated ETL **unit tests** (row counts per phase) | Maintenance |

### 3.2 Application

| Task | Notes |
|------|--------|
| Export results **CSV** | Extension |
| User authentication | Out of scope per report |
| Plotly **interactive** dashboards | §3 |
| Real-time election night updates | Out of scope |

### 3.3 Repository hygiene

| Task | Notes |
|------|--------|
| `[x]` | Removed duplicate root docs; canonical: `README.md`, `docs/`, `etl/README.md`, `todo.md` | Clarity |
| `[x]` | **`tmp.txt`** removed; listed in `.gitignore` (no passwords in repo) | Security |
| CI job: schema load + ETL smoke on empty DB | Optional automation |

---

## 4. Already implemented (reference — do not re-do)

- [x] Modular ETL: `etl/run_etl.py`, `etl/pipeline/*` (extract, operational, geo, warehouse, post_load)
- [x] MVP: Autárquicas **2021**, organ **CM**, **municipality** level
- [x] `party_municipality_summary` refresh after load
- [x] Flask: `election_id`, election/municipality selectors, districts/municipality/analytics routes
- [x] GeoJSON APIs: `/api/map/districts`, `/api/map/municipalities/<district_id>`
- [x] Chart.js visualisations on multiple pages (supplement with Python charts for §5.5)

---

## 5. Suggested work order (before 4 June)

1. **MUST:** `seat_result` or documented mandate strategy + validation sample  
2. **MUST:** Run `sql/04`, capture outputs  
3. **MUST:** `docs/etl_reconciliation.md` + ER diagrams + screenshots  
4. **MUST:** `docs/report.pdf` + `slides/`  
5. **MUST:** Python Matplotlib/Plotly chart(s) + map interaction decision  
6. **SHOULD:** agg tables, oral demo script, warehouse in one analytics query  
7. **OPTIONAL:** second election year, islands CAOP  

---

## 6. Rubric mapping (40% project)

| Rubric (PDF §8) | Weight | Primary closure |
|-----------------|--------|-----------------|
| Data modelling | 20% | Report §5.1 + ER + indexes; `seat_result` |
| ETL + warehouse | 20% | ETL doc + reconciliation + demo load |
| Functions / triggers | 20% | `sql/03` + report + live demo |
| Analytical SQL | 20% | `sql/04` executed + findings + D'Hondt check |
| Frontend + spatial | 10% | Flask + maps + **Python charts** |
| Documentation | 10% | README + report + reproducibility |

---

*Last updated: June 2026*
