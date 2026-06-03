"""
ETL configuration: database connection, dataset definitions, paths.
"""

import os
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# One ETL run targets a single election dataset (folder under etl/data).
DATASETS: Dict[str, Dict[str, Any]] = {
    'aut_2021': {
        'election_year': 2021,
        'election_date': '2021-09-26',
        'election_type_code': 'AUT',
        'description': 'Autárquicas 2021',
        'data_dirs': ['2021al_mapa_oficial'],
        'primary_organ': 'CM',
    },
}

DEFAULT_DATASET = 'aut_2021'

DB_CONFIG: Dict[str, str] = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'election_analytics'),
    'user': os.getenv('DB_USER', 'username'),
    'password': os.getenv('DB_PASSWORD', 'password'),
}

SCHEMAS = {
    'staging': 'staging',
    'operational': 'operational',
    'warehouse': 'warehouse',
}

ETL_CONFIG = {
    'batch_size': 1000,
    'log_level': 'INFO',
}

PARTY_MAPPING = {
    'PS': 'PS',
    'PSD': 'PSD',
    'CDS-PP': 'CDS-PP',
    'BE': 'BE',
    'CDU': 'CDU',
    'PCP': 'PCP',
    'PEV': 'PEV',
    'PAN': 'PAN',
    'CHEGA': 'CH',
    'IL': 'IL',
    'LIVRE': 'L',
    'PPD/PSD': 'PSD',
    'PSD/CDS-PP': 'PSD/CDS',
    'PS/PSD': 'PS/PSD',
}

ORGAN_CODES = {
    'Câmara Municipal': 'CM',
    'Assembleia Municipal': 'AM',
    'Junta de Freguesia': 'JF',
}


def get_dataset_config(dataset_key: str) -> Dict[str, Any]:
    """Return config for a named dataset or raise KeyError."""
    if dataset_key not in DATASETS:
        known = ', '.join(sorted(DATASETS))
        raise KeyError(f"Unknown dataset '{dataset_key}'. Available: {known}")
    return DATASETS[dataset_key]


def get_dataset_dirs(dataset_key: str = DEFAULT_DATASET) -> List[str]:
    """Return absolute paths to Excel source folders for one dataset."""
    cfg = get_dataset_config(dataset_key)
    dirs: List[str] = []
    for name in cfg['data_dirs']:
        path = os.path.join(DATA_DIR, name)
        if os.path.isdir(path):
            dirs.append(path)
    return dirs
