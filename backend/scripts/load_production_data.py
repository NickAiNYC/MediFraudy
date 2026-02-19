#!/usr/bin/env python3
"""
Production Data Loader for MediFraudy
Loads the 11GB ZIP file with 77.3M Medicaid claims into PostgreSQL
"""

import os
import zipfile
import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path
import logging
from tqdm import tqdm
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ZIP_PATH = Path("data/medicaid_claims.zip")
CSV_NAME = "medicaid-provider-spending.csv"
CHUNK_SIZE = 100000  # 100k rows per chunk
BATCH_SIZE = 10000   # Commit every 10k rows

def get_railway_db_url():
    """Get database URL from Railway"""
    import subprocess
    result = subprocess.run(['railway', 'variables', '--json'], 
                          capture_output=True, text=True)
    import json
    vars = json.loads(result.stdout)
    return vars.get('DATABASE_URL')

def load_claims_to_postgres(db_url, drop_existing=False):
    """Load claims data from ZIP to PostgreSQL"""
    
    engine = create_engine(db_url)
    
    # Check if ZIP exists
    if not ZIP_PATH.exists():
        logger.error(f"❌ ZIP file not found: {ZIP_PATH}")
        logger.info("Please place medicaid_claims.zip in the data/ directory")
        return False
    
    # Drop existing tables if requested
    if drop_existing:
        logger.warning("⚠️  Dropping existing tables...")
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS claims CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
            conn.commit()
    
    # Create tables if they don't exist
    logger.info("📦 Creating tables...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS providers (
                id SERIAL PRIMARY KEY,
                npi VARCHAR(20) UNIQUE,
                name VARCHAR(255),
                address TEXT,
                city VARCHAR(100),
                state VARCHAR(2),
                zip VARCHAR(10),
                facility_type VARCHAR(100),
                licensed_capacity INTEGER
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS claims (
                id SERIAL PRIMARY KEY,
                provider_id INTEGER REFERENCES providers(id),
                billing_code VARCHAR(20),
                amount DECIMAL(12,2),
                service_date DATE,
                submitted_date DATE,
                patient_id VARCHAR(50),
                diagnosis_code VARCHAR(20),
                status VARCHAR(20)
            )
        """))
        conn.commit()
    
    # Extract and load ZIP
    logger.info(f"📂 Extracting {ZIP_PATH}...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
        with zf.open(CSV_NAME) as f:
            # Read CSV in chunks
            chunks = pd.read_csv(f, chunksize=CHUNK_SIZE, low_memory=False)
            
            total_rows = 0
            for chunk in tqdm(chunks, desc="Loading claims"):
                # Process chunk
                chunk = chunk.dropna(subset=['npi'])  # Remove rows without NPI
                
                # Extract unique providers
                providers = chunk[['npi', 'provider_name', 'provider_address', 
                                   'provider_city', 'provider_state', 'provider_zip']].drop_duplicates()
                
                # Insert providers
                for i in range(0, len(providers), BATCH_SIZE):
                    batch = providers.iloc[i:i+BATCH_SIZE]
                    batch.to_sql('providers', engine, if_exists='append', 
                               index=False, method='multi')
                
                # Get provider IDs for claims
                with engine.connect() as conn:
                    npi_to_id = dict(conn.execute(
                        text("SELECT npi, id FROM providers")
                    ).fetchall())
                
                # Prepare claims with provider IDs
                chunk['provider_id'] = chunk['npi'].map(npi_to_id)
                chunk = chunk.dropna(subset=['provider_id'])
                
                # Insert claims
                claims_data = chunk[['provider_id', 'billing_code', 'amount', 
                                     'service_date', 'submitted_date', 
                                     'patient_id', 'diagnosis_code', 'status']]
                
                for i in range(0, len(claims_data), BATCH_SIZE):
                    batch = claims_data.iloc[i:i+BATCH_SIZE]
                    batch.to_sql('claims', engine, if_exists='append',
                               index=False, method='multi')
                
                total_rows += len(chunk)
                logger.info(f"✅ Loaded {total_rows:,} claims so far...")
    
    logger.info(f"🎉 SUCCESS! Loaded {total_rows:,} claims")
    return True

def verify_data(db_url):
    """Verify data was loaded correctly"""
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Check counts
        claims = conn.execute(text("SELECT COUNT(*) FROM claims")).scalar()
        providers = conn.execute(text("SELECT COUNT(*) FROM providers")).scalar()
        
        logger.info(f"📊 Final counts:")
        logger.info(f"   - Providers: {providers:,}")
        logger.info(f"   - Claims: {claims:,}")
        
        # Check NYC data
        nyc_providers = conn.execute(text("""
            SELECT COUNT(*) FROM providers 
            WHERE city IN ('NEW YORK', 'BROOKLYN', 'QUEENS', 'BRONX', 'STATEN ISLAND')
        """)).scalar()
        
        logger.info(f"🗽 NYC Providers: {nyc_providers:,}")
        
        # Sample some real data
        sample = conn.execute(text("""
            SELECT p.name, p.city, COUNT(c.id) as claim_count
            FROM providers p
            JOIN claims c ON p.id = c.provider_id
            WHERE p.city IN ('NEW YORK', 'BROOKLYN', 'QUEENS')
            GROUP BY p.id, p.name, p.city
            ORDER BY claim_count DESC
            LIMIT 5
        """)).fetchall()
        
        logger.info("📋 Top NYC Providers:")
        for row in sample:
            logger.info(f"   - {row.name} ({row.city}): {row.claim_count} claims")
        
        return claims > 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-url', help='PostgreSQL URL (or use Railway DATABASE_URL)')
    parser.add_argument('--drop', action='store_true', help='Drop existing tables')
    parser.add_argument('--verify-only', action='store_true', help='Only verify data')
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.db_url or get_railway_db_url() or os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("❌ No DATABASE_URL found. Set it or pass --db-url")
        return
    
    logger.info(f"🔌 Connecting to database...")
    
    if args.verify_only:
        verify_data(db_url)
        return
    
    # Load the data
    success = load_claims_to_postgres(db_url, drop_existing=args.drop)
    
    if success:
        logger.info("✅ Data loaded successfully!")
        verify_data(db_url)
    else:
        logger.error("❌ Failed to load data")

if __name__ == "__main__":
    main()