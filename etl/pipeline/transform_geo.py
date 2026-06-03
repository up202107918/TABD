"""
Attach CAOP polygon geometries to operational.district and operational.municipality.
Supports shapefiles (.shp) and GeoJSON (.geojson) under etl/data/caop/.
"""

import json
import logging
import os
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import CAOP_DATA_DIR

try:
    import shapefile  # pyshp
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform
except ImportError:
    shapefile = None


def normalize_key(value: Optional[str]) -> str:
    if not value:
        return ''
    text = str(value).strip().upper()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(text.split())


def find_boundary_files(layer_hint: str) -> List[Path]:
    hints = {
        'district': ('dist', 'dt', 'distrito'),
        'municipality': ('concel', 'munic', 'cc', 'municip'),
    }
    tokens = hints.get(layer_hint, ())
    files: List[Path] = []
    root = Path(CAOP_DATA_DIR)
    if not root.is_dir():
        return files
    for path in sorted(root.rglob('*')):
        if path.suffix.lower() not in {'.shp', '.geojson'}:
            continue
        name = path.name.lower()
        if any(token in name for token in tokens):
            files.append(path)
    return files


def find_shapefiles(layer_hint: str) -> List[Path]:
    return [p for p in find_boundary_files(layer_hint) if p.suffix.lower() == '.shp']


def pick_name_field(field_names: List[str]) -> Optional[str]:
    candidates = [
        'concelho', 'concelho_1', 'municipio', 'municipio_1', 'nome', 'name', 'designacao',
        'distrito', 'distrito_1',
    ]
    lowered = [f.lower() for f in field_names]
    for candidate in candidates:
        if candidate in lowered:
            return field_names[lowered.index(candidate)]
    return None


def pick_district_field(field_names: List[str]) -> Optional[str]:
    for candidate in ('distrito', 'distrito_1', 'dt', 'dtmn'):
        lowered = [f.lower() for f in field_names]
        if candidate in lowered:
            return field_names[lowered.index(candidate)]
    return None


def pick_municipality_field(field_names: List[str]) -> Optional[str]:
    for candidate in ('concelho', 'municipio', 'municipio_1', 'nome'):
        lowered = [f.lower() for f in field_names]
        if candidate in lowered:
            return field_names[lowered.index(candidate)]
    return None


def load_geojson_features(path: Path) -> List[Tuple[dict, object]]:
    if shapefile is None:
        raise ImportError('Install pyshp, shapely, and pyproj for CAOP loading')

    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    data = json.loads(text)
    rows: List[Tuple[dict, object]] = []
    for feature in data.get('features', []):
        props = feature.get('properties') or {}
        geom = shape(feature['geometry'])
        if geom.is_empty:
            continue
        minx, miny, maxx, maxy = geom.bounds
        if max(abs(minx), abs(maxx), abs(miny), abs(maxy)) > 360:
            transformer = Transformer.from_crs('EPSG:3763', 'EPSG:4326', always_xy=True)
            geom = transform(transformer.transform, geom)
        rows.append((props, geom))
    return rows


def read_layer(shp_path: Path) -> List[Tuple[dict, object]]:
    """Return list of (attributes dict, shapely geometry in EPSG:4326)."""
    if shapefile is None:
        raise ImportError('Install pyshp, shapely, and pyproj for CAOP loading')

    reader = shapefile.Reader(str(shp_path))
    fields = [field[0] for field in reader.fields[1:]]
    rows: List[Tuple[dict, object]] = []

    for shp_record in reader.shapeRecords():
        attrs = dict(zip(fields, shp_record.record))
        geom = shape(shp_record.shape.__geo_interface__)
        if geom.is_empty:
            continue
        # CAOP may be geographic (ETRS89) or projected (PT-TM06)
        minx, miny, maxx, maxy = geom.bounds
        if max(abs(minx), abs(maxx), abs(miny), abs(maxy)) > 360:
            transformer = Transformer.from_crs('EPSG:3763', 'EPSG:4326', always_xy=True)
            geom = transform(transformer.transform, geom)
        rows.append((attrs, geom))

    return rows


def update_geometry(conn, table: str, id_column: str, id_value: int, geom_wkt: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            UPDATE operational.{table}
            SET geometry = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromText(%s), 4326)))
            WHERE {id_column} = %s
            """,
            (geom_wkt, id_value),
        )


def iter_boundary_rows(path: Path) -> List[Tuple[dict, object]]:
    if path.suffix.lower() == '.geojson':
        return load_geojson_features(path)
    return read_layer(path)


def load_district_geometries(conn) -> int:
    name_to_id: Dict[str, int] = {}
    with conn.cursor() as cur:
        cur.execute('SELECT district_id, district_name FROM operational.district')
        for district_id, district_name in cur.fetchall():
            name_to_id[normalize_key(district_name)] = district_id

    updated = 0
    for boundary_path in find_boundary_files('district'):
        logging.info('Loading district boundaries from %s', boundary_path)
        for attrs, geom in iter_boundary_rows(boundary_path):
            field = pick_district_field(list(attrs.keys())) or pick_name_field(list(attrs.keys()))
            if not field:
                continue
            district_id = name_to_id.get(normalize_key(attrs.get(field)))
            if not district_id:
                continue
            update_geometry(conn, 'district', 'district_id', district_id, geom.wkt)
            updated += 1

    conn.commit()
    return updated


def load_municipality_geometries(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.municipality_id, m.municipality_name, d.district_name
            FROM operational.municipality m
            JOIN operational.district d ON d.district_id = m.district_id
            """
        )
        lookup = {
            (normalize_key(district_name), normalize_key(municipality_name)): municipality_id
            for municipality_id, municipality_name, district_name in cur.fetchall()
        }

    updated = 0
    for boundary_path in find_boundary_files('municipality'):
        logging.info('Loading municipality boundaries from %s', boundary_path)
        for attrs, geom in iter_boundary_rows(boundary_path):
            muni_field = pick_municipality_field(list(attrs.keys())) or pick_name_field(
                list(attrs.keys())
            )
            dist_field = pick_district_field(list(attrs.keys()))
            if not muni_field:
                continue
            muni_key = normalize_key(attrs.get(muni_field))
            dist_key = normalize_key(attrs.get(dist_field)) if dist_field else ''
            municipality_id = lookup.get((dist_key, muni_key))
            if not municipality_id and dist_key:
                # Fallback: match municipality name only if unique
                matches = [mid for (d, m), mid in lookup.items() if m == muni_key]
                if len(matches) == 1:
                    municipality_id = matches[0]
            if not municipality_id:
                continue
            update_geometry(conn, 'municipality', 'municipality_id', municipality_id, geom.wkt)
            updated += 1

    conn.commit()
    return updated


def run_transform_geo(conn) -> Dict[str, int]:
    root = Path(CAOP_DATA_DIR)
    boundary_files = (
        list(root.rglob('*.shp')) + list(root.rglob('*.geojson'))
        if root.is_dir()
        else []
    )
    if not boundary_files:
        logging.warning(
            'No CAOP shapefiles in %s — map will have no polygons. See etl/data/caop/README.md',
            CAOP_DATA_DIR,
        )
        return {'districts_geo': 0, 'municipalities_geo': 0}

    if shapefile is None:
        logging.warning('pyshp/shapely/pyproj not installed — skipping CAOP geometries')
        return {'districts_geo': 0, 'municipalities_geo': 0}

    districts = load_district_geometries(conn)
    municipalities = load_municipality_geometries(conn)
    logging.info('CAOP geometries updated: %s districts, %s municipalities', districts, municipalities)
    return {'districts_geo': districts, 'municipalities_geo': municipalities}
