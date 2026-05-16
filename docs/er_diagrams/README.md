# ER Diagrams Directory

Place your Entity-Relationship diagrams here.

## Required Diagrams

1. **Operational Schema ER Diagram**
   - Shows all tables in the operational schema
   - Relationships between entities
   - Primary and foreign keys
   - File: `operational_schema_er.png` or `.pdf`

2. **Data Warehouse Star Schema**
   - Fact tables in center
   - Dimension tables around it
   - Relationships
   - File: `warehouse_star_schema.png` or `.pdf`

3. **ETL Data Flow Diagram** (Optional)
   - Shows data flow from sources through staging to operational/warehouse
   - File: `etl_flow_diagram.png` or `.pdf`

## Tools Recommended

- **pgModeler** - PostgreSQL-specific modeling tool
- **DbSchema** - Universal database designer
- **draw.io** - Free online diagramming tool
- **Lucidchart** - Professional diagramming
- **DBeaver** - Can generate ER diagrams from existing schemas

## How to Generate from Database

If your database is already loaded, you can generate diagrams using:

```bash
# Using pgModeler
pgmodeler-cli --export-to-png --input your_model.dbm --output operational_schema_er.png

# Using DBeaver
# Connect to database → Right-click schema → ER Diagram → Export
```
