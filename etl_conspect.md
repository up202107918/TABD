# Plan kompletnego ETL pod końcową aplikację

Plan podzielony na **fazy z numerowanymi krokami**. Każdy krok ma cel, pliki, kryteria „done” i gotową frazę do wklejenia w czacie (np. *„Zrób krok 3.2”*).

**Stan projektu (punkt wyjścia):** `etl/etl_pipeline.py` ładuje dane tylko do **staging**. Schematy `operational`, `warehouse` i `staging` są w SQL. Aplikacja Flask czyta `operational.*` z hardcode `election_year = 2021`.

---

## Cel końcowy (Definition of Done)

Po pełnym ETL aplikacja Flask (`app/app.py`) ma działać **bez mocków** na danych z bazy:

| Wymaganie aplikacji | Co musi istnieć w DB |
|---------------------|----------------------|
| Lista dystryktów + frekwencja | `operational.district`, `municipality`, `turnout` (organ `CM`) |
| Szczegóły concelho | `candidacy` + `vote_result` + opcjonalnie `seat_result` |
| Mapa dystryktów | `district.geometry IS NOT NULL` + `turnout` |
| Mapa concelhos | `municipality.geometry` + winner z `vote_result.is_winner` |
| Wykresy / analytics | agregaty z operational (warehouse opcjonalnie na start) |
| Przyszły wybór roku | wiersz w `operational.election` per rok (2021 jako MVP) |

**MVP ETL:** Autárquicas **2021**, organ **CM** (Câmara Municipal), poziom **concelho** (bez freguesii w pierwszej iteracji).

**Rozszerzenie:** 2013/2017/2025 z `etl/data/` po ustabilizowaniu 2021.

---

## Architektura docelowa (docelowy układ plików)

Obecny monolit `etl/etl_pipeline.py` → podział:

```
etl/
├── config.py                 # DB, ścieżki, mapowania partii, datasety
├── run_etl.py                # jedyny punkt wejścia (CLI)
├── pipeline/
│   ├── __init__.py
│   ├── runner.py             # orchestracja faz + stg_etl_run_log
│   ├── extract.py            # Excel → staging (obecna logika)
│   ├── transform_geo.py      # CAOP shapefile → operational + staging geo
│   ├── transform_dims.py     # staging → election, district, municipality, party
│   ├── transform_facts.py    # staging → candidacy, vote_result, seat_result, turnout
│   ├── load_warehouse.py     # operational → warehouse + agregaty
│   └── quality.py            # walidacja + stg_data_quality_issues
├── data/                     # bez zmian koncepcji
└── docs/etl_reconciliation.md  # uzgodnienia CNE ↔ CAOP (wymóg zadania)
```

**Zasada:** każda faza = osobny moduł + test SQL. Nie przechodzimy dalej, dopóki liczby w bazie nie spełniają kryteriów kroku.

---

## Faza 0 — Przygotowanie i linia bazowa

### Krok 0.1 — Środowisko i schematy

**Cel:** czysta baza gotowa pod pełny pipeline.

**Komendy** (z `tmp.txt`):

```powershell
$env:DB_NAME="election_analytics"
$env:DB_USER="postgres"
$env:DB_PASSWORD="12345"

psql -U postgres -h localhost -d election_analytics -f sql/01_operational_schema.sql
psql -U postgres -h localhost -d election_analytics -f sql/02_warehouse_schema.sql
psql -U postgres -h localhost -d election_analytics -f sql/03_functions_triggers.sql
psql -U postgres -h localhost -d election_analytics -f sql/05_staging_schema.sql
```

**Done gdy:** schematy `operational`, `warehouse`, `staging` istnieją bez błędów.

**Fraza do agenta:** *„Krok 0.1 — zweryfikuj i napraw błędy przy ładowaniu schematów SQL.”*

---

### Krok 0.2 — Inwentaryzacja plików CNE 2021 ✅

**Cel:** wiedzieć, które arkusze dają wyniki vs frekwencję.

**Działania:**

1. Przejrzeć `etl/data/2021al_mapa_oficial/mapa_1_resultados.xlsx` (nagłówki, poziom: distrito/concelho/orgao).
2. Sprawdzić, czy `eleitores_inscritos` / `votantes` są w mapa_1, mapa_anexo czy innym pliku.
3. Zapisać w `etl/docs/source_inventory_2021.md` (1 strona): plik → typ arkusza → kolumny.

**Done gdy:** wiadomo, które pliki trafiają do `stg_election_results` vs `stg_turnout_data`.

**Fraza:** *„Krok 0.2 — przeanalizuj strukturę map CNE 2021 i utwórz source_inventory_2021.md.”*

---

### Krok 0.3 — Test obecnego Extract (staging) ✅

**Cel:** potwierdzić, że staging działa na 2021.

```powershell
cd etl
python etl_pipeline.py
```

**SQL walidacji:**

```sql
SELECT election_year, COUNT(*) FROM staging.stg_election_results GROUP BY 1 ORDER BY 1;
SELECT election_year, COUNT(*) FROM staging.stg_turnout_data GROUP BY 1 ORDER BY 1;
SELECT COUNT(*) FROM staging.vw_stg_missing_data;
```

**Done gdy:** `stg_election_results` dla 2021 ma dziesiątki tysięcy wierszy (rząd wielkości: setki concelhów × listy); brak masowych NULL w `distrito`, `concelho`, `candidatura`, `votos`.

**Uwaga:** obecny extract ładuje **wszystkie** lata z `etl/data/` — w Fazie 1 trzeba to ograniczyć do wybranego datasetu.

**Fraza:** *„Krok 0.3 — uruchom staging i napraw extract, jeśli 2021 ma 0 wierszy.”*

---

## Faza 1 — Orchestracja i konfiguracja datasetów

### Krok 1.1 — Konfiguracja datasetów w `config.py` ✅

**Cel:** jeden przebieg ETL = jeden rok wyborów.

Dodać np.:

```python
DATASETS = {
    'aut_2021': {
        'election_year': 2021,
        'election_date': '2021-09-26',
        'election_type_code': 'AUT',
        'data_dirs': ['2021al_mapa_oficial'],
        'primary_organ': 'CM',
    },
}
DEFAULT_DATASET = 'aut_2021'
```

**Done:** `get_dataset_dirs()` zwraca tylko foldery z aktywnego datasetu (nie miesza 2013+2017+2025).

**Fraza:** *„Krok 1.1 — dodaj DATASETS i filtruj foldery po DEFAULT_DATASET.”*

---

### Krok 1.2 — `run_etl.py` + `pipeline/runner.py` ✅

**Cel:** przebieg z logowaniem w `stg_etl_run_log`.

**Fazy runnera:**

1. `clear_staging` (opcjonalnie tylko dla datasetu)
2. `extract`
3. `transform_geography`
4. `transform_dimensions`
5. `transform_facts`
6. `load_warehouse`
7. `post_load` (summary, quality report)

**CLI:**

```powershell
python run_etl.py --dataset aut_2021 --mode full
python run_etl.py --dataset aut_2021 --mode staging-only
python run_etl.py --dataset aut_2021 --mode reload-operational
```

**Done:** każdy run zapisuje `rows_*` i `status` w `stg_etl_run_log`.

**Fraza:** *„Krok 1.2 — utwórz run_etl.py i runner z logowaniem ETL.”*

---

### Krok 1.3 — Strategia przeładowania (idempotentność)

**Cel:** pipeline można uruchomić wielokrotnie bez duplikatów.

**Zasada dla `full`:**

1. `TRUNCATE` staging (lub DELETE po `election_year`)
2. Extract → staging
3. Dla operational: `DELETE` dane wyboru `election_year = X` (candidacy, vote_result, seat_result, turnout, coalition…) **albo** `TRUNCATE` całego operational + pełny reload
4. Warehouse: `TRUNCATE` fact + dim (oprócz `dim_time`) + przeładuj

**Done:** drugi `full` daje te same liczby wierszy co pierwszy.

**Fraza:** *„Krok 1.3 — zaimplementuj bezpieczne truncate/delete per election_year.”*

---

## Faza 2 — Extract (staging) — utwardzenie

### Krok 2.1 — Klasyfikacja plików mapa ✅

**Cel:** nie ładować mapa_3 (eleitos) i mapa_2 (procenty) jako duplikatów wyników.

| Plik | Akcja w Extract |
|------|-----------------|
| `mapa_1` / `Parte1` | **LOAD** → `stg_election_results` |
| `mapa_anexo` | **LOAD** tylko jeśli ma frekwencję / turnout |
| `mapa_2`, `mapa_3` | **SKIP** w MVP (mandaty już w mapa_1) |
| `.ods` | SKIP (tylko xls/xlsx) |

**Done:** brak dubli w `vw_stg_potential_duplicates` dla tego samego concelho+lista.

**Fraza:** *„Krok 2.1 — filtruj workbooks po nazwie mapa i typie arkusza.”*

---

### Krok 2.2 — Normalizacja terytoriów i organów w staging

**Cel:** spójne klucze przed loadem operacyjnym.

W `extract.py` / helperach:

- `normalize_territory_name()` — trim, wielokrotne spacje, warianty „Ilha“ / Açores
- `normalize_organ()` → `CM` / `AM` / `JF` (mapowanie z `ORGAN_CODES` w config)
- `election_year` z ścieżki pliku (już jest jako generated column)

**Done:** ≤5% wierszy bez dopasowania concelho (reszta → `stg_data_quality_issues`).

**Fraza:** *„Krok 2.2 — normalizacja nazw distrito/concelho/orgao w extract.”*

---

### Krok 2.3 — Mapowanie partii

**Cel:** stabilne `party_acronym` w operational.

1. Z unikalnych `candidatura` w staging zbudować `stg_party_mapping` (auto + ręczne overrides w CSV/JSON).
2. Rozróżnić koalicje (np. zawiera `/`) vs pojedyncze partie.
3. Użyć `PARTY_MAPPING` + `get_or_create_party` z SQL tam, gdzie sensowne.

**Done:** top 20 partii z CNE ma sensowny acronym; reszta w quality log, nie crash.

**Fraza:** *„Krok 2.3 — auto-wypełnij stg_party_mapping i koalicje.”*

---

## Faza 3 — Geografia (CAOP → PostGIS)

### Krok 3.1 — Pobranie CAOP

**Cel:** działające granice dystryktów i concelhów.

**Opcje (wybierz jedną w implementacji):**

- A) Ręcznie: ZIP z [dgterritorio.gov.pt](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) → `etl/data/caop/`
- B) Skrypt `scripts/download_caop.py` z aktualnym URL (stary link dawał 404)

**Done:** lokalny folder ze shapefile (np. concelhos + distritos).

**Fraza:** *„Krok 3.1 — napraw pobieranie CAOP i opisz w README.”*

---

### Krok 3.2 — Load geografii do operational

**Cel:** `district.geometry` i `municipality.geometry` wypełnione.

**Implementacja:** `transform_geo.py` z `geopandas` + `psycopg2` (dodać do `requirements.txt`) **lub** `shp2pgsql` jako subprocess.

**Mapowanie:**

- CAOP kod INE (4 cyfry concelho, 2 dystrykt) ↔ `municipality_code` / `district_code`
- Nazwy tylko jako fallback (fuzzy match → quality issue)

**Done (SQL):**

```sql
SELECT COUNT(*) FROM operational.district WHERE geometry IS NOT NULL;   -- oczekiwane: ~18–20
SELECT COUNT(*) FROM operational.municipality WHERE geometry IS NOT NULL; -- oczekiwane: ~300+
```

**Fraza:** *„Krok 3.2 — załaduj geometrie CAOP do district i municipality.”*

---

### Krok 3.3 — Słownik terytorialny z CNE (bez CAOP) ✅

**Cel:** każdy concelho ze staging ma wiersz w `municipality`, nawet jeśli geometria chwilowo NULL.

1. Z `stg_election_results` wyciągnąć unikalne pary (distrito, concelho).
2. Utworzyć `district` (kod z `extract_district_code` w staging SQL lub Python).
3. Utworzyć `municipality` z tymczasowym kodem (hash/normalized name) jeśli brak INE — oznaczyć w quality.

**Done:** 0 orphan `candidacy.municipality_id` po Fazie 5.

**Fraza:** *„Krok 3.3 — utwórz district/municipality ze staging przed faktami.”*

---

## Faza 4 — Transform → operational (wymiary)

### Krok 4.1 — Wiersz wyborów ✅

**Cel:** `operational.election` dla 2021.

```sql
INSERT INTO operational.election (election_type_id, election_date, election_year, description)
SELECT et.election_type_id, '2021-09-26', 2021, 'Autárquicas 2021'
FROM operational.election_type et WHERE et.type_code = 'AUT'
ON CONFLICT DO NOTHING;
```

**Done:** `SELECT election_id FROM operational.election WHERE election_year = 2021` zwraca 1 wiersz.

**Fraza:** *„Krok 4.1 — load election z config datasetu.”*

---

### Krok 4.2 — Partie i koalicje ✅

**Cel:** `party`, `coalition`, `coalition_member` (opcjonalnie member w MVP).

Z `stg_party_mapping` + unikalne `candidatura`:

- pojedyncza partia → `party`
- koalicja → `coalition` (+ `election_id`)
- `candidacy` w Fazie 5 dostaje `party_id` XOR `coalition_id`

**Done:** liczba partii/koalicji zgodna z CNE (~15–30 akronimów na 2021).

**Fraza:** *„Krok 4.2 — transform partii i koalicji do operational.”*

---

## Faza 5 — Transform → operational (fakty)

### Krok 5.1 — Candidacy + vote_result (CM, concelho) ✅

**Cel:** wypełnić to, co czyta `municipality_detail`.

**Klucz naturalny kandydatury:**

`(election_id, organ_id=CM, municipality_id, party_id|coalition_id, numero_candidatura?)`

**Z `stg_election_results` (mapa_1):**

- `votos` → `vote_result.votes_obtained`
- `percentagem` → `vote_percentage` (trigger też może przeliczyć)
- `mandatos` → `seat_result.seats_obtained` (jeśli w mapa_1)

**Agregacja:** tylko wiersze z `concelho IS NOT NULL` i `orgao` = CM (lub NULL → CM w MVP).

**Done (SQL):**

```sql
SELECT COUNT(*) FROM operational.candidacy c
JOIN operational.election e ON e.election_id = c.election_id
WHERE e.election_year = 2021;
-- oczekiwane: tysiące (rzęd wielkości: ~308 concelhos × listy)
```

**Fraza:** *„Krok 5.1 — load candidacy i vote_result z staging dla CM 2021.”*

---

### Krok 5.2 — seat_result

**Cel:** wykresy z mandatami w analytics.

- Jeśli `mandatos` w staging: bezpośredni insert.
- Opcjonalnie: weryfikacja przez `allocate_seats_dhondt` (sample 5 concelhos vs CNE).

**Done:** `seat_result` powiązane 1:1 z `candidacy` gdzie są mandaty.

**Fraza:** *„Krok 5.2 — load seat_result i opcjonalna walidacja D'Hondt.”*

---

### Krok 5.3 — Turnout (frekwencja) ✅

**Cel:** mapa kolorów i karty statystyk.

Z `stg_turnout_data` → `operational.turnout`:

- `(election_id, organ_id=CM, municipality_id)`
- `registered_voters`, `votes_cast`, `valid_votes`, `blank_votes`, `null_votes`
- trigger `trg_turnout_percentages` uzupełni procenty

**Done:**

```sql
SELECT COUNT(*) FROM operational.turnout t
JOIN operational.election e ON e.election_id = t.election_id
WHERE e.election_year = 2021 AND t.municipality_id IS NOT NULL;
-- oczekiwane: ~300
```

**Fraza:** *„Krok 5.3 — load turnout z staging; jeśli brak danych, wskaż źródło w mapa_anexo.”*

---

### Krok 5.4 — Pola pochodne (ranking, zwycięzca) ✅

**Cel:** mapa concelhos pokazuje `winner`; lista posortowana.

W Pythonie lub SQL (`window functions`):

- `ranking_position` per `(municipality_id, organ_id, election_id)` po `votes_obtained`
- `is_winner = true` dla rank = 1

**Done:** API `/api/map/municipalities/<id>` zwraca sensownego `winner`.

**Fraza:** *„Krok 5.4 — ustaw ranking_position i is_winner.”*

---

### Krok 5.5 — Oznacz staging jako processed

**Cel:** audyt ETL.

`UPDATE staging.stg_* SET processed = true, error_message = NULL` dla załadowanych `row_id`; błędy → `error_message` + `stg_data_quality_issues`.

**Fraza:** *„Krok 5.5 — processed flags i raport jakości.”*

---

## Faza 6 — Post-load operational

### Krok 6.1 — `party_municipality_summary`

**Cel:** zgodność z procedurą w `03_functions_triggers.sql`.

```sql
CALL operational.refresh_party_municipality_summary(<election_id>);
```

**Fraza:** *„Krok 6.1 — odśwież party_municipality_summary po loadzie.”*

---

### Krok 6.2 — Walidacja liczb vs CNE (próbka)

**Cel:** obrona na prezentacji.

Ręcznie 3 concelhos (np. Lisboa, Porto, jedno małe):

- suma głosów list ≈ głosy ważne z frekwencji
- mandaty ≈ mapa CNE

Zapisać wynik w `etl/docs/validation_samples_2021.md`.

**Fraza:** *„Krok 6.2 — walidacja 3 concelhos vs oficjalne wyniki.”*

---

## Faza 7 — Warehouse

### Krok 7.1 — Wymiary z operational

**Cel:** wypełnić `dim_election`, `dim_organ`, `dim_district`, `dim_municipality`, `dim_party`.

Kolejność: district → municipality → election/organ/party (zgodnie z FK).

**Done:**

```sql
SELECT COUNT(*) FROM warehouse.dim_municipality;
SELECT COUNT(*) FROM warehouse.dim_party;
```

**Fraza:** *„Krok 7.1 — populate warehouse dimensions.”*

---

### Krok 7.2 — `fact_election_result` i `fact_turnout`

**Cel:** star schema gotowa pod `04_analytical_queries.sql` i przyszłe raporty.

INSERT z join operational + mapowanie kluczy surrogate (`*_key`).

**Done:** fakty > 0; `vw_complete_results` zwraca wiersze.

**Fraza:** *„Krok 7.2 — populate fact_election_result i fact_turnout.”*

---

### Krok 7.3 — Agregaty `agg_*`

**Cel:** szybkie zapytania analityczne.

Przeliczenie z faktów lub SQL GROUP BY → `agg_municipality_party_results`, `agg_district_results`.

**Fraza:** *„Krok 7.3 — wypełnij agg_municipality_party_results i agg_district_results.”*

---

## Faza 8 — Integracja z aplikacją (poza ETL, ale zależna)

Te kroki **nie są w ETL**, ale ETL pod nie przygotowuje dane:

| Krok | Opis |
|------|------|
| 8.1 | Parametr `election_year` / `election_id` w routach Flask zamiast hardcode 2021 |
| 8.2 | Dropdown wyborów + concelho w UI |
| 8.3 | Mapa: przeładowanie GeoJSON po zmianie roku |

**Fraza:** *„Krok 8.1 — podłącz election_id z query string w app.py.”*

ETL musi wcześniej dostarczyć wiele wierszy w `election`, jeśli ładujecie 2013/2017/2025.

---

## Faza 9 — Rozszerzenia (po MVP)

| Krok | Opis |
|------|------|
| 9.1 | Dataset `aut_2017`, `aut_2013` — ten sam pipeline, inny folder |
| 9.2 | Organy AM / JF (osobne filtry w transform_facts) |
| 9.3 | Freguesie (parish) — jeśli mapa_1 ma poziom freguesia |
| 9.4 | `docs/etl_reconciliation.md` — finalna dokumentacja dla raportu |

---

## Kolejność pracy z agentem (rekomendowana ścieżka)

```mermaid
flowchart LR
    F0[Faza 0: baseline] --> F1[Faza 1: orchestracja]
    F1 --> F2[Faza 2: extract]
    F2 --> F33[Faza 3.3: słownik CNE]
    F33 --> F32[Faza 3.2: CAOP geo]
    F32 --> F4[Faza 4: wymiary]
    F4 --> F5[Faza 5: fakty]
    F5 --> F6[Faza 6: post-load]
    F6 --> F7[Faza 7: warehouse]
    F7 --> F8[Faza 8: Flask]
```

**Minimalna ścieżka do działającej mapy + concelho:**

`0 → 1 → 2 → 3.3 → 4 → 5 → 6.4 → 8` (CAOP 3.2 równolegle lub zaraz po 3.3).

---

## Checklist SQL po pełnym MVP (`aut_2021`)

Uruchom po `python run_etl.py --dataset aut_2021 --mode full`:

```sql
-- 1. Wybory
SELECT * FROM operational.election WHERE election_year = 2021;

-- 2. Terytoria
SELECT COUNT(*) AS districts FROM operational.district;
SELECT COUNT(*) AS municipalities FROM operational.municipality;
SELECT COUNT(*) AS with_geom FROM operational.municipality WHERE geometry IS NOT NULL;

-- 3. Wyniki CM
SELECT COUNT(*) AS candidacies
FROM operational.candidacy c
JOIN operational.election e ON e.election_id = c.election_id
JOIN operational.electoral_organ o ON o.organ_id = c.organ_id
WHERE e.election_year = 2021 AND o.organ_code = 'CM';

-- 4. Frekwencja
SELECT ROUND(AVG(turnout_percentage), 2) FROM operational.turnout t
JOIN operational.election e ON e.election_id = t.election_id
WHERE e.election_year = 2021;

-- 5. Warehouse
SELECT COUNT(*) FROM warehouse.fact_election_result;
SELECT COUNT(*) FROM warehouse.fact_turnout;

-- 6. Jakość
SELECT severity, COUNT(*) FROM staging.stg_data_quality_issues
GROUP BY severity;
```

**Sukces MVP:** candidacies > 1000, municipalities > 280, turnout > 280, with_geom > 0 (idealnie > 280).

---

## Zależności Python do dodania (Faza 3)

W `requirements.txt` (przy CAOP w Pythonie):

- `geopandas`
- opcjonalnie `fiona`

---

## Jak z tym pracować w kolejnych sesjach

1. Zacznij od **„Krok 0.3”** jeśli staging już działa, albo **„Krok 0.1”** od zera.
2. Jedna sesja = **jeden krok** (max dwa małe, np. 4.1+4.2).
3. Po każdym kroku: podaj output SQL z checklisty.
4. Nie przechodź do warehouse (Faza 7), dopóki Faza 5 nie przejdzie checklisty MVP.

---

## Propozycja pierwszego kroku realizacji

**Krok 1.1 + 1.2** — `DATASETS`, `run_etl.py`, `pipeline/runner.py` z fazami (extract działa, transform jako stuby) + log w `stg_etl_run_log`.

**Fraza:** *„Zrób Krok 1.1 i 1.2 z etl_conspect.md.”*

---

*Ostatnia aktualizacja planu: czerwiec 2026*
