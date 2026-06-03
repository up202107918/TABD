# Project backlog

Single place to track remaining work. **ETL MVP (2021) is done** — see [etl/README.md](etl/README.md) for what is implemented.

---

## ETL (optional extensions)

| Item | Priority | Notes |
|------|----------|--------|
| Load `seat_result` from `mapa_2` / `mandatos` in staging | Medium | Schema exists; facts load with `seats_obtained = 0` today |
| Populate `warehouse.agg_*` tables | Low | Tables truncated on warehouse load; facts are enough for analytics SQL |
| `processed` flags + `stg_data_quality_issues` | Low | Audit trail in staging |
| Staging normalisation (territory codes, party aliases) | Low | `etl/docs/source_inventory_2021.md` |
| Validation sample vs CNE (3 municipalities) | Medium | For presentation / report — `etl/docs/validation_samples_2021.md` |
| `docs/etl_reconciliation.md` | **High (report)** | Required by assignment: CNE names/codes vs CAOP |
| Datasets `aut_2013`, `aut_2017`, `aut_2025` | Low | Folders exist under `etl/data/`; add entries in `config.py` |
| Organs AM / JF, parish level | Low | Out of MVP scope |
| Official CAOP shapefiles (Azores, Madeira) | Low | Fallback GeoJSON is continent-focused |
| Default CLI mode → `full` | Low | Today default is `staging-only` in `run_etl.py` |

---

## Web application

| Item | Priority | Notes |
|------|----------|--------|
| Pre-select municipality in navbar when on municipality page | Low | UX polish |
| Warehouse-backed analytics page | Low | Currently reads `operational` |
| Export results (CSV) | Low | Extension idea |

---

## Documentation & deliverables (assignment)

| Item | Priority | Notes |
|------|----------|--------|
| `docs/report.pdf` | **High** | Technical report |
| `docs/er_diagrams/` | **High** | Operational + warehouse + ETL flow |
| `slides/` presentation | **High** | Oral exam 5 June 2026 |
| Update README team section | Low | Remove placeholder “Example” block |
| `sql/06_sample_data.sql` | — | Validation queries, not seed data — do not load as “sample data” |

---

## Database / SQL (verify before defence)

| Item | Notes |
|------|--------|
| Run / demo `sql/04_analytical_queries.sql` | D'Hondt, ROLLUP, CUBE, window functions |
| Confirm triggers on fresh load | Turnout percentages, audit (ETL uses `session_replication_role = replica` during bulk load) |

---

## Done (reference)

- Modular ETL: `run_etl.py` + `etl/pipeline/*`
- MVP dataset: Autárquicas 2021, organ CM, municipality level
- Staging → operational → warehouse facts + geo + `party_municipality_summary`
- Flask: `election_id` query param, election/municipality selectors, maps & charts
