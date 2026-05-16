"""
Database Configuration for Election Analytics Platform
Advanced Topics in Databases - Practical Assignment
"""

import os
from typing import Dict

# Database connection parameters
DB_CONFIG: Dict[str, str] = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'election_analytics'),
    'user': os.getenv('DB_USER', 'net'),
    'password': os.getenv('DB_PASSWORD', '')
}

# Schema names
SCHEMAS = {
    'staging': 'staging',
    'operational': 'operational',
    'warehouse': 'warehouse'
}

# Data source URLs
DATA_SOURCES = {
    'autarquicas_2021': 'https://www.cne.pt/sites/default/files/dl/2021al_mapa_oficial.zip',
    'caop_2021': 'https://www.dgterritorio.gov.pt/sites/default/files/ficheiros-cartografia/CAOP2021_SHP_AAD-ETRS89.zip'
}

# Local data directories
DATA_DIRS = {
    'downloads': './data/downloads',
    'extracted': './data/extracted',
    'processed': './data/processed',
    'logs': './data/logs'
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

def ensure_data_directories():
    """Create data directories if they don't exist"""
    for dir_path in DATA_DIRS.values():
        os.makedirs(dir_path, exist_ok=True)
