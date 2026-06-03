# SQL demo outputs (sql/03 + sql/04)

Generated for the report and oral presentation. Regenerate after ETL full load:

```powershell
$env:DB_USER="postgres"
$env:DB_PASSWORD="12345"
$env:DB_NAME="election_analytics"

# 1) Refresh analytical views + functions (idempotent)
psql -U postgres -h localhost -d election_analytics -v ON_ERROR_STOP=1 -f sql/04_analytical_queries.sql

# 2) Run sample queries (all sections)
psql -U postgres -h localhost -d election_analytics -v ON_ERROR_STOP=1 -f sql/07_demo_queries.sql -o docs/sql_outputs/demo_results.txt

# Recommended — applies sql/04 + runs demos into demo_results.txt:
$env:DB_NAME="election_analytics"
$env:DB_USER="postgres"
$env:DB_PASSWORD="your_password"
$env:PGCLIENTENCODING="UTF8"
$env:LC_MESSAGES="C"
.\.venv\Scripts\python.exe scripts\run_sql_demos.py
```

`run_sql_demos.py` sets `LC_MESSAGES=C` so psql logs in `_apply_log.txt` use English NOTICE/ERROR text (not a Polish Windows locale).

After a full ETL reload or `seat_result` load, always re-run the script so `demo_results.txt` reflects current data.

## Files

| File | Contents |
|------|----------|
| `demo_results.txt` | Full psql output from `sql/07_demo_queries.sql` |
| `_apply_log.txt` | Log from `run_sql_demos.py` (04 apply + optional 03) |

## What is demonstrated

- **sql/03:** `calculate_vote_percentage`, `get_party_performance_in_municipality`, views `vw_*`, `allocate_seats_dhondt` (D'Hondt = course **ex10.sql**: `divisors` + `quotients` + `LIMIT` + `COUNT`), triggers (audit row count).
- **sql/04:** Views `analytical_query_1`–`6`, `8`, function `demonstrate_dhondt` (ranked quotients, same pattern).

**Note:** CNE 2021 uses list codes (A, B, …) in Lisboa, not always national acronyms (PS/PSD). D'Hondt samples use 7 seats for CM as in the assignment demo.
