"""Fix database schema to match SQLAlchemy models.

This script adds missing columns and foreign keys to align the database
with the current models.py definitions.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text, inspect
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_claims_table(engine):
    """Add provider_id column to claims table if it doesn't exist."""
    
    inspector = inspect(engine)
    
    # Check if claims table exists
    if 'claims' not in inspector.get_table_names():
        logger.info("Claims table doesn't exist yet - will be created by models")
        return
    
    # Check existing columns
    columns = {col['name'] for col in inspector.get_columns('claims')}
    logger.info(f"Existing claims columns: {columns}")
    
    with engine.connect() as conn:
        # Add provider_id if it doesn't exist
        if 'provider_id' not in columns:
            logger.info("Adding provider_id column to claims table...")
            
            # Add the column (nullable first)
            conn.execute(text("""
                ALTER TABLE claims 
                ADD COLUMN IF NOT EXISTS provider_id INTEGER;
            """))
            conn.commit()
            logger.info("✅ Added provider_id column")
            
            # Check if we have NPI-based columns to migrate from
            if 'billing_provider_npi' in columns or 'billing_provider_npi_num' in columns:
                npi_col = 'billing_provider_npi' if 'billing_provider_npi' in columns else 'billing_provider_npi_num'
                
                logger.info(f"Populating provider_id from {npi_col}...")
                
                # Update provider_id based on NPI mapping
                result = conn.execute(text(f"""
                    UPDATE claims 
                    SET provider_id = providers.id
                    FROM providers
                    WHERE claims.{npi_col} = providers.npi
                    AND claims.provider_id IS NULL;
                """))
                conn.commit()
                
                updated = result.rowcount
                logger.info(f"✅ Updated {updated:,} claims with provider_id")
                
                # Check for unmapped claims
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM claims WHERE provider_id IS NULL;
                """))
                unmapped = result.scalar()
                
                if unmapped > 0:
                    logger.warning(f"⚠️  {unmapped:,} claims have no matching provider (will be excluded from queries)")
            
            # Add foreign key constraint
            logger.info("Adding foreign key constraint...")
            conn.execute(text("""
                ALTER TABLE claims
                ADD CONSTRAINT fk_claims_provider
                FOREIGN KEY (provider_id) REFERENCES providers(id)
                ON DELETE CASCADE;
            """))
            conn.commit()
            logger.info("✅ Added foreign key constraint")
            
            # Create index for performance
            logger.info("Creating index on provider_id...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claims_provider_id 
                ON claims(provider_id);
            """))
            conn.commit()
            logger.info("✅ Created index")
            
        else:
            logger.info("✅ provider_id column already exists")

def verify_schema(engine):
    """Verify the schema is correct."""
    
    with engine.connect() as conn:
        # Check claims table
        result = conn.execute(text("""
            SELECT COUNT(*) FROM claims WHERE provider_id IS NOT NULL;
        """))
        claims_with_provider = result.scalar()
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM claims;
        """))
        total_claims = result.scalar()
        
        logger.info(f"Claims with provider_id: {claims_with_provider:,} / {total_claims:,}")
        
        # Test a join query
        try:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM providers 
                JOIN claims ON claims.provider_id = providers.id
                LIMIT 1;
            """))
            logger.info("✅ Join query works correctly")
        except Exception as e:
            logger.error(f"❌ Join query failed: {e}")

def main():
    """Run schema fixes."""
    
    logger.info("🔧 Starting schema fix...")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'local'}")
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        fix_claims_table(engine)
        verify_schema(engine)
        logger.info("🎉 Schema fix complete!")
        
    except Exception as e:
        logger.error(f"❌ Schema fix failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
