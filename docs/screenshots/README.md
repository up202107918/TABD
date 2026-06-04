# Application screenshots

Used in the report (`docs/report/`) and oral presentation (`slides/`).

## Web application

| File | Description |
|------|-------------|
| `home.png` | Homepage with statistics and district map |
| `districts.png` | Districts listing page |
| `analytics.png` | Analytics dashboard (2017 vs 2021 comparison) |
| `matplotlib_analytics_votes.png` | Matplotlib chart — votes (`scripts/export_charts.py` or `/analytics/chart.png`) |
| `matplotlib_analytics_seats.png` | Matplotlib chart — seats |

Regenerate Matplotlib exports:

```powershell
.\.venv\Scripts\python.exe scripts\export_charts.py
```

## Conventions

- PNG, descriptive lowercase names with underscores
- Desktop resolution ~1920×1080 where possible
