"""Small database helpers for the ETL runner."""

import logging
import sys

import psycopg2

from config import DB_CONFIG


def connect():
    try:
        return psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
        )
    except Exception as exc:
        logging.error('Database connection failed: %s', exc)
        sys.exit(1)
