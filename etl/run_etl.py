"""
CLI entry point for the election ETL pipeline.

Examples:
  python run_etl.py
  python run_etl.py --dataset aut_2021 --mode staging-only
"""

import argparse
import sys

from config import DATASETS, DEFAULT_DATASET
from pipeline.runner import MODE_FULL, MODE_RELOAD_OPERATIONAL, MODE_STAGING_ONLY, run_pipeline, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description='Run election ETL pipeline')
    parser.add_argument(
        '--dataset',
        default=DEFAULT_DATASET,
        choices=sorted(DATASETS.keys()),
        help=f'Dataset key (default: {DEFAULT_DATASET})',
    )
    parser.add_argument(
        '--mode',
        default=MODE_STAGING_ONLY,
        choices=[MODE_FULL, MODE_STAGING_ONLY, MODE_RELOAD_OPERATIONAL],
        help='full = extract + operational load; staging-only = Excel to staging only',
    )
    args = parser.parse_args()

    setup_logging()
    try:
        run_pipeline(args.dataset, args.mode)
    except Exception:
        sys.exit(1)


if __name__ == '__main__':
    main()
