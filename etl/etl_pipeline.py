"""
Main ETL Pipeline for Election Analytics Platform
Advanced Topics in Databases - Practical Assignment

This script orchestrates the complete ETL process:
1. Extract: Discover extracted election workbooks
2. Transform: Normalize heterogeneous sheet formats
3. Load: Insert recognized rows into staging tables
"""

import logging
import os
import psycopg2
import psycopg2.extras
import sys
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from config import DB_CONFIG, ETL_CONFIG, PARTY_MAPPING, get_dataset_dirs


RESULTS_ALIAS_MAP = {
    'distrito': 'distrito',
    'distrito_ilha': 'distrito',
    'ilha': 'distrito',
    'concelho': 'concelho',
    'municipio': 'concelho',
    'freguesia': 'freguesia',
    'orgao': 'orgao',
    'candidatura': 'candidatura',
    'lista': 'candidatura',
    'forca_politica': 'candidatura',
    'votos': 'votos',
    'num_votos': 'votos',
    'mandatos': 'mandatos',
    'percentagem': 'percentagem',
    'percentagem_votos_validos': 'percentagem',
    'numero_candidatura': 'numero_candidatura',
    'nome_candidato': 'nome_candidato',
    'lista_completa': 'lista_completa',
}

TURNOUT_ALIAS_MAP = {
    'distrito': 'distrito',
    'distrito_ilha': 'distrito',
    'ilha': 'distrito',
    'concelho': 'concelho',
    'municipio': 'concelho',
    'freguesia': 'freguesia',
    'orgao': 'orgao',
    'eleitores_inscritos': 'eleitores_inscritos',
    'inscritos': 'eleitores_inscritos',
    'votantes': 'votantes',
    'votos_validos': 'votos_validos',
    'votos_brancos': 'votos_brancos',
    'votos_em_branco': 'votos_brancos',
    'votos_nulos': 'votos_nulos',
}

RESULTS_COLUMNS = [
    'distrito',
    'concelho',
    'freguesia',
    'orgao',
    'candidatura',
    'votos',
    'mandatos',
    'percentagem',
    'numero_candidatura',
    'nome_candidato',
    'lista_completa',
]

TURNOUT_COLUMNS = [
    'distrito',
    'concelho',
    'freguesia',
    'orgao',
    'eleitores_inscritos',
    'votantes',
    'votos_validos',
    'votos_brancos',
    'votos_nulos',
]

TEXT_COLUMNS = {'distrito', 'concelho', 'freguesia', 'orgao', 'candidatura', 'nome_candidato', 'lista_completa'}
INTEGER_COLUMNS = {
    'votos',
    'mandatos',
    'numero_candidatura',
    'eleitores_inscritos',
    'votantes',
    'votos_validos',
    'votos_brancos',
    'votos_nulos',
}


def normalize_label(value: Any) -> str:
    if value is None or pd.isna(value):
        return ''
    text = str(value).strip().lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def discover_excel_workbooks(dataset_dirs: List[str]) -> List[str]:
    """Find all .xls/.xlsx files recursively under each dataset directory."""
    workbooks: List[str] = []
    for dataset_dir in dataset_dirs:
        root = Path(dataset_dir)
        if not root.exists():
            continue
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.suffix.lower() in {'.xls', '.xlsx'}:
                workbooks.append(str(path))
    return workbooks


def read_workbook_sheets(workbook_path: str) -> Dict[str, pd.DataFrame]:
    """Read all sheets from a workbook with pandas.read_excel, trying compatible engines."""
    extension = Path(workbook_path).suffix.lower()
    candidates: List[Optional[str]] = []

    if extension == '.xlsx':
        candidates = ['openpyxl', None]
    elif extension == '.xls':
        candidates = ['xlrd', None]
    else:
        raise ValueError(f'Unsupported workbook extension: {workbook_path}')

    last_error: Optional[Exception] = None
    for engine in candidates:
        try:
            # Explicitly use pandas.read_excel as requested, loading all sheets.
            return pd.read_excel(workbook_path, sheet_name=None, engine=engine, dtype=object)
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise RuntimeError(f'Failed to read workbook {workbook_path}: {last_error}')


def detect_header_row(df: pd.DataFrame, alias_map: Dict[str, str], max_scan_rows: int = 12) -> int:
    """Pick a probable header row for heterogeneous workbook layouts."""
    best_index = 0
    best_score = -1

    limit = min(max_scan_rows, len(df))
    for index in range(limit):
        row = df.iloc[index].tolist()
        normalized = [normalize_label(v) for v in row]
        score = sum(1 for item in normalized if item in alias_map)
        if score > best_score:
            best_score = score
            best_index = index

    return best_index


def normalize_sheet(df: pd.DataFrame, alias_map: Dict[str, str], expected_columns: List[str]) -> pd.DataFrame:
    """Normalize a raw DataFrame into a predictable tabular structure."""
    frame = df.copy()
    frame = frame.dropna(how='all').dropna(axis=1, how='all')
    if frame.empty:
        return pd.DataFrame(columns=expected_columns)

    header_row = detect_header_row(frame, alias_map)
    header_values = [normalize_label(v) for v in frame.iloc[header_row].tolist()]

    frame = frame.iloc[header_row + 1 :].copy()
    frame.columns = [alias_map.get(value, value) for value in header_values]
    frame = frame.loc[:, ~frame.columns.duplicated()].copy()

    available = [col for col in expected_columns if col in frame.columns]
    frame = frame[available].copy()
    for col in expected_columns:
        if col not in frame.columns:
            frame[col] = None
    frame = frame[expected_columns]

    for column in expected_columns:
        if column in TEXT_COLUMNS:
            frame[column] = frame[column].apply(lambda x: None if pd.isna(x) else str(x).strip() or None)
        elif column in INTEGER_COLUMNS:
            frame[column] = frame[column].apply(coerce_integer)
        elif column == 'percentagem':
            frame[column] = frame[column].apply(coerce_decimal)

    frame = frame.dropna(how='all')
    return frame.where(pd.notna(frame), None)


def coerce_integer(value: Any) -> Optional[int]:
    if value is None or pd.isna(value):
        return None
    text = str(value).replace(' ', '').replace('.', '').replace(',', '.')
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def coerce_decimal(value: Any) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    text = str(value).replace('%', '').replace(' ', '').replace('.', '').replace(',', '.')
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def classify_sheet(df: pd.DataFrame) -> Optional[str]:
    """Classify normalized sheet as results or turnout."""
    columns = set(df.columns)
    if {'candidatura', 'votos'}.issubset(columns):
        return 'results'
    if {'eleitores_inscritos', 'votantes'}.issubset(columns):
        return 'turnout'
    return None


def standardize_party_name(party_name: str) -> str:
    """Standardize party names using PARTY_MAPPING."""
    if not isinstance(party_name, str):
        return 'Unknown'

    normalized_name = unicodedata.normalize('NFKD', party_name).encode('ASCII', 'ignore').decode('utf-8').upper()
    cleaned_name = re.sub(r'[^A-Z0-9/]+', '', normalized_name)
    return PARTY_MAPPING.get(cleaned_name, cleaned_name)


def dataframe_to_records(df: pd.DataFrame, source_file: str) -> List[Dict[str, Any]]:
    """Convert a DataFrame to DB-ready records with source metadata."""
    records: List[Dict[str, Any]] = []
    for row in df.to_dict(orient='records'):
        row['source_file'] = source_file
        records.append(row)
    return records

def get_db_connection() -> psycopg2.extensions.connection:
    """Establish a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        return conn
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        sys.exit(1)

def insert_data(conn: psycopg2.extensions.connection, table: str, data: List[Dict]):
    """Insert data into the specified table."""
    if not data:
        logging.info(f"No data to insert into {table}.")
        return
    
    columns = list(data[0].keys())
    values = [[row.get(col) for col in columns] for row in data]
    
    insert_query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s"
    
    try:
        with conn.cursor() as cursor:
            psycopg2.extras.execute_values(cursor, insert_query, values)
        conn.commit()
        logging.info(f"Inserted {len(data)} records into {table}.")
    except Exception as e:
        logging.error(f"Failed to insert data into {table}: {e}")
        conn.rollback()

def main():
    """Main function to orchestrate the ETL process."""
    logging.basicConfig(level=ETL_CONFIG['log_level'])
    conn: Optional[psycopg2.extensions.connection] = None

    logging.info("Starting ETL pipeline...")

    try:
        dataset_dirs = get_dataset_dirs()
        if not dataset_dirs:
            raise FileNotFoundError('No dataset folders found under TABD/etl/data')

        workbook_paths = discover_excel_workbooks(dataset_dirs)
        if not workbook_paths:
            raise FileNotFoundError('No .xls/.xlsx files found under TABD/etl/data')

        conn = get_db_connection()

        loaded_results_rows = 0
        loaded_turnout_rows = 0
        failed_workbooks: List[Tuple[str, str]] = []

        for workbook_path in workbook_paths:
            logging.info('Processing workbook: %s', workbook_path)
            try:
                sheets = read_workbook_sheets(workbook_path)
            except Exception as exc:  # noqa: BLE001
                failed_workbooks.append((workbook_path, str(exc)))
                logging.error('Failed to read workbook %s: %s', workbook_path, exc)
                continue

            for sheet_name, raw_sheet in sheets.items():
                if raw_sheet is None or raw_sheet.empty:
                    continue

                normalized_results = normalize_sheet(raw_sheet, RESULTS_ALIAS_MAP, RESULTS_COLUMNS)
                if {'candidatura', 'votos'}.issubset(set(normalized_results.columns)):
                    if normalized_results['candidatura'].notna().any():
                        normalized_results['candidatura'] = normalized_results['candidatura'].apply(standardize_party_name)
                        records = dataframe_to_records(normalized_results, f'{workbook_path}::{sheet_name}')
                        if records:
                            insert_data(conn, 'staging.stg_election_results', records)
                            loaded_results_rows += len(records)
                            continue

                normalized_turnout = normalize_sheet(raw_sheet, TURNOUT_ALIAS_MAP, TURNOUT_COLUMNS)
                if {'eleitores_inscritos', 'votantes'}.issubset(set(normalized_turnout.columns)):
                    records = dataframe_to_records(normalized_turnout, f'{workbook_path}::{sheet_name}')
                    if records:
                        insert_data(conn, 'staging.stg_turnout_data', records)
                        loaded_turnout_rows += len(records)

        if loaded_results_rows == 0 and loaded_turnout_rows == 0:
            raise RuntimeError('No rows were loaded from .xls/.xlsx files; check workbook layout and staging schema.')

        logging.info(
            'ETL load completed. Results rows: %s, Turnout rows: %s, Failed workbooks: %s',
            loaded_results_rows,
            loaded_turnout_rows,
            len(failed_workbooks),
        )

        if failed_workbooks:
            for workbook_path, reason in failed_workbooks:
                logging.warning('Workbook skipped: %s (%s)', workbook_path, reason)

    except Exception as e:  # noqa: BLE001
        logging.error("ETL pipeline failed: %s", e)
        sys.exit(1)
    finally:
        if conn is not None:
            conn.close()

    try:
        # Keep connection check explicit in logs for compatibility with previous flow.
        logging.info("Loading data into database finished.")
    except Exception as e:  # noqa: BLE001
        logging.error(f"Data loading failed: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()

    logging.info("ETL pipeline completed successfully.")


if __name__ == "__main__":
    main()