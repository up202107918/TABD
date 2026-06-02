"""
Database Configuration for Election Analytics Platform
Advanced Topics in Databases - Practical Assignment
"""

import os
from typing import Dict, List


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')


def _discover_dataset_dirs(root_dir: str) -> List[str]:
    """Return absolute paths for each dataset directory under ETL data."""
    if not os.path.isdir(root_dir):
        return []

    dataset_dirs = []
    for entry in sorted(os.listdir(root_dir)):
        full_path = os.path.join(root_dir, entry)
        if os.path.isdir(full_path):
            dataset_dirs.append(full_path)
    return dataset_dirs

# Database connection parameters
DB_CONFIG: Dict[str, str] = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'election_analytics'),
    'user': os.getenv('DB_USER', 'username'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

# Path configuration for ETL input folders
DATA_PATH = DATA_DIR  # Backward-compatible alias
DATASET_DIRS = _discover_dataset_dirs(DATA_DIR)

# Schema names
SCHEMAS = {
    'staging': 'staging',
    'operational': 'operational',
    'warehouse': 'warehouse'
}

# ETL Configuration
ETL_CONFIG = {
    'batch_size': 1000,  # Number of records to insert at once
    'max_retries': 3,     # Max retries for failed operations
    'log_level': 'INFO'   # Logging level: DEBUG, INFO, WARNING, ERROR
}

# Party name standardization mapping
PARTY_MAPPING = {
    # Common variations → standardized acronym
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
    'PSD/CDS-PP': 'PSD/CDS',  # Coalition
    'PS/PSD': 'PS/PSD',  # Coalition
}

# Electoral organ codes
ORGAN_CODES = {
    'Câmara Municipal': 'CM',
    'Assembleia Municipal': 'AM',
    'Junta de Freguesia': 'JF'
}

def get_connection_string() -> str:
    """Generate PostgreSQL connection string"""
    return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"


def get_dataset_dirs() -> List[str]:
    """Get dataset directories and refresh discovery if needed."""
    return _discover_dataset_dirs(DATA_DIR)

