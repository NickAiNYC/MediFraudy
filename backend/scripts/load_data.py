#!/usr/bin/env python
"""Load Medicaid dataset into database efficiently.

Supports large files (10GB+) via chunked processing and bulk inserts.
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
import math

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, engine, Base
from data_ingestion.loader import MedicaidDataLoader
from data_ingestion.transformer import transform_medicaid_data
from models import Provider, Claim
from scripts.classify_transporters import classify_transporters

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Column mapping from CSV/Parquet to Database Models
# Adjust these based on your actual dataset headers
PROVIDER_MAPPING = {
    'provider_npi': 'npi',
    'npi': 'npi',
    'billing_provider_npi_num': 'npi',
    'provider_name': 'name',
    'provider_last_name_org': 'name',
    'provider_street1': 'address',
    'provider_city': 'city',
    'provider_state': 'state',
    'provider_zip': 'zip_code',
    'provider_type': 'facility_type',
    'provider_specialty': 'specialty',
}

CLAIM_MAPPING = {
    'claim_id': 'claim_id',
    'beneficiary_id': 'beneficiary_id',
    'billing_code': 'billing_code',
    'hcpcs_code': 'billing_code',
    'total_amount': 'amount',
    'line_payment_amount': 'amount',
    'amount': 'amount',
    'total_paid': 'amount',
    'claim_date': 'claim_date',
    'service_date': 'claim_date',
    'claim_from_month': 'claim_date',
    'submitted_date': 'submitted_date',
    'units': 'units',
    'total_claims': 'units',
    'place_of_service': 'place_of_service',
}

def get_db_session():
    """Get a new database session."""
    return SessionLocal()

def map_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    """Rename columns based on mapping if they exist."""
    rename_map = {}
    for csv_col, db_col in mapping.items():
        if csv_col in df.columns:
            rename_map[csv_col] = db_col
    return df.rename(columns=rename_map)

def bulk_upsert_providers(session, providers_df: pd.DataFrame) -> Dict[str, int]:
    """Upsert providers and return NPI -> ID map."""
    if providers_df.empty:
        return {}

    # Deduplicate by NPI
    providers_df = providers_df.drop_duplicates(subset=['npi'])
    
    # Prepare data for insertion
    records = providers_df.to_dict(orient='records')
    
    # Define insert statement
    stmt = insert(Provider).values(records)
    
    # Define update on conflict (upsert)
    # We update fields if NPI exists
    update_dict = {
        col.name: col
        for col in stmt.excluded
        if col.name not in ['id', 'npi', 'created_at']
    }
    
    if update_dict:
        stmt = stmt.on_conflict_do_update(
            index_elements=['npi'],
            set_=update_dict
        )
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=['npi'])
        
    # Execute upsert
    session.execute(stmt)
    session.commit()
    
    # Fetch all relevant IDs (both new and existing)
    # This might be slow if we fetch ALL providers every time.
    # Optimization: Filter by NPIs in the current batch
    npis = providers_df['npi'].tolist()
    
    # Query for IDs
    # Using raw SQL for speed or ORM
    rows = session.query(Provider.id, Provider.npi).filter(Provider.npi.in_(npis)).all()
    
    return {row.npi: row.id for row in rows}

def process_chunk(df: pd.DataFrame, session, state_filter: str = None):
    """Process a single chunk of data."""
    # 1. Transform and Clean
    # Disable fraud features that require global context
    df = transform_medicaid_data(df, state=state_filter, add_fraud_features=False)
    
    if df.empty:
        return 0

    # 2. Map columns to DB schema
    df = map_columns(df, {**PROVIDER_MAPPING, **CLAIM_MAPPING})
    
    # Post-mapping cleanup
    # Ensure amount is numeric (handle $ and ,)
    if 'amount' in df.columns:
        df['amount'] = (
            df['amount'].astype(str)
            .str.replace('$', '', regex=False)
            .str.replace(',', '', regex=False)
        )
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
    # Ensure NPI is 10 digits
    if 'npi' in df.columns:
        df['npi'] = (
            df['npi'].astype(str)
            .str.replace(r'\D', '', regex=True)
            .str.zfill(10)
        )
    
    # Ensure required columns exist
    required_provider_cols = ['npi']
    if not all(col in df.columns for col in required_provider_cols):
        logger.warning(f"Skipping chunk: Missing provider NPI column. Available: {df.columns.tolist()}")
        return 0
        
    # Fill missing provider fields
    for col in ['name', 'address', 'city', 'state', 'zip_code', 'facility_type', 'specialty']:
        if col not in df.columns:
            if col == 'name':
                df['name'] = "Provider " + df['npi'].astype(str)
            else:
                df[col] = None
            
    # 3. Handle Providers
    # Extract unique provider data from this chunk
    provider_cols = ['npi', 'name', 'address', 'city', 'state', 'zip_code', 'facility_type', 'specialty']
    # Filter to columns that actually exist in df
    existing_provider_cols = [c for c in provider_cols if c in df.columns]
    
    providers_df = df[existing_provider_cols].drop_duplicates(subset=['npi'])
    
    # Upsert and get IDs
    npi_to_id = bulk_upsert_providers(session, providers_df)
    
    # 4. Handle Claims
    # Map NPI to provider_id
    df['provider_id'] = df['npi'].map(npi_to_id)
    
    # Drop rows where provider_id is missing (shouldn't happen if upsert worked)
    df = df.dropna(subset=['provider_id'])
    
    # Prepare claim records
    claim_cols = [
        'provider_id', 'claim_id', 'beneficiary_id', 'billing_code', 
        'amount', 'claim_date', 'submitted_date', 'units', 'place_of_service'
    ]
    
    # Ensure columns exist
    for col in claim_cols:
        if col not in df.columns:
            df[col] = None
            
    # Filter to claim columns
    claims_df = df[claim_cols].copy()
    
    # Convert dates
    if 'claim_date' in claims_df.columns:
        claims_df['claim_date'] = pd.to_datetime(claims_df['claim_date']).dt.date
    
    # Bulk insert claims
    # We use simple insert here. If claim_id collisions are a concern, we might need upsert.
    # Assuming new data or relying on claim_id constraints.
    # The Claim model has no unique constraint on claim_id alone (just an index),
    # but it's good practice to handle duplicates.
    # For speed, we'll try straight insert, and maybe ignore errors or use chunked insert.
    
    claims_records = claims_df.to_dict(orient='records')
    
    if not claims_records:
        return 0
        
    session.bulk_insert_mappings(Claim, claims_records)
    session.commit()
    
    return len(claims_records)

def main():
    parser = argparse.ArgumentParser(description="Load Medicaid dataset efficiently")
    parser.add_argument("--file", help="Path to dataset file", required=True)
    parser.add_argument("--url", help="URL to download from (optional)")
    parser.add_argument("--chunksize", type=int, default=50000, help="Chunk size (rows)")
    parser.add_argument("--state", default="NY", help="Filter to state (default: NY)")
    parser.add_argument("--limit", type=int, help="Limit total rows to load (for testing)")
    
    args = parser.parse_args()
    
    # Create tables if not exist
    logger.info("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    
    # Initialize Loader
    loader = MedicaidDataLoader(
        file_path=args.file,
        url=args.url,
    )
    
    session = get_db_session()
    total_claims = 0
    
    try:
        logger.info(f"Starting ingestion from {args.file}...")
        logger.info(f"Chunk size: {args.chunksize}, State filter: {args.state}")
        
        # We use the iter_data generator
        # To get a progress bar with ETA, we need total chunks.
        # Since we stream, we can't know exact rows, but we can estimate from file size.
        # 11GB file ~ 11,000,000 KB.
        # Avg row ~ 200 bytes? -> 50k rows ~ 10MB.
        # Total chunks ~ 11GB / 10MB ~ 1100 chunks.
        
        # Let's try to get file size for better progress bar
        total_size_bytes = os.path.getsize(args.file)
        if args.file.endswith('.zip'):
             import zipfile
             with zipfile.ZipFile(args.file) as z:
                 total_size_bytes = sum(zi.file_size for zi in z.infolist() if not zi.filename.startswith('__MACOSX'))
        
        # Estimate: 1 chunk (50k rows) is roughly 15MB of CSV data (very rough)
        # 11GB / 15MB = ~733 chunks.
        # Let's just use a manual progress bar or simple counter if we can't be precise.
        # But we can try to guess.
        estimated_chunks = int(total_size_bytes / (15 * 1024 * 1024)) 
        
        iterator = loader.iter_data(chunk_size=args.chunksize)
        
        # Use tqdm for progress if possible (chunks)
        pbar = tqdm(iterator, desc="Processing Chunks", unit="chunk", total=estimated_chunks)
        
        for i, df_chunk in enumerate(pbar):
            try:
                count = process_chunk(df_chunk, session, state_filter=args.state)
                total_claims += count
                pbar.set_postfix({"claims": total_claims})
                
                if args.limit and total_claims >= args.limit:
                    logger.info(f"Reached limit of {args.limit} claims.")
                    break
                    
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                session.rollback()
                # Continue to next chunk? Or stop?
                # For large loads, maybe continue but log error
                continue
                
        # After claims are loaded, classify transporters
        try:
            classify_transporters()
            logger.info("Transporter classification complete")
        except Exception as e:
            logger.error(f"Failed to classify transporters: {e}")
            
        logger.info(f"Ingestion complete. Total claims loaded: {total_claims}")
        
    except KeyboardInterrupt:
        logger.warning("Ingestion interrupted by user.")
    except Exception as e:
        logger.error(f"Fatal error during ingestion: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
