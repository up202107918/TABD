"""
Main ETL Pipeline for Election Analytics Platform
Advanced Topics in Databases - Practical Assignment

This script orchestrates the complete ETL process:
1. Extract: Download and extract official election data
2. Transform: Clean, normalize, and validate data
3. Load: Insert into operational schema and populate warehouse
"""

import psycopg2
import psycopg2.extras
import logging
import sys
from datetime import datetime
from typing import Optional, Dict, List
import pandas as pd
import zipfile
import urllib.request
import os

from config import (
    DB_CONFIG, SCHEMAS, DATA_SOURCES, DATA_DIRS, 
    ETL_CONFIG, ensure_data_directories
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, ETL_CONFIG['log_level']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIRS['logs'], 'etl_pipeline.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class ETLPipeline:
    """Main ETL Pipeline orchestrator"""
    
    def __init__(self):
        self.conn = None
        self.run_id = None
        ensure_data_directories()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.autocommit = False
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def start_etl_run(self, run_name: str, run_type: str = 'full_load') -> int:
        """Log the start of an ETL run"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO staging.stg_etl_run_log (run_name, run_type, status)
                VALUES (%s, %s, 'running')
                RETURNING run_id
            """, (run_name, run_type))
            run_id = cur.fetchone()[0]
            self.conn.commit()
            logger.info(f"Started ETL run {run_id}: {run_name}")
            return run_id
    
    def end_etl_run(self, run_id: int, status: str, stats: Optional[Dict] = None, error: Optional[str] = None):
        """Log the end of an ETL run"""
        with self.conn.cursor() as cur:
            cur.execute("""
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
            """, (
                status,
                stats.get('extracted', 0) if stats else 0,
                stats.get('staged', 0) if stats else 0,
                stats.get('transformed', 0) if stats else 0,
                stats.get('loaded', 0) if stats else 0,
                stats.get('rejected', 0) if stats else 0,
                error,
                run_id
            ))
            self.conn.commit()
            logger.info(f"Ended ETL run {run_id} with status: {status}")
    
    def download_data(self, force_download: bool = False):
        """Download official election data if not already present"""
        logger.info("Starting data download phase")
        
        for source_name, url in DATA_SOURCES.items():
            filename = url.split('/')[-1]
            filepath = os.path.join(DATA_DIRS['downloads'], filename)
            
            if os.path.exists(filepath) and not force_download:
                logger.info(f"File {filename} already exists, skipping download")
                continue
            
            try:
                logger.info(f"Downloading {source_name} from {url}")
                urllib.request.urlretrieve(url, filepath)
                logger.info(f"Downloaded {filename}")
                
                # Extract if zip file
                if filename.endswith('.zip'):
                    extract_dir = os.path.join(DATA_DIRS['extracted'], source_name)
                    os.makedirs(extract_dir, exist_ok=True)
                    
                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    logger.info(f"Extracted {filename} to {extract_dir}")
                    
            except Exception as e:
                logger.error(f"Failed to download {source_name}: {e}")
                raise
    
    def clear_staging_tables(self):
        """Clear all staging tables before new load"""
        logger.info("Clearing staging tables")
        
        with self.conn.cursor() as cur:
            tables = ['stg_election_results', 'stg_turnout_data', 'stg_geographic_boundaries']
            for table in tables:
                cur.execute(f"TRUNCATE TABLE staging.{table} CASCADE")
                logger.debug(f"Truncated staging.{table}")
        
        self.conn.commit()
        logger.info("Staging tables cleared")
    
    def load_staging_from_csv(self, csv_path: str, staging_table: str) -> int:
        """Load CSV data into staging table"""
        logger.info(f"Loading {csv_path} into staging.{staging_table}")
        
        try:
            # Read CSV with pandas
            df = pd.read_csv(csv_path, encoding='utf-8-sig', low_memory=False)
            rows_loaded = 0
            
            # Map DataFrame columns to staging table columns
            # This will depend on the actual CSV structure
            # For demonstration, assuming the CSV has matching column names
            
            with self.conn.cursor() as cur:
                # Create the INSERT statement dynamically based on columns
                columns = df.columns.tolist()
                placeholders = ', '.join(['%s'] * len(columns))
                insert_sql = f"""
                    INSERT INTO staging.{staging_table} ({', '.join(columns)}, source_file)
                    VALUES ({placeholders}, %s)
                """
                
                # Insert in batches
                batch_size = ETL_CONFIG['batch_size']
                for i in range(0, len(df), batch_size):
                    batch = df.iloc[i:i+batch_size]
                    values = [tuple(row) + (csv_path,) for row in batch.values]
                    
                    psycopg2.extras.execute_batch(cur, insert_sql, values)
                    rows_loaded += len(values)
                    
                    if i % (batch_size * 10) == 0:
                        logger.debug(f"Loaded {rows_loaded} rows so far...")
            
            self.conn.commit()
            logger.info(f"Loaded {rows_loaded} rows into staging.{staging_table}")
            return rows_loaded
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to load staging data: {e}")
            raise
    
    def transform_and_load_geography(self):
        """Transform geography data from staging to operational schema"""
        logger.info("Transforming and loading geography data")
        
        with self.conn.cursor() as cur:
            # Load districts
            cur.execute("""
                INSERT INTO operational.district (district_code, district_name)
                SELECT DISTINCT 
                    staging.extract_district_code(distrito),
                    staging.normalize_municipality_name(distrito)
                FROM staging.stg_election_results
                WHERE staging.extract_district_code(distrito) IS NOT NULL
                ON CONFLICT (district_code) DO NOTHING
            """)
            districts_loaded = cur.rowcount
            
            # Load municipalities
            cur.execute("""
                INSERT INTO operational.municipality (municipality_code, municipality_name, district_id)
                SELECT DISTINCT 
                    CONCAT(staging.extract_district_code(s.distrito), 
                           LPAD(ROW_NUMBER() OVER (PARTITION BY s.distrito ORDER BY s.concelho)::TEXT, 2, '0')),
                    staging.normalize_municipality_name(s.concelho),
                    d.district_id
                FROM staging.stg_election_results s
                JOIN operational.district d ON d.district_code = staging.extract_district_code(s.distrito)
                WHERE s.concelho IS NOT NULL
                ON CONFLICT (municipality_code) DO NOTHING
            """)
            municipalities_loaded = cur.rowcount
            
        self.conn.commit()
        logger.info(f"Loaded {districts_loaded} districts and {municipalities_loaded} municipalities")
        
        return {'districts': districts_loaded, 'municipalities': municipalities_loaded}
    
    def transform_and_load_parties(self):
        """Transform party data from staging to operational schema"""
        logger.info("Transforming and loading party data")
        
        with self.conn.cursor() as cur:
            # Extract unique parties from staging
            cur.execute("""
                INSERT INTO operational.party (party_acronym, party_name)
                SELECT DISTINCT 
                    UPPER(TRIM(candidatura)) as acronym,
                    candidatura as name
                FROM staging.stg_election_results
                WHERE candidatura NOT LIKE '%/%'  -- Exclude coalitions for now
                    AND candidatura IS NOT NULL
                ON CONFLICT (party_acronym) DO NOTHING
            """)
            parties_loaded = cur.rowcount
            
        self.conn.commit()
        logger.info(f"Loaded {parties_loaded} parties")
        
        return parties_loaded
    
    def transform_and_load_results(self):
        """Transform election results from staging to operational schema"""
        logger.info("Transforming and loading election results")
        
        # This is a complex transformation that would require:
        # 1. Creating candidacies
        # 2. Loading vote results
        # 3. Loading seat results
        # 4. Loading turnout data
        
        # For demonstration, simplified version:
        with self.conn.cursor() as cur:
            # Get the 2021 election ID
            cur.execute("""
                SELECT election_id FROM operational.election 
                WHERE election_year = 2021 
                LIMIT 1
            """)
            election_id = cur.fetchone()[0]
            
            logger.info(f"Loading results for election_id: {election_id}")
            
            # More complex transformation logic would go here
            # This would involve multiple steps to properly create candidacies
            # and link all the related data
            
        self.conn.commit()
        logger.info("Election results transformation complete")
        
        return {'results_loaded': 0}  # Placeholder
    
    def populate_warehouse(self):
        """Populate data warehouse from operational schema"""
        logger.info("Populating data warehouse")
        
        with self.conn.cursor() as cur:
            # Populate dimension tables
            logger.info("Populating dimension: elections")
            cur.execute("""
                INSERT INTO warehouse.dim_election (
                    election_id, election_type_code, election_type_name,
                    election_date, election_year, election_description
                )
                SELECT 
                    e.election_id,
                    et.type_code,
                    et.type_name,
                    e.election_date,
                    e.election_year,
                    e.description
                FROM operational.election e
                JOIN operational.election_type et ON e.election_type_id = et.election_type_id
                ON CONFLICT (election_id) DO UPDATE SET
                    election_description = EXCLUDED.election_description
            """)
            
            logger.info("Populating dimension: districts")
            cur.execute("""
                INSERT INTO warehouse.dim_district (
                    district_id, district_code, district_name
                )
                SELECT district_id, district_code, district_name
                FROM operational.district
                ON CONFLICT (district_id) DO UPDATE SET
                    district_name = EXCLUDED.district_name
            """)
            
            logger.info("Populating dimension: municipalities")
            cur.execute("""
                INSERT INTO warehouse.dim_municipality (
                    municipality_id, municipality_code, municipality_name,
                    district_key, district_name
                )
                SELECT 
                    m.municipality_id,
                    m.municipality_code,
                    m.municipality_name,
                    dd.district_key,
                    d.district_name
                FROM operational.municipality m
                JOIN operational.district d ON m.district_id = d.district_id
                JOIN warehouse.dim_district dd ON dd.district_id = d.district_id
                ON CONFLICT (municipality_id) DO UPDATE SET
                    municipality_name = EXCLUDED.municipality_name
            """)
            
            # Populate fact tables would go here
            # This requires more complex logic to properly denormalize and aggregate
            
        self.conn.commit()
        logger.info("Data warehouse population complete")
    
    def run_full_pipeline(self, download: bool = True):
        """Execute the complete ETL pipeline"""
        logger.info("="*80)
        logger.info("Starting full ETL pipeline")
        logger.info("="*80)
        
        stats = {
            'extracted': 0,
            'staged': 0,
            'transformed': 0,
            'loaded': 0,
            'rejected': 0
        }
        
        try:
            self.connect()
            self.run_id = self.start_etl_run('Full Pipeline Run', 'full_load')
            
            # Phase 1: Extract
            if download:
                self.download_data()
            
            # Phase 2: Stage
            self.clear_staging_tables()
            # Load CSV files would go here
            # stats['staged'] = self.load_staging_from_csv(...)
            
            # Phase 3: Transform & Load
            geo_stats = self.transform_and_load_geography()
            stats['loaded'] += geo_stats.get('districts', 0) + geo_stats.get('municipalities', 0)
            
            party_stats = self.transform_and_load_parties()
            stats['loaded'] += party_stats
            
            result_stats = self.transform_and_load_results()
            stats['loaded'] += result_stats.get('results_loaded', 0)
            
            # Phase 4: Populate Warehouse
            self.populate_warehouse()
            
            # Mark run as successful
            self.end_etl_run(self.run_id, 'completed', stats)
            
            logger.info("="*80)
            logger.info("ETL Pipeline completed successfully")
            logger.info(f"Statistics: {stats}")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"ETL Pipeline failed: {e}", exc_info=True)
            if self.run_id:
                self.end_etl_run(self.run_id, 'failed', stats, str(e))
            raise
        
        finally:
            self.disconnect()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Election Analytics ETL Pipeline')
    parser.add_argument('--skip-download', action='store_true', help='Skip data download phase')
    parser.add_argument('--staging-only', action='store_true', help='Only load staging tables')
    
    args = parser.parse_args()
    
    pipeline = ETLPipeline()
    
    try:
        pipeline.run_full_pipeline(download=not args.skip_download)
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
