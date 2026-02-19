#!/usr/bin/env python3
"""
Proper Medicaid data loader that matches the expected schema
"""

import os
import zipfile
import csv
import psycopg2
from pathlib import Path
import logging
import argparse
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip-path', default='medicaid-provider-spending.csv.zip')
    parser.add_argument('--max-rows', type=int, help='Limit rows for testing')
    args = parser.parse_args()
    
    # Get database URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("❌ DATABASE_URL not set")
        return
    
    logger.info(f"🔌 Connecting to database...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Check if ZIP exists
    zip_path = Path(args.zip_path)
    if not zip_path.exists():
        logger.error(f"❌ ZIP file not found: {zip_path}")
        return
    
    file_size_gb = zip_path.stat().st_size / (1024**3)
    logger.info(f"📦 ZIP file: {zip_path} ({file_size_gb:.2f} GB)")
    
    # Create tables with proper schema
    logger.info("📦 Creating tables with proper schema...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS providers (
            id SERIAL PRIMARY KEY,
            npi VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            address VARCHAR(500),
            city VARCHAR(100),
            state VARCHAR(2),
            zip_code VARCHAR(10),
            facility_type VARCHAR(100),
            specialty VARCHAR(100),
            licensed_capacity INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id SERIAL PRIMARY KEY,
            provider_id INTEGER REFERENCES providers(id) NOT NULL,
            claim_id VARCHAR(50),
            beneficiary_id VARCHAR(50),
            billing_code VARCHAR(20) NOT NULL,
            amount DECIMAL(12,2) NOT NULL,
            claim_date DATE NOT NULL,
            submitted_date TIMESTAMP,
            service_category VARCHAR(100),
            units INTEGER DEFAULT 1,
            place_of_service VARCHAR(50) DEFAULT 'OFFICE',
            modifiers TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_claims_provider_id ON claims(provider_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_claims_billing_code ON claims(billing_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_claims_claim_date ON claims(claim_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_providers_npi ON providers(npi)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_providers_location ON providers(state, city)")
    
    conn.commit()
    logger.info("✅ Tables created with proper schema")
    
    # Extract and load CSV
    logger.info(f"📂 Extracting and loading from {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        with zf.open('medicaid-provider-spending.csv') as f:
            # Skip header
            f.readline()
            
            total_rows = 0
            batch_size = 100
            batch = []
            
            for line_num, line in enumerate(f):
                if args.max_rows and total_rows >= args.max_rows:
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
                        ON CONFLICT (npi) DO UPDATE SET
                            name = EXCLUDED.name,
                            city = EXCLUDED.city,
                            state = EXCLUDED.state,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (billing_npi, f'Provider {billing_npi}', 'NEW YORK', 'NY'))
                    
                    result = cur.fetchone()
                    if not result:
                        continue
                    
                    provider_id = result[0]
                    
                    # Parse claim month (format: 2024-07)
                    year, month = claim_month.split('-')
                    claim_date = f"{year}-{month}-01"
                    
                    # Create claim record
                    batch.append((
                        provider_id,  # provider_id
                        f'CLAIM_{total_rows + 1}',  # claim_id
                        f'BEN_{beneficiaries}',  # beneficiary_id
                        hcpcs_code,  # billing_code
                        amount,  # amount
                        claim_date,  # claim_date
                        datetime.now(),  # submitted_date
                        hcpcs_code,  # service_category
                        claims,  # units
                        'OFFICE',  # place_of_service
                        '[]'  # modifiers (JSON)
                    ))
                    
                    # Insert batch
                    if len(batch) >= batch_size:
                        # Debug: check data lengths
                        for i, row in enumerate(batch[:5]):  # Check first 5 rows
                            logger.info(f"Debug row {i}: {row}")
                        cur.executemany("""
                            INSERT INTO claims (
                                provider_id, claim_id, beneficiary_id, billing_code,
                                amount, claim_date, submitted_date, service_category,
                                units, place_of_service, modifiers
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, batch)
                        conn.commit()
                        total_rows += len(batch)
                        batch = []
                        
                        if total_rows % 10000 == 0:
                            logger.info(f"✅ Loaded {total_rows:,} rows...")
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Skipping line {line_num + 2}: {e}")
                    continue
            
            # Insert remaining batch
            if batch:
                cur.executemany("""
                    INSERT INTO claims (
                        provider_id, claim_id, beneficiary_id, billing_code,
                        amount, claim_date, submitted_date, service_category,
                        units, place_of_service, modifiers
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, batch)
                conn.commit()
                total_rows += len(batch)
    
    logger.info(f"🎉 SUCCESS! Loaded {total_rows:,} claims")
    
    # Verify data
    cur.execute("SELECT COUNT(*) FROM claims")
    claims = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM providers")
    providers = cur.fetchone()[0]
    
    logger.info(f"📊 Final counts:")
    logger.info(f"   - Providers: {providers:,}")
    logger.info(f"   - Claims: {claims:,}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
