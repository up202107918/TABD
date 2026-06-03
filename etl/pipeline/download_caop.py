"""
Optional CAOP download helper. Run: python -m pipeline.download_caop
"""

import json
import logging
import os
import zipfile
from pathlib import Path

import requests

from config import CAOP_DATA_DIR, CAOP_DOWNLOAD_URLS, CAOP_FALLBACK_GEOJSON

logging.basicConfig(level=logging.INFO)


def _has_boundary_files() -> bool:
    root = Path(CAOP_DATA_DIR)
    if not root.is_dir():
        return False
    return bool(list(root.rglob('*.shp'))) or bool(list(root.rglob('*.geojson')))


def _download_file(url: str, dest: Path) -> bool:
    logging.info('Downloading %s', url)
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    logging.info('Saved %s (%s bytes)', dest, dest.stat().st_size)
    return True


def download_zip_sources() -> bool:
    for url in CAOP_DOWNLOAD_URLS:
        try:
            response = requests.get(url, timeout=120)
            response.raise_for_status()
        except Exception as exc:
            logging.warning('ZIP download failed: %s', exc)
            continue

        zip_path = Path(CAOP_DATA_DIR) / 'caop_download.zip'
        zip_path.write_bytes(response.content)
        with zipfile.ZipFile(zip_path, 'r') as archive:
            archive.extractall(CAOP_DATA_DIR)
        zip_path.unlink(missing_ok=True)
        logging.info('Extracted official CAOP ZIP to %s', CAOP_DATA_DIR)
        return True
    return False


def download_geojson_fallback() -> bool:
    """Download continent district + municipality GeoJSON (DGT-derived, GitHub mirror)."""
    ok = False
    for filename, url in CAOP_FALLBACK_GEOJSON.items():
        dest = Path(CAOP_DATA_DIR) / filename
        if dest.exists() and dest.stat().st_size > 1000:
            logging.info('Already present: %s', dest)
            ok = True
            continue
        try:
            _download_file(url, dest)
            ok = True
        except Exception as exc:
            logging.warning('Failed %s: %s', filename, exc)
    return ok


def download_caop() -> bool:
    os.makedirs(CAOP_DATA_DIR, exist_ok=True)
    if _has_boundary_files():
        logging.info('CAOP boundary files already present in %s', CAOP_DATA_DIR)
        return True

    if download_zip_sources() and _has_boundary_files():
        return True

    if download_geojson_fallback() and _has_boundary_files():
        logging.info(
            'Using GeoJSON fallback (nmota/caop_GeoJSON). '
            'Cite DGT CAOP as original source in your report.'
        )
        return True

    logging.error(
        'All downloads failed. See etl/data/caop/README.md for manual steps.'
    )
    return False


if __name__ == '__main__':
    raise SystemExit(0 if download_caop() else 1)
