#!/usr/bin/env python3
"""
Fix schema to match expected model columns
"""

import os
import psycopg2
from pathlib import Path
import logging

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
    
    try:
        # Add missing columns to claims table
        logger.info("📝 Adding missing columns to claims table...")
        
        # Add claim_id (we'll generate from existing data)
        cur.execute("""
            ALTER TABLE claims 
            ADD COLUMN IF NOT EXISTS claim_id VARCHAR(50)
        """)
        
        # Add beneficiary_id (use unique_beneficiaries as placeholder)
        cur.execute("""
            ALTER TABLE claims 
            ADD COLUMN IF NOT EXISTS beneficiary_id VARCHAR(50)
        """)
        
        # Add submitted_date (use current timestamp)
        cur.execute("""
            ALTER TABLE claims 
            ADD COLUMN IF NOT EXISTS submitted_date TIMESTAMP
        """)
        
        # Add service_category (use billing_code as placeholder)
        cur.execute("""
            ALTER TABLE claims 
            ADD COLUMN IF NOT EXISTS service_category VARCHAR(100)
        """)
        
        # Add units (use claim_count)
        cur.execute("""
            ALTER TABLE claims 
            ADD COLUMN IF NOT EXISTS units INTEGER DEFAULT 1
        """)
        
        # Add place_of_service (default to office)
        cur.execute("""
            ALTER TABLE claims 
            ADD COLUMN IF NOT EXISTS place_of_service VARCHAR(50) DEFAULT 'OFFICE'
        """)
        
        # Add modifiers (empty JSON array)
        cur.execute("""
            ALTER TABLE claims 
            ADD COLUMN IF NOT EXISTS modifiers JSON DEFAULT '[]'
        """)
        
        conn.commit()
        logger.info("✅ Added missing columns")
        
        # Update the new columns with data
        logger.info("🔄 Updating columns with data...")
        
        # Generate claim_id from existing data
        cur.execute("""
            UPDATE claims 
            SET claim_id = 'CLAIM_' || id::TEXT 
            WHERE claim_id IS NULL
        """)
        
        # Set beneficiary_id from unique_beneficiaries
        cur.execute("""
            UPDATE claims 
            SET beneficiary_id = 'BEN_' || unique_beneficiaries::TEXT 
            WHERE beneficiary_id IS NULL AND unique_beneficiaries IS NOT NULL
        """)
        
        # Set submitted_date to current timestamp
        cur.execute("""
            UPDATE claims 
            SET submitted_date = NOW() 
            WHERE submitted_date IS NULL
        """)
        
        # Set service_category from billing_code
        cur.execute("""
            UPDATE claims 
            SET service_category = billing_code 
            WHERE service_category IS NULL
        """)
        
        # Set units from claim_count
        cur.execute("""
            UPDATE claims 
            SET units = claim_count 
            WHERE units = 1 AND claim_count IS NOT NULL
        """)
        
        conn.commit()
        logger.info("✅ Updated columns with data")
        
        # Verify the schema
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'claims' 
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        logger.info("📋 Claims table columns:")
        for col in columns:
            logger.info(f"   - {col[0]} ({col[1]})")
        
        # Get counts
        cur.execute("SELECT COUNT(*) FROM claims")
        claims_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM providers")
        providers_count = cur.fetchone()[0]
        
        logger.info(f"📊 Final counts:")
        logger.info(f"   - Providers: {providers_count:,}")
        logger.info(f"   - Claims: {claims_count:,}")
        
        logger.info("🎉 Schema fix completed!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
