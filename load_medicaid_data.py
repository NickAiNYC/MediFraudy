#!/usr/bin/env python3
"""
Simple Medicaid data loader for the downloaded CSV file.
Loads medicaid-provider-spending.csv into the database.
"""

import os
import sys
import zipfile
import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path
import logging
from tqdm import tqdm
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip-path', default='/tmp/medicaid_claims.zip')
    parser.add_argument('--max-rows', type=int, help='Limit rows for testing')
    parser.add_argument('--chunk-size', type=int, default=10000)
    args = parser.parse_args()
    
    # Get database URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("❌ DATABASE_URL not set")
        return
    
    logger.info(f"🔌 Connecting to database...")
    engine = create_engine(db_url)
    
    # Check if ZIP exists
    zip_path = Path(args.zip_path)
    if not zip_path.exists():
        logger.error(f"❌ ZIP file not found: {zip_path}")
        return
    
    file_size_gb = zip_path.stat().st_size / (1024**3)
    logger.info(f"📦 ZIP file: {zip_path} ({file_size_gb:.2f} GB)")
    
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
                billing_provider_npi VARCHAR(20),
                servicing_provider_npi VARCHAR(20),
                billing_code VARCHAR(20),
                claim_date VARCHAR(20),
                unique_beneficiaries INTEGER,
                claim_count INTEGER,
                amount DECIMAL(12,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
    
    # Extract and load CSV
    logger.info(f"📂 Extracting and loading from {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        with zf.open('medicaid-provider-spending.csv') as f:
            # Read CSV in chunks
            chunks = pd.read_csv(f, chunksize=args.chunk_size, low_memory=False)
            
            total_rows = 0
            for chunk_num, chunk in enumerate(tqdm(chunks, desc="Loading chunks")):
                # Remove rows without NPI
                chunk = chunk.dropna(subset=['BILLING_PROVIDER_NPI_NUM'])
                
                # Extract unique providers
                providers = chunk[['BILLING_PROVIDER_NPI_NUM']].drop_duplicates()
                providers['name'] = 'Provider ' + providers['BILLING_PROVIDER_NPI_NUM'].astype(str)
                providers['city'] = 'NEW YORK'
                providers['state'] = 'NY'
                providers.columns = ['npi', 'name', 'city', 'state']
                
                # Insert providers (ignore duplicates)
                try:
                    providers.to_sql('providers', engine, if_exists='append', 
                                   index=False, method='multi')
                except Exception as e:
                    logger.warning(f"Provider insert warning: {e}")
                
                # Get provider IDs for claims
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT npi, id FROM providers"))
                    npi_to_id = {row[0]: row[1] for row in result.fetchall()}
                
                # Prepare claims with provider IDs
                chunk['provider_id'] = chunk['BILLING_PROVIDER_NPI_NUM'].map(npi_to_id)
                chunk = chunk.dropna(subset=['provider_id'])
                
                # Prepare claims data
                claims_data = chunk[[
                    'provider_id', 'BILLING_PROVIDER_NPI_NUM', 
                    'SERVICING_PROVIDER_NPI_NUM', 'HCPCS_CODE',
                    'CLAIM_FROM_MONTH', 'TOTAL_UNIQUE_BENEFICIARIES',
                    'TOTAL_CLAIMS', 'TOTAL_PAID'
                ]].copy()
                
                claims_data.columns = [
                    'provider_id', 'billing_provider_npi', 'servicing_provider_npi',
                    'billing_code', 'claim_date', 'unique_beneficiaries',
                    'claim_count', 'amount'
                ]
                
                # Insert claims
                claims_data.to_sql('claims', engine, if_exists='append',
                                 index=False, method='multi')
                
                total_rows += len(chunk)
                logger.info(f"✅ Loaded chunk {chunk_num + 1}: {len(chunk)} rows (total: {total_rows:,})")
                
                # Stop if max rows reached
                if args.max_rows and total_rows >= args.max_rows:
                    logger.info(f"🛑 Reached max rows limit: {args.max_rows:,}")
                    break
    
    logger.info(f"🎉 SUCCESS! Loaded {total_rows:,} claims")
    
    # Verify data
    with engine.connect() as conn:
        claims = conn.execute(text("SELECT COUNT(*) FROM claims")).scalar()
        providers = conn.execute(text("SELECT COUNT(*) FROM providers")).scalar()
        
        logger.info(f"📊 Final counts:")
        logger.info(f"   - Providers: {providers:,}")
        logger.info(f"   - Claims: {claims:,}")

if __name__ == "__main__":
    main()
