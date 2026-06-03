# CAOP administrative boundaries

Boundary files for the map in the Flask app. The ETL loads them into `operational.district.geometry` and `operational.municipality.geometry`.

## Quick start (automatic)

```bash
cd etl
python -m pipeline.download_caop
python run_etl.py --dataset aut_2021 --mode full
```

If the official DGT ZIP URL returns **404**, the script downloads **GeoJSON fallback** files from [nmota/caop_GeoJSON](https://github.com/nmota/caop_GeoJSON) (data originally from DGT WFS). Mention this in your report and prefer official shapefiles if you obtain them manually.

Expected files after download:

- `ContinenteDistritos.geojson` — district polygons (continent)
- `Portugal_Municipalities.geojson` — municipality polygons

## Manual download (official shapefiles)

1. Open [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) or [CAOP 2021](https://www.dgterritorio.gov.pt/node/457).
2. Download **Continente** shapefiles (district + municipality).
3. Unzip into this folder (`.shp` files in any subfolder).

## Re-run only geometries

After placing files here, run the full pipeline (or operational reload). The geo step runs automatically when boundary files exist.

## Note on election year

Autárquicas 2021 align best with CAOP 2021 boundaries. Fallback GeoJSON may differ slightly from 2021 units; document any mismatch in the report.
