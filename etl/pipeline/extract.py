"""
Extract phase: read CNE Excel workbooks and load staging tables.
"""

import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import psycopg2.extras

from config import PARTY_MAPPING

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
    'distrito', 'concelho', 'freguesia', 'orgao', 'candidatura',
    'votos', 'mandatos', 'percentagem', 'numero_candidatura',
    'nome_candidato', 'lista_completa',
]

TURNOUT_COLUMNS = [
    'distrito', 'concelho', 'freguesia', 'orgao',
    'eleitores_inscritos', 'votantes', 'votos_validos',
    'votos_brancos', 'votos_nulos',
]

TEXT_COLUMNS = {
    'distrito', 'concelho', 'freguesia', 'orgao', 'candidatura',
    'nome_candidato', 'lista_completa',
}
INTEGER_COLUMNS = {
    'votos', 'mandatos', 'numero_candidatura',
    'eleitores_inscritos', 'votantes', 'votos_validos',
    'votos_brancos', 'votos_nulos',
}

# CNE wide-format party column codes (row 3 of mapa_1) -> acronym
CNE_PARTY_CODE_MAP = {
    'ps': 'PS',
    'ppd_psd': 'PSD',
    'cds_pp': 'CDS-PP',
    'pcp_pev': 'CDU',
    'pctp_mrpp': 'MRPP',
    'b_e': 'BE',
    'ch': 'CH',
    'il': 'IL',
    'pan': 'PAN',
    'l': 'L',
    'jpp': 'JPP',
    'mas': 'MAS',
    'mpt': 'MPT',
    'nc': 'NC',
    'pdr': 'PDR',
    'ppm': 'PPM',
    'ptp': 'PTP',
    'r_i_r': 'RIR',
    'vp': 'VP',
    'e': 'E',
}

# mapa_2 / mapa_3 are skipped in MVP (see etl/docs/source_inventory_2021.md)
SKIP_WORKBOOK_MARKERS = (
    'mapa_2', 'mapa_3', 'parte2', 'parte3', 'perc_mandatos', 'eleitos',
)

WIDE_PARTY_COL_START = 8


def normalize_label(value: Any) -> str:
    if value is None or pd.isna(value):
        return ''
    text = str(value).strip().lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def should_load_workbook(workbook_path: str) -> bool:
    name = Path(workbook_path).name.lower()
    return not any(marker in name for marker in SKIP_WORKBOOK_MARKERS)


def discover_excel_workbooks(
    dataset_dirs: List[str],
    include_markers: Optional[List[str]] = None,
) -> List[str]:
    workbooks: List[str] = []
    for dataset_dir in dataset_dirs:
        root = Path(dataset_dir)
        if not root.exists():
            continue
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.suffix.lower() in {'.xls', '.xlsx'}:
                if not should_load_workbook(str(path)):
                    continue
                name = path.name.lower()
                if include_markers and not any(m in name for m in include_markers):
                    continue
                workbooks.append(str(path))
    return workbooks


def find_wide_mapa_header_row(df: pd.DataFrame, max_scan_rows: int = 15) -> Optional[int]:
    """Locate the cod/conc header row (row 3 in 2021, row 2 in 2017)."""
    for index in range(min(max_scan_rows, len(df))):
        normalized = [normalize_label(v) for v in df.iloc[index].tolist()]
        if 'cod' in normalized and 'conc' in normalized:
            return index
    return None


def read_workbook_sheets(workbook_path: str) -> Dict[str, pd.DataFrame]:
    extension = Path(workbook_path).suffix.lower()
    if extension == '.xlsx':
        engines: List[Optional[str]] = ['openpyxl', None]
    elif extension == '.xls':
        engines = ['xlrd', None]
    else:
        raise ValueError(f'Unsupported workbook: {workbook_path}')

    last_error: Optional[Exception] = None
    for engine in engines:
        try:
            return pd.read_excel(
                workbook_path, sheet_name=None, engine=engine, dtype=object, header=None
            )
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f'Failed to read {workbook_path}: {last_error}')


def detect_header_row(df: pd.DataFrame, alias_map: Dict[str, str], max_scan_rows: int = 12) -> int:
    best_index = 0
    best_score = -1
    for index in range(min(max_scan_rows, len(df))):
        normalized = [normalize_label(v) for v in df.iloc[index].tolist()]
        score = sum(1 for item in normalized if item in alias_map)
        if score > best_score:
            best_score = score
            best_index = index
    return best_index


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


def normalize_sheet(df: pd.DataFrame, alias_map: Dict[str, str], expected_columns: List[str]) -> pd.DataFrame:
    frame = df.copy().dropna(how='all').dropna(axis=1, how='all')
    if frame.empty:
        return pd.DataFrame(columns=expected_columns)

    header_row = detect_header_row(frame, alias_map)
    header_values = [normalize_label(v) for v in frame.iloc[header_row].tolist()]
    frame = frame.iloc[header_row + 1 :].copy()
    frame.columns = [alias_map.get(v, v) for v in header_values]
    frame = frame.loc[:, ~frame.columns.duplicated()].copy()

    for col in expected_columns:
        if col not in frame.columns:
            frame[col] = None
    frame = frame[expected_columns]

    for column in expected_columns:
        if column in TEXT_COLUMNS:
            frame[column] = frame[column].apply(
                lambda x: None if pd.isna(x) else str(x).strip() or None
            )
        elif column in INTEGER_COLUMNS:
            frame[column] = frame[column].apply(coerce_integer)
        elif column == 'percentagem':
            frame[column] = frame[column].apply(coerce_decimal)

    return frame.dropna(how='all').where(pd.notna(frame), None)


def standardize_party_name(party_name: str) -> str:
    if not isinstance(party_name, str):
        return 'Unknown'
    normalized = unicodedata.normalize('NFKD', party_name).encode('ASCII', 'ignore').decode('utf-8').upper()
    cleaned = re.sub(r'[^A-Z0-9/]+', '', normalized)
    return PARTY_MAPPING.get(cleaned, cleaned)


def cell_text(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def party_code_to_acronym(code: str) -> str:
    key = normalize_label(code)
    if key in CNE_PARTY_CODE_MAP:
        return CNE_PARTY_CODE_MAP[key]
    return standardize_party_name(key.upper().replace('_', ''))


def is_wide_mapa_sheet(df: pd.DataFrame) -> bool:
    """Detect CNE mapa_I wide layout (cod/conc header row varies by year)."""
    return find_wide_mapa_header_row(df) is not None


def parse_wide_mapa_sheet(
    raw_sheet: pd.DataFrame,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Unpivot CNE mapa_1 wide sheet into long result and turnout records.
    Loads municipality-level CM rows only.
    """
    header_row = find_wide_mapa_header_row(raw_sheet)
    if header_row is None:
        return [], []

    header = [normalize_label(v) for v in raw_sheet.iloc[header_row].tolist()]
    party_columns: List[Tuple[int, str]] = []
    for idx in range(WIDE_PARTY_COL_START, len(header)):
        code = header[idx]
        if code and code not in ('partidos', 'org'):
            party_columns.append((idx, code))

    results: List[Dict[str, Any]] = []
    turnouts: List[Dict[str, Any]] = []
    current_district: Optional[str] = None
    data_start_row = header_row + 1

    for row_idx in range(data_start_row, len(raw_sheet)):
        row = raw_sheet.iloc[row_idx].tolist()
        conc = cell_text(row[1] if len(row) > 1 else None)
        freg = cell_text(row[2] if len(row) > 2 else None)
        org = normalize_label(row[3] if len(row) > 3 else None)
        insc = coerce_integer(row[4] if len(row) > 4 else None)
        vot = coerce_integer(row[5] if len(row) > 5 else None)
        brancos = coerce_integer(row[6] if len(row) > 6 else None) or 0
        nulos = coerce_integer(row[7] if len(row) > 7 else None) or 0

        if not org and conc and not freg and insc is None:
            current_district = conc
            continue

        if org != 'cm' or freg or not conc or not current_district:
            continue

        if insc is not None and vot is not None:
            valid = max(0, vot - brancos - nulos)
            turnouts.append({
                'distrito': current_district,
                'concelho': conc,
                'freguesia': None,
                'orgao': 'CM',
                'eleitores_inscritos': insc,
                'votantes': vot,
                'votos_validos': valid,
                'votos_brancos': brancos,
                'votos_nulos': nulos,
            })

        for col_idx, party_code in party_columns:
            votes = coerce_integer(row[col_idx] if col_idx < len(row) else None)
            if votes is None or votes <= 0:
                continue
            results.append({
                'distrito': current_district,
                'concelho': conc,
                'freguesia': None,
                'orgao': 'CM',
                'candidatura': party_code_to_acronym(party_code),
                'votos': votes,
                'mandatos': None,
                'percentagem': None,
                'numero_candidatura': None,
                'nome_candidato': None,
                'lista_completa': None,
            })

    return results, turnouts


def dataframe_to_records(df: pd.DataFrame, source_file: str) -> List[Dict[str, Any]]:
    records = []
    for row in df.to_dict(orient='records'):
        row['source_file'] = source_file
        records.append(row)
    return records


def insert_rows(conn, table: str, data: List[Dict[str, Any]]) -> int:
    if not data:
        return 0
    columns = list(data[0].keys())
    values = [[row.get(col) for col in columns] for row in data]
    query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s"
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, query, values)
    conn.commit()
    return len(data)


def run_extract(
    conn,
    dataset_dirs: List[str],
    workbook_include: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    Load Excel files into staging.stg_election_results and stg_turnout_data.
    Returns row counts for logging.
    """
    workbook_paths = discover_excel_workbooks(dataset_dirs, workbook_include)
    if not workbook_paths:
        raise FileNotFoundError('No .xls/.xlsx files found in dataset folders')

    results_rows = 0
    turnout_rows = 0
    failed = 0

    for workbook_path in workbook_paths:
        logging.info('Reading workbook: %s', workbook_path)
        try:
            sheets = read_workbook_sheets(workbook_path)
        except Exception as exc:
            failed += 1
            logging.error('Skipped workbook %s: %s', workbook_path, exc)
            continue

        for sheet_name, raw_sheet in sheets.items():
            if raw_sheet is None or raw_sheet.empty:
                continue

            if is_wide_mapa_sheet(raw_sheet):
                wide_results, wide_turnout = parse_wide_mapa_sheet(raw_sheet)
                source = f'{workbook_path}::{sheet_name}'
                if wide_results:
                    results_rows += insert_rows(
                        conn,
                        'staging.stg_election_results',
                        dataframe_to_records(pd.DataFrame(wide_results), source),
                    )
                if wide_turnout:
                    turnout_rows += insert_rows(
                        conn,
                        'staging.stg_turnout_data',
                        dataframe_to_records(pd.DataFrame(wide_turnout), source),
                    )
                logging.info(
                    'Wide sheet %s: %s results, %s turnout rows',
                    sheet_name, len(wide_results), len(wide_turnout),
                )
                continue

            normalized_results = normalize_sheet(raw_sheet, RESULTS_ALIAS_MAP, RESULTS_COLUMNS)
            if {'candidatura', 'votos'}.issubset(normalized_results.columns):
                if normalized_results['candidatura'].notna().any():
                    normalized_results['candidatura'] = normalized_results['candidatura'].apply(
                        standardize_party_name
                    )
                    records = dataframe_to_records(
                        normalized_results, f'{workbook_path}::{sheet_name}'
                    )
                    if records:
                        results_rows += insert_rows(conn, 'staging.stg_election_results', records)
                        continue

            normalized_turnout = normalize_sheet(raw_sheet, TURNOUT_ALIAS_MAP, TURNOUT_COLUMNS)
            if {'eleitores_inscritos', 'votantes'}.issubset(normalized_turnout.columns):
                records = dataframe_to_records(
                    normalized_turnout, f'{workbook_path}::{sheet_name}'
                )
                if records:
                    turnout_rows += insert_rows(conn, 'staging.stg_turnout_data', records)

    if results_rows == 0 and turnout_rows == 0:
        raise RuntimeError('No rows loaded into staging; check Excel layout and schema.')

    logging.info(
        'Extract done: results=%s turnout=%s failed_workbooks=%s',
        results_rows, turnout_rows, failed,
    )
    return {
        'rows_extracted': len(workbook_paths),
        'rows_staged': results_rows + turnout_rows,
        'rows_rejected': failed,
    }
