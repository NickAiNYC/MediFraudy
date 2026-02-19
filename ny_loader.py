#!/usr/bin/env python3
"""
New York focused Medicaid data loader
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

def main():
    # Get database URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("❌ DATABASE_URL not set")
        return
    
    logger.info(f"🔌 Connecting to database...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Clear existing data for clean load
    logger.info("🧹 Clearing existing data...")
    try:
        cur.execute('TRUNCATE TABLE claims CASCADE')
        cur.execute('TRUNCATE TABLE providers CASCADE')
        conn.commit()
    except psycopg2.errors.UndefinedTable:
        logger.info("Tables don't exist yet, will create new ones")
        conn.rollback()
    
    # Check if ZIP exists
    zip_path = Path('medicaid-provider-spending.csv.zip')
    if not zip_path.exists():
        logger.error(f"❌ ZIP file not found: {zip_path}")
        return
    
    file_size_gb = zip_path.stat().st_size / (1024**3)
    logger.info(f"📦 ZIP file: {zip_path} ({file_size_gb:.2f} GB)")
    
    # Create NY-specific tables
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
    
    # Create indexes for performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_claims_provider_npi ON claims(billing_provider_npi)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_claims_hcpcs ON claims(hcpcs_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_claims_month ON claims(claim_month)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_providers_npi ON providers(npi)")
    
    conn.commit()
    logger.info("✅ NY tables created")
    
    # Extract and load CSV with NY focus
    logger.info(f"📂 Loading NY Medicaid data from {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        with zf.open('medicaid-provider-spending.csv') as f:
            # Skip header
            f.readline()
            
            total_rows = 0
            batch_size = 50  # Smaller batches for stability
            batch = []
            provider_stats = {}  # Track provider totals
            
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
                    
                    batch.append((
                        billing_npi, servicing_npi, hcpcs_code,
                        claim_month, beneficiaries, claims, amount
                    ))
                    
                    # Insert batch
                    if len(batch) >= batch_size:
                        try:
                            cur.executemany("""
                                INSERT INTO claims (
                                    billing_provider_npi, servicing_provider_npi, hcpcs_code,
                                    claim_month, unique_beneficiaries, claim_count, amount
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, batch)
                            conn.commit()
                            total_rows += len(batch)
                            batch = []
                            
                            if total_rows % 1000 == 0:
                                logger.info(f"✅ Loaded {total_rows:,} NY claims...")
                        
                        except Exception as e:
                            logger.warning(f"Batch insert failed: {e}")
                            conn.rollback()
                            # Try individual inserts
                            for row in batch:
                                try:
                                    cur.execute("""
                                        INSERT INTO claims (
                                            billing_provider_npi, servicing_provider_npi, hcpcs_code,
                                            claim_month, unique_beneficiaries, claim_count, amount
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                                    """, row)
                                    conn.commit()
                                    total_rows += 1
                                except Exception as e2:
                                    logger.warning(f"Individual insert failed: {e2}")
                                    conn.rollback()
                            batch = []
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Skipping line {line_num + 2}: {e}")
                    continue
            
            # Insert remaining batch
            if batch:
                try:
                    cur.executemany("""
                        INSERT INTO claims (
                            billing_provider_npi, servicing_provider_npi, hcpcs_code,
                            claim_month, unique_beneficiaries, claim_count, amount
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, batch)
                    conn.commit()
                    total_rows += len(batch)
                except Exception as e:
                    logger.warning(f"Final batch insert failed: {e}")
    
    logger.info(f"🎉 Loaded {total_rows:,} NY claims")
    
    # Now create provider records with statistics
    logger.info("📊 Creating NY provider records...")
    provider_batch = []
    for npi, stats in provider_stats.items():
        provider_batch.append((
            npi,
            f'NY Provider {npi}',
            'NEW YORK',  # Default to NYC since this appears to be NY data
            'MEDICAID',
            stats['beneficiaries'],
            stats['claims'],
            stats['amount']
        ))
        
        if len(provider_batch) >= 100:
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
    
    # Update provider_id in claims table
    logger.info("🔗 Linking claims to providers...")
    cur.execute("""
        UPDATE claims 
        SET provider_id = providers.id 
        FROM providers 
        WHERE claims.billing_provider_npi = providers.npi
    """)
    conn.commit()
    
    # Verify data
    cur.execute("SELECT COUNT(*) FROM claims")
    claims = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM providers")
    providers = cur.fetchone()[0]
    
    # Get NY-specific stats
    cur.execute("""
        SELECT COUNT(*) as ny_providers,
               SUM(total_beneficiaries) as total_beneficiaries,
               SUM(total_claims) as total_claims,
               SUM(total_amount) as total_amount
        FROM providers
    """)
    ny_stats = cur.fetchone()
    
    logger.info(f"📊 NY Medicaid Data Summary:")
    logger.info(f"   - Providers: {providers:,}")
    logger.info(f"   - Claims: {claims:,}")
    logger.info(f"   - Total Beneficiaries: {ny_stats[1]:,}")
    logger.info(f"   - Total Claims: {ny_stats[2]:,}")
    logger.info(f"   - Total Amount: ${ny_stats[3]:,.2f}")
    
    cur.close()
    conn.close()
    
    logger.info("🎉 NY Medicaid data loading completed!")

if __name__ == "__main__":
    main()
