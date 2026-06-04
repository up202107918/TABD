# ETL reconciliation: CNE election data ↔ CAOP boundaries

**Project:** Election Analytics Platform (TABD) · **Assignment:** §5.2 staging, ETL, data warehouse  
**Primary dataset:** CNE Autárquicas 2021 (`aut_2021`) · **Organ / level:** Câmara Municipal (CM), municipality (`concelho`)  
**Related:** [etl/docs/source_inventory_2021.md](../etl/docs/source_inventory_2021.md) · [etl/docs/validation_samples_2021.md](../etl/docs/validation_samples_2021.md) · [etl/data/caop/README.md](../etl/data/caop/README.md)

---

## 1. Purpose

This document records how **Comissão Nacional de Eleições (CNE)** Excel results are aligned with **Direção-Geral do Território (DGT) CAOP** administrative boundaries in our ETL, including:

- identifier and naming strategy (no shared numeric key in MVP);
- files loaded vs used only for validation;
- known gaps (islands geometry, municipalities missing from mapa_1, quality-issue logging);
- post-load checks and how to reproduce them.

---

## 2. Data sources

| Source | Role | Location / access |
|--------|------|-------------------|
| **CNE Autárquicas 2021** | Votes, turnout, party/list columns | `etl/data/2021al_mapa_oficial/` (from [official ZIP](https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip)) |
| **DGT CAOP 2021** (preferred) | District / municipality polygons | Manual ZIP → `etl/data/caop/` · URL in `etl/config.py` (`CAOP_DOWNLOAD_URLS`) |
| **CAOP GeoJSON fallback** | Continent districts + municipalities when official ZIP fails | `python -m pipeline.download_caop` → [nmota/caop_GeoJSON](https://github.com/nmota/caop_GeoJSON) (derived from DGT WFS) |

**Election year vs boundaries:** Results are for **26 September 2021**. CAOP **2021** is the best match; fallback GeoJSON may reflect a slightly different vintage—geometry is matched by **name**, not by official concelho code.

---

## 3. CNE files: what ETL loads vs what we reconcile offline

### 3.1 Loaded by ETL (MVP)

| File | Content | Staging | Operational |
|------|---------|---------|-------------|
| **`mapa_1_resultados.xlsx`** (`mapa_I`, wide layout) | District header rows + CM municipality rows; turnout columns (`insc`, `vot`, `br`, `nul`) + party vote columns | `stg_election_results`, `stg_turnout_data` | `vote_result`, `turnout`, territories, parties/coalitions, candidacies |

**Note:** Turnout for CM municipalities comes from **`mapa_1`**, not from `mapa_anexo.xlsx`. The annex is present in the ZIP but **not parsed** in MVP (reserved if gaps are found).

**MVP row filter** (`etl/pipeline/extract.py` → `parse_wide_mapa_sheet`):

- `org = CM`
- empty `freguesia` (municipality-level chamber only)
- district name carried from header rows where `org` is empty

### 3.2 Skipped by ETL, used for reconciliation / validation

| File | Why skipped in load | How we use it |
|------|---------------------|---------------|
| **`mapa_2_perc_mandatos.xlsx`** | Vote % (`%` columns) + **official seat counts** (`M` columns) per list | Vote % cross-check in validation; **seats** → `operational.seat_result` via `etl/pipeline/load_seats.py` |
| **`mapa_3_eleitos.xlsx`** | Elected persons list; out of MVP aggregate scope | Not used |
| **`*.ods`** | Pipeline reads `.xls` / `.xlsx` only | Reference copies in ZIP |

### 3.3 `mapa_1` vs `mapa_2` (same municipalities, different semantics)

| Aspect | `mapa_1` | `mapa_2` |
|--------|----------|----------|
| **Primary fields** | Integer votes per list/party; turnout counts | Published **vote percentages** per list |
| **In database** | `vote_result.votes`; `turnout.*` | Not stored; % recomputed as `votes / sum(votes)` per municipality |
| **Parsing pitfall** | `coerce_integer` strips `.` (correct for vote counts) | Must **not** use `coerce_decimal` from ETL for % — it breaks decimals (documented in validation script) |
| **Party identifiers** | Column headers → acronyms via `party_code_to_acronym` / `PARTY_MAPPING` | Same list codes (e.g. Lisboa: **A**, **B**, not national PS/PSD) |
| **Mandates** | Loaded into `seat_result` from mapa_2 `M` columns | `allocation_method = 'CNE mapa_2'`; `total_seats_available` = sum of M per municipality |

**Reconciliation outcome (samples):** For Lisboa, Porto, and Barrancos, `mapa_1` votes and turnout match DB **0 mismatches**; `mapa_2` vote % and **seat counts** match `seat_result` **0 mismatches**. See [etl/docs/validation_samples_2021.md](../etl/docs/validation_samples_2021.md).

**Coverage:** ~308 municipalities in mapa_2; seat rows are inserted only where the municipality exists in `operational.municipality` (~258 loaded from mapa_1). ~50 concelhos present in mapa_2 but missing from mapa_1 extract have no `seat_result` (document as data gap, not allocation bug).

---

## 4. Territorial identifiers: CNE ↔ operational DB ↔ CAOP

There is **no single official concelho code** wired through the full pipeline in MVP. Reconciliation is **name-based**.

### 4.1 CNE (staging)

| Field | Source | Usage |
|-------|--------|--------|
| `distrito` | Text from `mapa_1` (district header row, then CM rows) | Staging + join key to municipalities |
| `concelho` | Municipality name on CM rows | Staging + join key |
| Column `cod` (index 0) | Present in workbook | **Not extracted** in wide parser |

Names are stored as in CNE (often **UPPERCASE** in Excel); operational load applies `title()` for display (`transform_operational.py`).

### 4.2 Operational database (generated keys)

| Entity | Code strategy | Name |
|--------|---------------|------|
| **District** | Fixed map `DISTRICT_CODES` (INE-style 01–18, 20 Açores, 30 Madeira) | `district_name` from CNE `distrito` |
| **Municipality** | `{district_code}{seq:02d}` per district (sequence from distinct CNE pairs in staging) | `municipality_name` from CNE `concelho` |

Implications:

- Municipality codes are **internal**, not necessarily identical to INE/DGT concelho codes.
- Two elections (e.g. 2017 + 2021) reuse the same territory rows; only election-scoped facts are replaced per `election_id`.

### 4.3 CAOP (geometry load)

Module: `etl/pipeline/transform_geo.py`.

| Step | Rule |
|------|------|
| Normalization | `normalize_key`: uppercase, strip accents (NFKD), collapse whitespace |
| **District** | Match CAOP attribute (`distrito`, `name`, …) → `operational.district.district_name` |
| **Municipality** | Match **(district, municipality)** pair; if unique, fallback to municipality name only |

Unmatched polygons are **skipped silently** (no row in `stg_data_quality_issues` yet). Count geometries after load:

```sql
SELECT COUNT(*) FROM operational.district WHERE geometry IS NOT NULL;
SELECT COUNT(*) FROM operational.municipality WHERE geometry IS NOT NULL;
```

Expected with **fallback GeoJSON**: on the order of **~18 districts** and **~280+ municipalities** on the **continent**; see [etl/README.md](../etl/README.md) sanity section.

---

## 5. Islands and continental coverage (CAOP gap)

| Region | In CNE `mapa_1` (votes/turnout) | In CAOP fallback GeoJSON | Map in Flask |
|--------|----------------------------------|---------------------------|--------------|
| **Continental Portugal** | Yes | Yes (`ContinenteDistritos.geojson`, `Portugal_Municipalities.geojson`) | Polygons + results |
| **Azores** | Yes (district codes 20 in `DISTRICT_CODES`) | **Not** in default fallback files | Results/tables work; **geometry often NULL** |
| **Madeira** | Yes (code 30) | **Not** in default fallback | Same as Azores |

**Mitigation (recommended for report/demo):**

1. Download official **CAOP 2021** shapefiles (all regions) from [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) into `etl/data/caop/`.
2. Re-run `run_etl.py --dataset aut_2021 --mode full` (or `reload-operational` if only geometry changed).

**Automatic download:** `python -m pipeline.download_caop` tries the official ZIP URL first; if it returns **404**, it fetches the GitHub GeoJSON fallback and logs that fact.

---

## 6. Party / list naming

| Layer | Behaviour |
|-------|-----------|
| CNE wide headers | Short codes (`ps`, `ppd_psd`, single-letter lists in large cities) |
| Staging `candidatura` | Normalized acronym via `party_code_to_acronym` and `PARTY_MAPPING` in `etl/config.py` |
| Coalitions | Detected by `/` in acronym; stored as `coalition` + members |

**Reconciliation:** Compare per-municipality vote totals and %, not necessarily national party labels. Lisboa uses list codes **A, B, …** in both `mapa_1` and `mapa_2`; DB stores the same codes as party acronyms.

---

## 7. Cleaning and transformations (summary)

| Issue | Handling |
|-------|----------|
| Wide → long votes | Unpivot party columns in `parse_wide_mapa_sheet` |
| Valid votes | `votos_validos = votantes - brancos - nulos` at extract; stored in staging turnout |
| Zero / null votes | Omitted from `stg_election_results` (not inserted) |
| Duplicate territory names | `ON CONFLICT` on `district_code` / `municipality_code` updates names |
| Failed workbooks | Logged; run continues (`rows_rejected` in run log) |
| Audit triggers during bulk load | `session_replication_role = replica` in operational transform (triggers apply on normal inserts) |
| Quality issue table | `staging.stg_data_quality_issues` exists in DDL; **not populated** in MVP |

---

## 8. Warehouse load (brief)

After operational load and optional geometry:

- Dimensions `dim_*` and facts `fact_election_result`, `fact_turnout` are built from operational joins (`load_warehouse.py`).
- `seats_obtained` in facts comes from `operational.seat_result` → **0** while that table is empty.
- Pre-aggregate tables `warehouse.agg_*` are **not** filled after truncate (schema only).

---

## 9. Multi-election note (2017 + 2021)

`etl/config.py` defines `aut_2017` and `aut_2021`. Each `run_etl.py --mode full` run:

- replaces operational rows for that **`election_id`** only;
- does not truncate global territory tables.

Territory names must stay consistent across years for the same concelho; reconciliation for 2017 uses the same name-matching rules (2017 workbooks may use `mapa_i` naming—see `workbook_include` in config).

---

## 10. Verification checklist (reproducible)

From repository root (PostgreSQL schemas applied, `DB_*` set — see [README.md](../README.md)):

```powershell
cd etl
..\.venv\Scripts\python.exe -m pipeline.download_caop
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2017 --mode full
..\.venv\Scripts\python.exe run_etl.py --dataset aut_2021 --mode full
cd ..
..\.venv\Scripts\python.exe scripts\smoke_check.py
..\.venv\Scripts\python.exe scripts\validate_samples_2021.py
```

**Outputs:**

| Check | Artifact |
|-------|----------|
| CNE `mapa_1` vs DB votes/turnout | [etl/docs/validation_samples_2021.md](../etl/docs/validation_samples_2021.md) |
| CNE `mapa_2` % vs DB derived % | Same file |
| D'Hondt vs sample expectations | Same file (`allocate_seats_dhondt`, 7 seats in script) |
| SQL demos | `docs/sql_outputs/demo_results.txt` (after `sql/04` / `sql/07`) |

**Staging sanity:**

```sql
SELECT COUNT(*) FROM staging.stg_election_results;
SELECT COUNT(*) FROM staging.stg_turnout_data;
SELECT status, rows_staged, rows_loaded FROM staging.stg_etl_run_log ORDER BY run_id DESC LIMIT 1;
```

---

## 11. Known limitations (honest scope for §5.2)

1. **No CAOP↔CNE numeric key** — matching by normalized district/municipality names only.  
2. **`mapa_3` not loaded** — elected officials list out of scope; seats come from mapa_2 `M`, not mapa_3.  
3. **`mapa_anexo` not loaded** — turnout taken from `mapa_1`.  
4. **Islands** — likely missing polygons with default GeoJSON fallback.  
5. **`stg_data_quality_issues`** — not written by pipeline yet.  
6. **CM only, no freguesia** — AM/JF rows filtered out in extract.  

---

## 12. External references

| Resource | Citation |
|----------|----------|
| CNE Autárquicas 2021 results | [cne.pt — Eleições Autárquicas 2021](https://www.cne.pt/content/eleicoes-autarquicas-2021) |
| DGT CAOP | [Cartografia CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) |
| GeoJSON fallback | [nmota/caop_GeoJSON](https://github.com/nmota/caop_GeoJSON) — use with statement that primary authority is DGT CAOP |

---

*Document version: June 2026 · aligns with MVP ETL in `etl/pipeline/`.*
