"""
Migration script from legacy to modern architecture
"""

import asyncio
import logging
from sqlalchemy import text
from database_v2 import async_engine, AsyncSessionLocal
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_schema():
    """Migrate database schema to modern structure"""
    
    logger.info("🔄 Starting schema migration to v2...")
    
    async with async_engine.begin() as conn:
        # 1. Convert NPI columns to BIGINT for performance
        logger.info("📊 Converting NPI columns to BIGINT...")
        await conn.execute(text("""
            ALTER TABLE providers 
            ALTER COLUMN npi TYPE BIGINT USING npi::BIGINT
        """))
        
        await conn.execute(text("""
            ALTER TABLE claims 
            ALTER COLUMN billing_provider_npi TYPE BIGINT USING billing_provider_npi::BIGINT
        """))
        
        await conn.execute(text("""
            ALTER TABLE claims 
            ALTER COLUMN servicing_provider_npi TYPE BIGINT USING servicing_provider_npi::BIGINT
        """))
        
        # 2. Add missing modern columns
        logger.info("🔧 Adding modern columns...")
        
        # Provider enhancements
        await conn.execute(text("""
            ALTER TABLE providers 
            ADD COLUMN IF NOT EXISTS total_beneficiaries BIGINT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS total_claims BIGINT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS total_amount DECIMAL(15,2) DEFAULT 0.00
        """))
        
        # Claims enhancements
        await conn.execute(text("""
            ALTER TABLE claims 
            ADD COLUMN IF NOT EXISTS modifiers JSONB DEFAULT '[]',
            ADD COLUMN IF NOT EXISTS billing_provider_npi BIGINT,
            ADD COLUMN IF NOT EXISTS servicing_provider_npi BIGINT,
            ADD COLUMN IF NOT EXISTS hcpcs_code VARCHAR(20),
            ADD COLUMN IF NOT EXISTS claim_month VARCHAR(20),
            ADD COLUMN IF NOT EXISTS unique_beneficiaries INTEGER,
            ADD COLUMN IF NOT EXISTS claim_count INTEGER
        """))
        
        # 3. Create performance indexes
        logger.info("📈 Creating performance indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_providers_npi_bigint ON providers(npi)",
            "CREATE INDEX IF NOT EXISTS idx_claims_billing_npi_bigint ON claims(billing_provider_npi)",
            "CREATE INDEX IF NOT EXISTS idx_claims_hcpcs ON claims(hcpcs_code)",
            "CREATE INDEX IF NOT EXISTS idx_claims_claim_month ON claims(claim_month)",
            "CREATE INDEX IF NOT EXISTS idx_providers_total_amount ON providers(total_amount DESC)",
            "CREATE INDEX IF NOT EXISTS idx_claims_amount_desc ON claims(amount DESC)",
            "CREATE INDEX IF NOT EXISTS idx_claims_modifiers ON claims USING GIN(modifiers)"
        ]
        
        for index_sql in indexes:
            await conn.execute(text(index_sql))
        
        # 4. Populate modern columns with existing data
        logger.info("🔄 Populating modern columns...")
        
        # Update provider totals
        await conn.execute(text("""
            UPDATE providers p SET
                total_beneficiaries = COALESCE((
                    SELECT SUM(c.unique_beneficiaries) 
                    FROM claims c 
                    WHERE c.billing_provider_npi::TEXT = p.npi
                ), 0),
                total_claims = COALESCE((
                    SELECT COUNT(*) 
                    FROM claims c 
                    WHERE c.billing_provider_npi::TEXT = p.npi
                ), 0),
                total_amount = COALESCE((
                    SELECT SUM(c.amount) 
                    FROM claims c 
                    WHERE c.billing_provider_npi::TEXT = p.npi
                ), 0)
        """))
        
        # Update claims with derived data
        await conn.execute(text("""
            UPDATE claims SET
                billing_provider_npi = billing_provider_npi::BIGINT,
                servicing_provider_npi = servicing_provider_npi::BIGINT,
                hcpcs_code = billing_code,
                claim_month = TO_CHAR(claim_date, 'YYYY-MM')
            WHERE billing_provider_npi IS NOT NULL
        """))
        
        logger.info("✅ Schema migration completed!")

async def validate_migration():
    """Validate that migration was successful"""
    
    logger.info("🔍 Validating migration...")
    
    async with AsyncSessionLocal() as session:
        # Check data integrity
        result = await session.execute(text("SELECT COUNT(*) FROM providers"))
        provider_count = result.scalar()
        
        result = await session.execute(text("SELECT COUNT(*) FROM claims"))
        claim_count = result.scalar()
        
        result = await session.execute(text("""
            SELECT COUNT(*) FROM claims WHERE billing_provider_npi IS NOT NULL
        """))
        linked_claims = result.scalar()
        
        logger.info(f"📊 Migration Results:")
        logger.info(f"  Providers: {provider_count:,}")
        logger.info(f"  Claims: {claim_count:,}")
        logger.info(f"  Linked claims: {linked_claims:,}")
        
        # Check for data issues
        result = await session.execute(text("""
            SELECT COUNT(*) FROM providers WHERE npi IS NULL OR npi = ''
        """))
        invalid_providers = result.scalar()
        
        if invalid_providers > 0:
            logger.warning(f"⚠️ Found {invalid_providers} providers with invalid NPI")
        
        result = await session.execute(text("""
            SELECT COUNT(*) FROM claims WHERE amount <= 0
        """))
        zero_amount_claims = result.scalar()
        
        if zero_amount_claims > 0:
            logger.warning(f"⚠️ Found {zero_amount_claims} claims with zero/negative amount")
        
        logger.info("✅ Migration validation completed!")

async def backup_before_migration():
    """Create backup before migration"""
    
    logger.info("💾 Creating backup before migration...")
    
    async with async_engine.begin() as conn:
        # Create backup tables
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS providers_backup AS 
            SELECT * FROM providers
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS claims_backup AS 
            SELECT * FROM claims
        """))
        
        logger.info("✅ Backup created successfully!")

async def main():
    """Main migration workflow"""
    
    try:
        # 1. Create backup
        await backup_before_migration()
        
        # 2. Migrate schema
        await migrate_schema()
        
        # 3. Validate migration
        await validate_migration()
        
        logger.info("🎉 Migration to v2 completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
