"""
ETL runner: runs pipeline phases and writes staging.stg_etl_run_log.
"""

import logging
from typing import Any, Dict, Optional

from config import ETL_CONFIG, get_dataset_config, get_dataset_dirs

from pipeline.db import connect
from pipeline.extract import run_extract
from pipeline.load_warehouse import run_load_warehouse
from pipeline.post_load import run_post_load
from pipeline.transform_geo import run_transform_geo
from pipeline.transform_operational import run_transform_operational

# Modes supported by run_etl.py
MODE_FULL = 'full'
MODE_STAGING_ONLY = 'staging-only'
MODE_RELOAD_OPERATIONAL = 'reload-operational'


def clear_staging(conn) -> None:
    with conn.cursor() as cur:
        cur.execute('TRUNCATE staging.stg_election_results RESTART IDENTITY')
        cur.execute('TRUNCATE staging.stg_turnout_data RESTART IDENTITY')
    conn.commit()
    logging.info('Staging tables cleared')


def start_run(conn, dataset_key: str, mode: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO staging.stg_etl_run_log (run_name, run_type, status)
            VALUES (%s, %s, 'running')
            RETURNING run_id
            """,
            (f'{dataset_key} ({mode})', mode),
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def finish_run(conn, run_id: int, status: str, stats: Dict[str, Any], error: Optional[str] = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE staging.stg_etl_run_log
            SET end_time = CURRENT_TIMESTAMP,
                status = %s,
                rows_extracted = %s,
                rows_staged = %s,
                rows_transformed = %s,
                rows_loaded = %s,
                rows_rejected = %s,
                error_message = %s
            WHERE run_id = %s
            """,
            (
                status,
                stats.get('rows_extracted', 0),
                stats.get('rows_staged', 0),
                stats.get('rows_transformed', 0),
                stats.get('rows_loaded', 0),
                stats.get('rows_rejected', 0),
                error,
                run_id,
            ),
        )
    conn.commit()


def apply_operational_transform(conn, dataset_key: str, stats: Dict[str, Any]) -> None:
    transform_stats = run_transform_operational(conn, dataset_key)
    stats['rows_transformed'] = transform_stats.get('transformed', 0)
    stats['rows_loaded'] = transform_stats.get('loaded', 0)


def run_pipeline(dataset_key: str, mode: str = MODE_FULL) -> None:
    cfg = get_dataset_config(dataset_key)
    dataset_dirs = get_dataset_dirs(dataset_key)
    if not dataset_dirs:
        folders = cfg['data_dirs']
        raise FileNotFoundError(
            f"No data folders found for {dataset_key}. Expected under etl/data/: {folders}"
        )

    stats: Dict[str, Any] = {
        'rows_extracted': 0,
        'rows_staged': 0,
        'rows_transformed': 0,
        'rows_loaded': 0,
        'rows_rejected': 0,
    }

    conn = connect()
    run_id = start_run(conn, dataset_key, mode)

    try:
        if mode == MODE_STAGING_ONLY:
            clear_staging(conn)
            extract_stats = run_extract(
                conn, dataset_dirs, cfg.get('workbook_include')
            )
            stats.update(extract_stats)

        elif mode in (MODE_FULL, MODE_RELOAD_OPERATIONAL):
            clear_staging(conn)
            extract_stats = run_extract(
                conn, dataset_dirs, cfg.get('workbook_include')
            )
            stats.update(extract_stats)
            apply_operational_transform(conn, dataset_key, stats)
            geo_stats = run_transform_geo(conn)
            stats['rows_loaded'] = stats.get('rows_loaded', 0) + geo_stats.get(
                'districts_geo', 0
            ) + geo_stats.get('municipalities_geo', 0)
            if mode == MODE_FULL:
                wh_stats = run_load_warehouse(conn, dataset_key)
                stats['rows_loaded'] += wh_stats.get('warehouse_facts', 0)
            post_stats = run_post_load(conn, dataset_key)
            stats['rows_transformed'] += post_stats.get('summary_refreshed', 0)

        finish_run(conn, run_id, 'completed', stats)
        logging.info('Pipeline finished: dataset=%s mode=%s', dataset_key, mode)

    except Exception as exc:
        finish_run(conn, run_id, 'failed', stats, str(exc))
        logging.error('Pipeline failed: %s', exc)
        raise
    finally:
        conn.close()


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, ETL_CONFIG.get('log_level', 'INFO')),
        format='%(asctime)s - %(levelname)s - %(message)s',
    )
