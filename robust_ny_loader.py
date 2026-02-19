#!/usr/bin/env python3
"""
Robust NY Medicaid data loader with connection retry
"""

import os
import zipfile
import csv
import psycopg2
from pathlib import Path
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    """Get a fresh database connection"""
    db_url = os.getenv('DATABASE_URL')
    return psycopg2.connect(db_url)

def load_chunk(chunk_data, attempt=1):
    """Load a chunk of data with retry logic"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            cur.executemany("""
                INSERT INTO claims (
                    billing_provider_npi, servicing_provider_npi, hcpcs_code,
                    claim_month, unique_beneficiaries, claim_count, amount
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, chunk_data)
            
            conn.commit()
            cur.close()
            conn.close()
            return len(chunk_data)
            
        except Exception as e:
            logger.warning(f"Chunk load attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Failed to load chunk after {max_attempts} attempts")
                return 0

def main():
    # Get database URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("❌ DATABASE_URL not set")
        return
    
    logger.info(f"🔌 Starting robust NY data loader...")
    
    # Clear existing data for clean load
    try:
        conn = get_connection()
        cur = conn.cursor()
        logger.info("🧹 Clearing existing data...")
        cur.execute('TRUNCATE TABLE claims CASCADE')
        cur.execute('TRUNCATE TABLE providers CASCADE')
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Clear data failed: {e}")
    
    # Check if ZIP exists
    zip_path = Path('medicaid-provider-spending.csv.zip')
    if not zip_path.exists():
        logger.error(f"❌ ZIP file not found: {zip_path}")
        return
    
    file_size_gb = zip_path.stat().st_size / (1024**3)
    logger.info(f"📦 ZIP file: {zip_path} ({file_size_gb:.2f} GB)")
    
    # Create tables
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        logger.info("📦 Creating NY-specific tables...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS providers (
                id SERIAL PRIMARY KEY,
                npi VARCHAR(20) UNIQUE,
                name VARCHAR(255),
                city VARCHAR(100),
                state VARCHAR(2) DEFAULT 'NY',
                specialty VARCHAR(100),
                total_beneficiaries INTEGER DEFAULT 0,
                total_claims INTEGER DEFAULT 0,
                total_amount DECIMAL(15,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                id SERIAL PRIMARY KEY,
                provider_id INTEGER REFERENCES providers(id),
                billing_provider_npi VARCHAR(20),
                servicing_provider_npi VARCHAR(20),
                hcpcs_code VARCHAR(20),
                claim_month VARCHAR(20),
                unique_beneficiaries INTEGER,
                claim_count INTEGER,
                amount DECIMAL(12,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("✅ NY tables created")
        
    except Exception as e:
        logger.error(f"Table creation failed: {e}")
        return
    
    # Extract and load CSV with robust error handling
    logger.info(f"📂 Loading NY Medicaid data from {zip_path}...")
    
    total_rows = 0
    chunk_size = 25  # Very small chunks for stability
    chunk = []
    provider_stats = {}
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        with zf.open('medicaid-provider-spending.csv') as f:
            # Skip header
            f.readline()
            
            for line_num, line in enumerate(f):
                # Parse CSV line
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                
                parts = line.split(',')
                if len(parts) < 7:
                    continue
                
                try:
                    billing_npi = parts[0].strip('"')
                    servicing_npi = parts[1].strip('"')
                    hcpcs_code = parts[2].strip('"')
                    claim_month = parts[3].strip('"')
                    beneficiaries = int(parts[4])
                    claims = int(parts[5])
                    amount = float(parts[6])
                    
                    # Track provider statistics
                    if billing_npi not in provider_stats:
                        provider_stats[billing_npi] = {
                            'beneficiaries': 0,
                            'claims': 0,
                            'amount': 0.0
                        }
                    provider_stats[billing_npi]['beneficiaries'] += beneficiaries
                    provider_stats[billing_npi]['claims'] += claims
                    provider_stats[billing_npi]['amount'] += amount
                    
                    chunk.append((
                        billing_npi, servicing_npi, hcpcs_code,
                        claim_month, beneficiaries, claims, amount
                    ))
                    
                    # Load chunk when full
                    if len(chunk) >= chunk_size:
                        loaded = load_chunk(chunk)
                        total_rows += loaded
                        chunk = []
                        
                        if total_rows % 500 == 0:
                            logger.info(f"✅ Loaded {total_rows:,} NY claims...")
                        
                        # Small delay to avoid overwhelming the database
                        time.sleep(0.1)
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Skipping line {line_num + 2}: {e}")
                    continue
            
            # Load final chunk
            if chunk:
                loaded = load_chunk(chunk)
                total_rows += loaded
    
    logger.info(f"🎉 Loaded {total_rows:,} NY claims")
    
    # Create provider records
    logger.info("📊 Creating NY provider records...")
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        provider_batch = []
        for npi, stats in provider_stats.items():
            provider_batch.append((
                npi,
                f'NY Provider {npi}',
                'NEW YORK',
                'MEDICAID',
                stats['beneficiaries'],
                stats['claims'],
                stats['amount']
            ))
            
            if len(provider_batch) >= 50:
                cur.executemany("""
                    INSERT INTO providers (npi, name, city, specialty, total_beneficiaries, total_claims, total_amount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, provider_batch)
                conn.commit()
                provider_batch = []
        
        # Insert remaining providers
        if provider_batch:
            cur.executemany("""
                INSERT INTO providers (npi, name, city, specialty, total_beneficiaries, total_claims, total_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, provider_batch)
            conn.commit()
        
        # Link claims to providers
        logger.info("🔗 Linking claims to providers...")
        cur.execute("""
            UPDATE claims 
            SET provider_id = providers.id 
            FROM providers 
            WHERE claims.billing_provider_npi = providers.npi
            AND claims.provider_id IS NULL
        """)
        conn.commit()
        
        # Final verification
        cur.execute("SELECT COUNT(*) FROM claims")
        claims = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM providers")
        providers = cur.fetchone()[0]
        
        cur.execute("""
            SELECT SUM(total_beneficiaries), SUM(total_claims), SUM(total_amount)
            FROM providers
        """)
        ny_stats = cur.fetchone()
        
        logger.info(f"📊 NY Medicaid Data Summary:")
        logger.info(f"   - Providers: {providers:,}")
        logger.info(f"   - Claims: {claims:,}")
        logger.info(f"   - Total Beneficiaries: {ny_stats[0]:,}")
        logger.info(f"   - Total Claims: {ny_stats[1]:,}")
        logger.info(f"   - Total Amount: ${ny_stats[2]:,.2f}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Provider creation failed: {e}")
    
    logger.info("🎉 NY Medicaid data loading completed!")

if __name__ == "__main__":
    main()
