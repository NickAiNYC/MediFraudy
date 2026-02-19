#!/usr/bin/env python3
"""
Simple Railway CSV loader without pandas
"""

import os
import zipfile
import csv
import psycopg2
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Get database URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("❌ DATABASE_URL not set")
        return
    
    logger.info(f"🔌 Connecting to database...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Clear existing data to avoid duplicates
    logger.info("🧹 Clearing existing data...")
    cur.execute('TRUNCATE TABLE claims CASCADE')
    cur.execute('TRUNCATE TABLE providers CASCADE')
    conn.commit()
    
    # Check if ZIP exists
    zip_path = Path('/tmp/medicaid_claims.zip')
    if not zip_path.exists():
        logger.error(f"❌ ZIP file not found: {zip_path}")
        return
    
    file_size_gb = zip_path.stat().st_size / (1024**3)
    logger.info(f"📦 ZIP file: {zip_path} ({file_size_gb:.2f} GB)")
    
    # Create tables with minimal schema that works
    logger.info("📦 Creating tables...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS providers (
            id SERIAL PRIMARY KEY,
            npi VARCHAR(20) UNIQUE,
            name VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(2)
        )
    """)
    
    cur.execute("""
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
    """)
    conn.commit()
    logger.info("✅ Tables created")
    
    # Extract and load CSV
    logger.info(f"📂 Loading data from {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        with zf.open('medicaid-provider-spending.csv') as f:
            # Skip header
            f.readline()
            
            total_rows = 0
            batch_size = 100
            batch = []
            
            for line_num, line in enumerate(f):
                if total_rows >= 1000:  # Limit to 1000 for testing
                    break
                
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
                    
                    # Insert provider if not exists
                    cur.execute("""
                        INSERT INTO providers (npi, name, city, state)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (npi) DO NOTHING
                    """, (billing_npi, f'Provider {billing_npi}', 'NEW YORK', 'NY'))
                    
                    # Get provider ID
                    cur.execute("SELECT id FROM providers WHERE npi = %s", (billing_npi,))
                    result = cur.fetchone()
                    if not result:
                        continue
                    
                    provider_id = result[0]
                    
                    batch.append((
                        provider_id, billing_npi, servicing_npi, hcpcs_code,
                        claim_month, beneficiaries, claims, amount
                    ))
                    
                    # Insert batch
                    if len(batch) >= batch_size:
                        cur.executemany("""
                            INSERT INTO claims (
                                provider_id, billing_provider_npi, servicing_provider_npi,
                                billing_code, claim_date, unique_beneficiaries,
                                claim_count, amount
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, batch)
                        conn.commit()
                        total_rows += len(batch)
                        batch = []
                        
                        if total_rows % 500 == 0:
                            logger.info(f"✅ Loaded {total_rows} rows...")
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Skipping line {line_num + 2}: {e}")
                    continue
            
            # Insert remaining batch
            if batch:
                cur.executemany("""
                    INSERT INTO claims (
                        provider_id, billing_provider_npi, servicing_provider_npi,
                        billing_code, claim_date, unique_beneficiaries,
                        claim_count, amount
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, batch)
                conn.commit()
                total_rows += len(batch)
    
    logger.info(f"🎉 SUCCESS! Loaded {total_rows} claims")
    
    # Verify data
    cur.execute("SELECT COUNT(*) FROM claims")
    claims = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM providers")
    providers = cur.fetchone()[0]
    
    logger.info(f"📊 Final counts:")
    logger.info(f"   - Providers: {providers}")
    logger.info(f"   - Claims: {claims}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
