# CNE Autárquicas 2021 — source file inventory

Dataset folder: `etl/data/2021al_mapa_oficial/`

## Files used by ETL (MVP)

| File | Sheet | Format | Staging target | Notes |
|------|-------|--------|----------------|-------|
| `mapa_1_resultados.xlsx` | `mapa_I` | **Wide** (party columns) | `stg_election_results`, `stg_turnout_data` | Main results + turnout per row; CM rows only (~308 municipalities) |
| `mapa_anexo.xlsx` | (varies) | Not loaded in MVP | — | Supplementary tables; revisit if turnout gaps found |

## Files skipped (MVP)

| File | Reason |
|------|--------|
| `mapa_2_perc_mandatos.xlsx` | Mandate percentages; votes/mandates already in mapa_1 |
| `mapa_3_eleitos.xlsx` | Elected officials list; not needed for vote aggregates |
| `*.ods` | Not read by pipeline (Excel only) |

## `mapa_1` layout (wide)

| Row | Content |
|-----|---------|
| 0–1 | Title rows (ignored) |
| 2 | Group labels: `org`, `insc`, `vot`, `br`, `nul`, `partidos` |
| 3 | Column headers: `cod`, `conc`, `freg`, then party codes (`ps`, `ppd_psd`, …) |
| 4+ | Data rows |

**Fixed columns (0-based index):**

| Index | Field | Staging |
|-------|-------|---------|
| 0 | District/municipality code | — |
| 1 | `conc` — district name (header row) or municipality name | `distrito` / `concelho` |
| 2 | `freg` — parish (often empty for CM) | `freguesia` |
| 3 | Organ code (`CM`, `AM`, `AF`, …) | `orgao` |
| 4 | Registered voters (`insc`) | `eleitores_inscritos` |
| 5 | Votes cast (`vot`) | `votantes` |
| 6 | Blank votes (`br`) | `votos_brancos` |
| 7 | Null votes (`nul`) | `votos_nulos` |
| 8+ | Party vote counts | `candidatura` + `votos` (unpivot) |

**District name:** rows with empty `org` and no turnout numbers update the current district; following `CM` rows use that district.

**MVP filter:** only `org = CM` and empty `freg` (municipality-level chamber results).

## Long format (other years / files)

Some CNE workbooks use long columns (`candidatura`, `votos`, …). The extractor still supports them via header detection when present.
