"""
Legacy entry point. Prefer: python run_etl.py --dataset aut_2021 --mode staging-only
"""

from pipeline.runner import MODE_STAGING_ONLY, run_pipeline, setup_logging

if __name__ == '__main__':
    setup_logging()
    run_pipeline('aut_2021', MODE_STAGING_ONLY)
