# Validation samples — Autárquicas 2021 (CM)

Generated: 2026-06-03 15:42 UTC  
Sources: `mapa_1_resultados.xlsx` (votes/turnout), `mapa_2_perc_mandatos.xlsx` (vote % + seat counts), `operational.seat_result`, function `allocate_seats_dhondt(..., 7)` (demo only).

## Sample municipalities

| Municipality (DB) | CNE `concelho` | Role |
|-------------------|----------------|------|
| Lisboa | LISBOA | large capital |
| Porto | PORTO | large city |
| Barrancos | BARRANCOS | small municipality (Beja, ~1.3k registered voters) |

## Lisboa (large capital)

District (CNE row): **LISBOA** · DB: **Lisboa**

### Turnout (mapa_1 vs DB)

| Metric | CNE mapa_1 | DB `turnout` | Match |
|--------|------------|--------------|-------|
| Registered | 476050 | 476050 | OK |
| Votes cast | 242743 | 242743 | OK |
| Valid votes | 235298 | 235298 | OK |
| Blank | 4823 | 4823 | OK |
| Null | 2622 | 2622 | OK |

Sum party votes: CNE **235298** · DB **235298** · OK  
Valid votes check: sum ≤ valid → CNE True, DB True

### Votes by party/list

**Vote mismatches:** 0 / 12 parties

| Party | CNE | DB | Status |
|-------|-----|-----|--------|
| A | 83185 | 83185 | OK |
| B | 80907 | 80907 | OK |
| BE | 15057 | 15057 | OK |
| CDU | 25550 | 25550 | OK |
| CH | 10730 | 10730 | OK |
| D | 864 | 864 | OK |
| E | 338 | 338 | OK |
| IL | 10213 | 10213 | OK |
| NC | 494 | 494 | OK |
| PAN | 6625 | 6625 | OK |
| PDR | 319 | 319 | OK |
| VP | 1016 | 1016 | OK |

### Seats (mapa_2 M columns vs `seat_result`)

**Seat mismatches:** 0 / 4 parties · CNE council total: **17** seats

| Party | mapa_2 M | DB `seat_result` | Status |
|-------|----------|------------------|--------|
| A | 7 | 7 | OK |
| B | 7 | 7 | OK |
| BE | 1 | 1 | OK |
| CDU | 2 | 2 | OK |

### D'Hondt demo (`allocate_seats_dhondt`, 7 seats — ex10.sql pattern)

| Party | Votes | Seats |
|-------|-------|-------|
| A | 83185 | 3 |
| B | 80907 | 3 |
| CDU | 25550 | 1 |

### mapa_2 vote % vs DB (derived from valid votes)

**mapa_2 % mismatches:** 0 / 12 parties

| Party | mapa_2 % | DB vote % | Status |
|-------|----------|-----------|--------|
| A | 35.35% | 35.35% | OK |
| B | 34.38% | 34.38% | OK |
| BE | 6.4% | 6.4% | OK |
| CDU | 10.86% | 10.86% | OK |
| CH | 4.56% | 4.56% | OK |
| D | 0.37% | 0.37% | OK |
| E | 0.14% | 0.14% | OK |
| IL | 4.34% | 4.34% | OK |
| NC | 0.21% | 0.21% | OK |
| PAN | 2.82% | 2.82% | OK |
| PDR | 0.14% | 0.14% | OK |
| VP | 0.43% | 0.43% | OK |

**Top quotients (`demonstrate_dhondt`):** see `sql/07_demo_queries.sql`.


## Porto (large city)

District (CNE row): **PORTO** · DB: **Porto**

### Turnout (mapa_1 vs DB)

| Metric | CNE mapa_1 | DB `turnout` | Match |
|--------|------------|--------------|-------|
| Registered | 207129 | 74295 | **MISMATCH** |
| Votes cast | 101179 | 49451 | **MISMATCH** |
| Valid votes | 97796 | 47671 | **MISMATCH** |
| Blank | 2253 | 960 | **MISMATCH** |
| Null | 1130 | 820 | **MISMATCH** |

Sum party votes: CNE **97796** · DB **47671** · **MISMATCH**  
Valid votes check: sum ≤ valid → CNE True, DB True

### Votes by party/list

**Vote mismatches:** 13 / 13 parties

| Party | CNE | DB | Status |
|-------|-----|-----|--------|
| A | — | 1325 | **MISMATCH** |
| B | — | 12663 | **MISMATCH** |
| BE | 6321 | 681 | **MISMATCH** |
| CDU | 7610 | 1166 | **MISMATCH** |
| CH | 2983 | 821 | **MISMATCH** |
| D | 41213 | — | **MISMATCH** |
| E | 79 | — | **MISMATCH** |
| L | 461 | — | **MISMATCH** |
| PAN | 2821 | — | **MISMATCH** |
| PPM | 211 | — | **MISMATCH** |
| PS | 18192 | 31015 | **MISMATCH** |
| PSD | 17481 | — | **MISMATCH** |
| VP | 424 | — | **MISMATCH** |

### Seats (mapa_2 M columns vs `seat_result`)

**Seat mismatches:** 2 / 5 parties · CNE council total: **13** seats

| Party | mapa_2 M | DB `seat_result` | Status |
|-------|----------|------------------|--------|
| BE | 1 | 1 | OK |
| CDU | 1 | 1 | OK |
| D | 6 | — | **MISMATCH** |
| PS | 3 | 3 | OK |
| PSD | 2 | — | **MISMATCH** |

### D'Hondt demo (`allocate_seats_dhondt`, 7 seats — ex10.sql pattern)

| Party | Votes | Seats |
|-------|-------|-------|
| PS | 31015 | 5 |
| B | 12663 | 2 |

### mapa_2 vote % vs DB (derived from valid votes)

**mapa_2 % mismatches:** 13 / 13 parties

| Party | mapa_2 % | DB vote % | Status |
|-------|----------|-----------|--------|
| A | — | 2.78% | **missing in mapa_2** |
| B | — | 26.56% | **missing in mapa_2** |
| BE | 6.46% | 1.43% | **MISMATCH** |
| CDU | 7.78% | 2.45% | **MISMATCH** |
| CH | 3.05% | 1.72% | **MISMATCH** |
| D | 42.14% | —% | **MISMATCH** |
| E | 0.08% | —% | **MISMATCH** |
| L | 0.47% | —% | **MISMATCH** |
| PAN | 2.88% | —% | **MISMATCH** |
| PPM | 0.22% | —% | **MISMATCH** |
| PS | 18.6% | 65.06% | **MISMATCH** |
| PSD | 17.87% | —% | **MISMATCH** |
| VP | 0.43% | —% | **MISMATCH** |

**Top quotients (`demonstrate_dhondt`):** see `sql/07_demo_queries.sql`.


## Barrancos (small municipality (Beja, ~1.3k registered voters))

District (CNE row): **BEJA** · DB: **Beja**

### Turnout (mapa_1 vs DB)

| Metric | CNE mapa_1 | DB `turnout` | Match |
|--------|------------|--------------|-------|
| Registered | 1310 | 1310 | OK |
| Votes cast | 1000 | 1000 | OK |
| Valid votes | 968 | 968 | OK |
| Blank | 20 | 20 | OK |
| Null | 12 | 12 | OK |

Sum party votes: CNE **968** · DB **968** · OK  
Valid votes check: sum ≤ valid → CNE True, DB True

### Votes by party/list

**Vote mismatches:** 0 / 3 parties

| Party | CNE | DB | Status |
|-------|-----|-----|--------|
| A | 155 | 155 | OK |
| CDU | 465 | 465 | OK |
| PS | 348 | 348 | OK |

### Seats (mapa_2 M columns vs `seat_result`)

**Seat mismatches:** 0 / 3 parties · CNE council total: **5** seats

| Party | mapa_2 M | DB `seat_result` | Status |
|-------|----------|------------------|--------|
| A | 1 | 1 | OK |
| CDU | 2 | 2 | OK |
| PS | 2 | 2 | OK |

### D'Hondt demo (`allocate_seats_dhondt`, 7 seats — ex10.sql pattern)

| Party | Votes | Seats |
|-------|-------|-------|
| CDU | 465 | 4 |
| PS | 348 | 2 |
| A | 155 | 1 |

### mapa_2 vote % vs DB (derived from valid votes)

**mapa_2 % mismatches:** 0 / 3 parties

| Party | mapa_2 % | DB vote % | Status |
|-------|----------|-----------|--------|
| A | 16.01% | 16.01% | OK |
| CDU | 48.04% | 48.04% | OK |
| PS | 35.95% | 35.95% | OK |

**Top quotients (`demonstrate_dhondt`):** see `sql/07_demo_queries.sql`.


## Summary

| Municipality | Turnout | | Votes | | mapa_2 % | | Seats | | D'Hondt demo | |
|--------------|---------|--|-------|--|----------|--|-------|--|--------------|--|
| Lisboa | Turnout | PASS | Votes | PASS | mapa_2 % | PASS | Seats | PASS | D'Hondt demo | OK |
| Porto | Turnout | FAIL | Votes | FAIL | mapa_2 % | FAIL | Seats | FAIL | D'Hondt demo | OK |
| Barrancos | Turnout | PASS | Votes | PASS | mapa_2 % | PASS | Seats | PASS | D'Hondt demo | OK |

## Notes

- **Lisboa** uses CNE list codes (A, B, …) in mapa_1/mapa_2, not national acronyms (PS/PSD).
- **`seat_result`** loaded from CNE **mapa_2** `M` columns (`etl/pipeline/load_seats.py`); D'Hondt block uses fixed 7 seats for SQL demo only.
- **mapa_2** = vote % published by CNE; parser must keep decimal points (unlike ETL `coerce_decimal` for integers).
- D'Hondt uses **7** seats in this script; smaller councils may have a different official seat total.
- Regenerate: `python scripts/validate_samples_2021.py` from repo root (with DB env vars set).
