# ER diagrams (deliverables)

Generated from **pgAdmin 4 → ERD For Schema** on database `election_analytics` (June 2026).

## Files in this folder

| File | Description |
|------|-------------|
| `operational_schema_er.png` | Normalized operational model (`operational.*`) |
| `warehouse_star_schema.png` | Warehouse model (`warehouse.*` — facts + dimensions) |
| `operational_schema.pgerd` | pgAdmin ERD project (re-export / edit) |
| `warehouse_schema.pgerd` | pgAdmin ERD project (re-export / edit) |

Use the PNG files in **`docs/report.pdf`** and slides (§5.1 data modelling).

## Regenerate PNG from pgAdmin

1. Schemas **`operational`** / **`warehouse`** → right-click → **ERD For Schema**.
2. Layout → **Export** → PNG.
3. Overwrite the matching `.png` above.

## Not included (by design)

| Schema | Reason |
|--------|--------|
| `staging` | Shown in ETL narrative / `sql/05_staging_schema.sql`, not a separate ER deliverable |
| `public` | PostGIS system tables only — no project tables |

Optional later: `etl_flow_diagram.png` (CNE → staging → operational → warehouse) for one slide.

## SQL source of truth

- `sql/01_operational_schema.sql`
- `sql/02_warehouse_schema.sql`
