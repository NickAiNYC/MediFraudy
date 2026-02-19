Python 3.14.2 (v3.14.2:df793163d58, Dec  5 2025, 12:18:06) [Clang 16.0.0 (clang-1600.0.26.6)] on darwin
Enter "help" below or click "Help" above for more information.
>>> #!/usr/bin/env python3
... """
... RESILIENT Medicaid Data Loader for MediFraudy
... Handles connection drops and large datasets gracefully
... """
... 
... import os
... import zipfile
... import pandas as pd
... from sqlalchemy import create_engine, text
... from pathlib import Path
... import logging
... from tqdm import tqdm
... import argparse
... import time
... import json
... 
... logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
... logger = logging.getLogger(__name__)
... 
... # Configuration
... ZIP_PATH = Path("data/medicaid_claims.zip")
... CSV_NAME = "medicaid-provider-spending.csv"
... CHUNK_SIZE = 100000  # Smaller chunks for stability
... PROVIDER_BATCH_SIZE = 5000
... CLAIM_BATCH_SIZE = 2000  # Smaller batches for claims
... 
... def get_db_url(args_db_url):
...     """Get database URL from args or environment"""
...     if args_db_url:
...         return args_db_url
...     return os.getenv('DATABASE_URL')
... 
... def create_engine_with_retry(db_url, max_retries=3):
...     """Create engine with connection retry logic"""
...     for attempt in range(max_retries):
        try:
            engine = create_engine(
                db_url,
                connect_args={'connect_timeout': 30},
                pool_pre_ping=True,
                pool_recycle=300,  # Recycle connections every 5 minutes
                pool_size=5,
                max_overflow=10
            )
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection established")
            return engine
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Connection attempt {attempt + 1} failed, retrying...")
                time.sleep(5)
            else:
                logger.error(f"Failed to connect after {max_retries} attempts")
                raise

def reset_database(engine):
    """Drop and recreate tables"""
    logger.info("🗑️  Dropping existing tables...")
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS claims CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS providers CASCADE"))
        conn.commit()
    
    logger.info("🏗️  Creating tables...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE providers (
                id SERIAL PRIMARY KEY,
                npi VARCHAR(20) UNIQUE,
                name VARCHAR(255) DEFAULT 'Unknown Provider',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE claims (
                id SERIAL PRIMARY KEY,
                provider_id INTEGER REFERENCES providers(id),
                billing_provider_npi VARCHAR(20),
                billing_code VARCHAR(20),
                amount DECIMAL(12,2),
                service_month VARCHAR(7),
                total_unique_beneficiaries INTEGER,
                total_claims_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("CREATE INDEX idx_providers_npi ON providers(npi)"))
        conn.execute(text("CREATE INDEX idx_claims_provider_id ON claims(provider_id)"))
        conn.commit()
    logger.info("✅ Tables created")

def insert_providers_batch(engine, npis_batch):
    """Insert a batch of providers with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            values = []
            for npi in npis_batch:
                values.append(f"('{npi}')")
            
            with engine.connect() as conn:
                conn.execute(text(f"""
                    INSERT INTO providers (npi) 
                    VALUES {','.join(values)}
                    ON CONFLICT (npi) DO NOTHING
                """))
                conn.commit()
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Provider insert failed (attempt {attempt + 1}), retrying...")
                time.sleep(2)
            else:
                logger.error(f"Failed to insert provider batch after {max_retries} attempts")
                return False

def insert_claims_batch(engine, claims_batch):
    """Insert a batch of claims with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO claims 
                        (provider_id, billing_provider_npi, billing_code, amount, 
                         service_month, total_unique_beneficiaries, total_claims_count)
                        VALUES (:provider_id, :billing_provider_npi, :billing_code, :amount,
                                :service_month, :total_unique_beneficiaries, :total_claims_count)
                    """),
                    claims_batch
                )
                conn.commit()
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Claims insert failed (attempt {attempt + 1}), retrying...")
                time.sleep(2)
            else:
                logger.error(f"Failed to insert claims batch after {max_retries} attempts: {e}")
                return False

def load_data_resilient(db_url, reset=False, max_chunks=None):
    """Load data with resilience to connection drops"""
    
    if not ZIP_PATH.exists():
        logger.error(f"❌ ZIP file not found: {ZIP_PATH}")
        logger.info("Please place medicaid_claims.zip in the data/ directory")
        return False
    
    # Create engine with retry
    engine = create_engine_with_retry(db_url)
    
    if reset:
        reset_database(engine)
    
    file_size = ZIP_PATH.stat().st_size / (1024**3)
    logger.info(f"📂 Processing {ZIP_PATH.name} ({file_size:.2f} GB)")
    
    start_time = time.time()
    
    # Check if providers already exist
    with engine.connect() as conn:
        existing_providers = conn.execute(text("SELECT COUNT(*) FROM providers")).scalar()
    
    if existing_providers == 0 or reset:
        # First pass: collect all unique NPIs
        logger.info("🔍 First pass: Collecting unique NPIs...")
        all_providers = set()
        chunk_count = 0
        
        with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
            with zf.open(CSV_NAME) as f:
                # Specify dtype to avoid warnings
                for chunk in pd.read_csv(f, chunksize=CHUNK_SIZE, 
                                        usecols=['BILLING_PROVIDER_NPI_NUM'],
                                        dtype={'BILLING_PROVIDER_NPI_NUM': str}):
                    chunk = chunk.dropna()
                    all_providers.update(chunk['BILLING_PROVIDER_NPI_NUM'].unique())
                    chunk_count += 1
                    
                    if chunk_count % 10 == 0:
                        logger.info(f"   Scanned {chunk_count * CHUNK_SIZE:,} rows, found {len(all_providers):,} providers")
        
        logger.info(f"📊 Found {len(all_providers):,} unique providers")
        
        # Insert providers in batches
        logger.info("💾 Inserting providers...")
        providers_list = list(all_providers)
        
        for i in range(0, len(providers_list), PROVIDER_BATCH_SIZE):
            batch = providers_list[i:i+PROVIDER_BATCH_SIZE]
            success = insert_providers_batch(engine, batch)
            
            if not success:
                logger.error("Stopping due to provider insert failure")
                return False
            
            if (i // PROVIDER_BATCH_SIZE) % 10 == 0:
                logger.info(f"   Inserted {min(i+PROVIDER_BATCH_SIZE, len(providers_list)):,} providers...")
    
    # Get provider ID mapping
    logger.info("🔗 Creating provider ID mapping...")
    provider_df = pd.read_sql("SELECT id, npi FROM providers", engine)
    npi_to_id = dict(zip(provider_df['npi'], provider_df['id']))
    logger.info(f"   Mapped {len(npi_to_id):,} providers")
    
    # Second pass: load claims
    logger.info("📥 Second pass: Loading claims (with connection resilience)...")
    total_claims = 0
    chunk_count = 0
    
    with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
        with zf.open(CSV_NAME) as f:
            chunks = pd.read_csv(f, chunksize=CHUNK_SIZE, 
                                dtype={'BILLING_PROVIDER_NPI_NUM': str,
                                      'HCPCS_CODE': str,
                                      'TOTAL_PAID': float,
                                      'CLAIM_FROM_MONTH': str,
                                      'TOTAL_UNIQUE_BENEFICIARIES': float,
                                      'TOTAL_CLAIMS': float})
            
            for chunk_idx, chunk in enumerate(tqdm(chunks, desc="Loading claims")):
                # Check if we've hit the limit
                if max_chunks and chunk_idx >= max_chunks:
                    logger.info(f"Reached max chunks limit ({max_chunks})")
                    break
                
                try:
                    # Clean and prepare data
                    chunk = chunk.dropna(subset=['BILLING_PROVIDER_NPI_NUM'])
                    chunk['BILLING_PROVIDER_NPI_NUM'] = chunk['BILLING_PROVIDER_NPI_NUM'].astype(str)
                    
                    # Map to provider IDs
                    chunk['provider_id'] = chunk['BILLING_PROVIDER_NPI_NUM'].map(npi_to_id)
                    chunk = chunk.dropna(subset=['provider_id'])
                    
                    if len(chunk) == 0:
                        continue
                    
                    # Prepare claims data
                    claims_batch = []
                    for _, row in chunk.iterrows():
                        claims_batch.append({
                            'provider_id': int(row['provider_id']),
                            'billing_provider_npi': str(row['BILLING_PROVIDER_NPI_NUM'])[:20],
                            'billing_code': str(row.get('HCPCS_CODE', ''))[:20],
                            'amount': float(row.get('TOTAL_PAID', 0)),
                            'service_month': str(row.get('CLAIM_FROM_MONTH', ''))[:7],
                            'total_unique_beneficiaries': int(float(row.get('TOTAL_UNIQUE_BENEFICIARIES', 0))),
                            'total_claims_count': int(float(row.get('TOTAL_CLAIMS', 0)))
                        })
                    
                    # Insert in smaller batches
                    for i in range(0, len(claims_batch), CLAIM_BATCH_SIZE):
                        small_batch = claims_batch[i:i+CLAIM_BATCH_SIZE]
                        success = insert_claims_batch(engine, small_batch)
                        
                        if not success:
                            logger.warning(f"Failed to insert batch at chunk {chunk_idx}, continuing...")
                            time.sleep(5)  # Wait before continuing
                    
                    total_claims += len(chunk)
                    chunk_count += 1
                    
                    # Progress update
                    if chunk_count % 5 == 0:
                        elapsed = time.time() - start_time
                        rate = total_claims / elapsed if elapsed > 0 else 0
                        logger.info(f"   Progress: {total_claims:,} claims ({rate:,.0f} claims/sec)")
                        
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk_idx}: {e}")
                    logger.info("🔄 Continuing with next chunk...")
                    time.sleep(10)
                    continue
    
    elapsed = time.time() - start_time
    logger.info(f"\n🎉 SUCCESS! Loaded {total_claims:,} claims in {elapsed/60:.1f} minutes")
    
    # Final verification
    with engine.connect() as conn:
        provider_count = conn.execute(text("SELECT COUNT(*) FROM providers")).scalar()
        claim_count = conn.execute(text("SELECT COUNT(*) FROM claims")).scalar()
        
        logger.info(f"\n📊 FINAL COUNTS:")
        logger.info(f"   Providers: {provider_count:,}")
        logger.info(f"   Claims: {claim_count:,}")
        
        if claim_count > 0:
            # Sample some data
            sample = conn.execute(text("""
                SELECT p.npi, COUNT(c.id) as claim_count 
                FROM providers p 
                JOIN claims c ON p.id = c.provider_id 
                GROUP BY p.npi 
                ORDER BY claim_count DESC 
                LIMIT 3
            """)).fetchall()
            
            logger.info("\n📋 Sample top providers:")
            for row in sample:
                logger.info(f"   NPI {row[0]}: {row[1]:,} claims")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Load Medicaid data resiliently')
    parser.add_argument('--db-url', help='PostgreSQL URL')
    parser.add_argument('--reset', action='store_true', help='Reset database before loading')
    parser.add_argument('--test', action='store_true', help='Test mode (load only 10 chunks)')
    parser.add_argument('--resume', action='store_true', help='Resume loading (keep existing providers)')
    args = parser.parse_args()
    
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     MEDIFRAUDY - RESILIENT DATA LOADER                    ║")
    print("║     Handles connection drops and large datasets           ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    db_url = get_db_url(args.db_url)
    if not db_url:
        logger.error("❌ No DATABASE_URL found")
        return
    
    # If resuming, don't reset
    if args.resume:
        args.reset = False
        logger.info("🔄 Resume mode: keeping existing providers")
    
    # Test mode - only load 10 chunks
    max_chunks = 10 if args.test else None
    if args.test:
        logger.info("🧪 TEST MODE: Loading only 10 chunks")
    
    success = load_data_resilient(db_url, reset=args.reset, max_chunks=max_chunks)
    
    if success:
        print("\n" + "="*60)
        print("✅✅✅ DATA LOAD COMPLETE! ✅✅✅")
        print("="*60)
        print("\nYour Railway database now has the Medicaid data!")
        if args.test:
            print("\n⚠️  This was a TEST run. Run without --test to load all data.")
    else:
        logger.error("❌ Failed to load data")

if __name__ == "__main__":
