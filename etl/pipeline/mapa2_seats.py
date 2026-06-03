"""
Parse CNE mapa_2 (perc. mandatos) CM seat counts from official Excel workbooks.

Layout (2017 + 2021): header row with party codes; sub-header row with '%' and 'M'
pairs; CM municipality rows have vote % in '%' column and seats in 'M' column.
"""

from __future__ import annotations

import logging
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from pipeline.extract import (
    cell_text,
    normalize_label,
    party_code_to_acronym,
    read_workbook_sheets,
)

MAPA2_MARKERS = ('mapa_2', 'mapa_ii', 'mapa ii', 'perc_mandatos', 'parte2', 'parte 2')


def _subcolumn_label(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    return str(value).strip().upper()


def normalize_territory_key(value: Optional[str]) -> str:
    if not value:
        return ''
    text = str(value).strip().upper()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(text.split())


def find_mapa2_workbook(dataset_dirs: List[str]) -> Optional[Path]:
    for root_name in dataset_dirs:
        root = Path(root_name)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            if path.suffix.lower() not in {'.xls', '.xlsx'}:
                continue
            name = path.name.lower()
            if any(marker in name for marker in MAPA2_MARKERS):
                return path
    return None


def _parse_mandate_int(value: Any) -> Optional[int]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text in {'-', '[RM]', 'RM'}:
        return None
    try:
        seats = int(float(text))
    except (TypeError, ValueError):
        return None
    return seats if seats >= 0 else None


def parse_mapa2_cm_seats(workbook_path: str) -> List[Dict[str, Any]]:
    """
    Return one dict per party/list with seats in a CM municipality row:
    {distrito, concelho, party_acronym, seats}
    """
    sheets = read_workbook_sheets(workbook_path)
    if not sheets:
        return []

    raw = list(sheets.values())[0]
    header_row = None
    for idx in range(min(15, len(raw))):
        normalized = [normalize_label(v) for v in raw.iloc[idx].tolist()]
        if 'cod' in normalized and 'conc' in normalized:
            header_row = idx
            break
    if header_row is None:
        logging.warning('mapa_2: no cod/conc header in %s', workbook_path)
        return []

    header = raw.iloc[header_row]
    sub = raw.iloc[header_row + 1] if header_row + 1 < len(raw) else None
    if sub is None:
        return []

    party_columns: List[Tuple[int, str]] = []
    for col_idx in range(4, len(header)):
        sub_label = _subcolumn_label(sub.iloc[col_idx] if col_idx < len(sub) else None)
        if sub_label != '%':
            continue
        if col_idx + 1 >= len(sub) or _subcolumn_label(sub.iloc[col_idx + 1]) != 'M':
            continue
        party_label = cell_text(header.iloc[col_idx])
        if not party_label or party_label == '-':
            continue
        party_columns.append((col_idx, party_label))

    if not party_columns:
        logging.warning('mapa_2: no %%/M party columns in %s', workbook_path)
        return []

    records: List[Dict[str, Any]] = []
    current_district: Optional[str] = None
    data_start = header_row + 2

    for row_idx in range(data_start, len(raw)):
        row = raw.iloc[row_idx].tolist()
        conc = cell_text(row[1] if len(row) > 1 else None)
        freg = cell_text(row[2] if len(row) > 2 else None)
        org = normalize_label(row[3] if len(row) > 3 else None)
        insc = row[4] if len(row) > 4 else None
        has_insc = insc is not None and not (isinstance(insc, float) and pd.isna(insc))

        if not org and conc and not freg and not has_insc:
            current_district = conc
            continue

        if org != 'cm' or freg or not conc or not current_district:
            continue

        for col_idx, party_label in party_columns:
            seats = _parse_mandate_int(row[col_idx + 1] if col_idx + 1 < len(row) else None)
            if seats is None:
                continue
            acronym = party_code_to_acronym(normalize_label(party_label))
            records.append({
                'distrito': current_district,
                'concelho': conc,
                'party_acronym': acronym,
                'seats': seats,
            })

    return records


def total_seats_per_municipality(records: List[Dict[str, Any]]) -> Dict[Tuple[str, str], int]:
    totals: Dict[Tuple[str, str], int] = {}
    for rec in records:
        key = (normalize_territory_key(rec['distrito']), normalize_territory_key(rec['concelho']))
        totals[key] = totals.get(key, 0) + rec['seats']
    return totals
