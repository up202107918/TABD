# Validation samples — Autárquicas 2021 (CM)

Generated: 2026-06-03 13:09 UTC  
Sources: `mapa_1_resultados.xlsx` (votes/turnout), `mapa_2_perc_mandatos.xlsx` (vote %), PostgreSQL `operational.*`, function `allocate_seats_dhondt(..., 7)`.

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

### D'Hondt seats (`allocate_seats_dhondt`, 7 seats — ex10.sql pattern)

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
| Registered | 207129 | 207129 | OK |
| Votes cast | 101179 | 101179 | OK |
| Valid votes | 97796 | 97796 | OK |
| Blank | 2253 | 2253 | OK |
| Null | 1130 | 1130 | OK |

Sum party votes: CNE **97796** · DB **97796** · OK  
Valid votes check: sum ≤ valid → CNE True, DB True

### Votes by party/list

**Vote mismatches:** 0 / 11 parties

| Party | CNE | DB | Status |
|-------|-----|-----|--------|
| BE | 6321 | 6321 | OK |
| CDU | 7610 | 7610 | OK |
| CH | 2983 | 2983 | OK |
| D | 41213 | 41213 | OK |
| E | 79 | 79 | OK |
| L | 461 | 461 | OK |
| PAN | 2821 | 2821 | OK |
| PPM | 211 | 211 | OK |
| PS | 18192 | 18192 | OK |
| PSD | 17481 | 17481 | OK |
| VP | 424 | 424 | OK |

### D'Hondt seats (`allocate_seats_dhondt`, 7 seats — ex10.sql pattern)

| Party | Votes | Seats |
|-------|-------|-------|
| D | 41213 | 4 |
| PS | 18192 | 2 |
| PSD | 17481 | 1 |

### mapa_2 vote % vs DB (derived from valid votes)

**mapa_2 % mismatches:** 0 / 11 parties

| Party | mapa_2 % | DB vote % | Status |
|-------|----------|-----------|--------|
| BE | 6.46% | 6.46% | OK |
| CDU | 7.78% | 7.78% | OK |
| CH | 3.05% | 3.05% | OK |
| D | 42.14% | 42.14% | OK |
| E | 0.08% | 0.08% | OK |
| L | 0.47% | 0.47% | OK |
| PAN | 2.88% | 2.88% | OK |
| PPM | 0.22% | 0.22% | OK |
| PS | 18.6% | 18.6% | OK |
| PSD | 17.87% | 17.87% | OK |
| VP | 0.43% | 0.43% | OK |

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

### D'Hondt seats (`allocate_seats_dhondt`, 7 seats — ex10.sql pattern)

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

| Municipality | Turnout | | Votes | | mapa_2 % | | D'Hondt | |
|--------------|---------|--|-------|--|----------|--|---------|--|
| Lisboa | Turnout | PASS | Votes | PASS | mapa_2 % | PASS | D'Hondt | OK |
| Porto | Turnout | PASS | Votes | PASS | mapa_2 % | PASS | D'Hondt | OK |
| Barrancos | Turnout | PASS | Votes | PASS | mapa_2 % | PASS | D'Hondt | OK |

## Notes

- **Lisboa** uses CNE list codes (A, B, …) in mapa_1/mapa_2, not national acronyms (PS/PSD).
- **`seat_result`** table is still empty in MVP; seats come from **`allocate_seats_dhondt`** (same algorithm as course `ex10.sql`).
- **mapa_2** = vote % published by CNE; parser must keep decimal points (unlike ETL `coerce_decimal` for integers).
- D'Hondt uses **7** seats in this script; smaller councils may have a different official seat total.
- Regenerate: `python scripts/validate_samples_2021.py` from repo root (with DB env vars set).
