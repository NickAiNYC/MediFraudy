"""
Safe migration that handles mixed NPI data types
"""

import asyncio
import logging
from sqlalchemy import text
from database_v2 import async_engine, AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def safe_migration():
    """Safe migration that preserves existing data"""
    
    logger.info("🔄 Starting SAFE schema migration to v2...")
    
    async with async_engine.begin() as conn:
        # 1. Add modern columns first (safer)
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
            ADD COLUMN IF NOT EXISTS hcpcs_code VARCHAR(20),
            ADD COLUMN IF NOT EXISTS claim_month VARCHAR(20),
            ADD COLUMN IF NOT EXISTS unique_beneficiaries INTEGER,
            ADD COLUMN IF NOT EXISTS claim_count INTEGER
        """))
        
        # 2. Create performance indexes
        logger.info("📈 Creating performance indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_providers_npi_text ON providers(npi)",
            "CREATE INDEX IF NOT EXISTS idx_claims_billing_npi_text ON claims(billing_provider_npi)",
            "CREATE INDEX IF NOT EXISTS idx_claims_hcpcs ON claims(hcpcs_code)",
            "CREATE INDEX IF NOT EXISTS idx_claims_claim_month ON claims(claim_month)",
            "CREATE INDEX IF NOT EXISTS idx_providers_total_amount ON providers(total_amount DESC)",
            "CREATE INDEX IF NOT EXISTS idx_claims_amount_desc ON claims(amount DESC)"
        ]
        
        for index_sql in indexes:
            await conn.execute(text(index_sql))
        
        # 3. Populate modern columns safely
        logger.info("🔄 Populating modern columns...")
        
        # Update provider totals
        await conn.execute(text("""
            UPDATE providers p SET
                total_beneficiaries = COALESCE((
                    SELECT SUM(c.unique_beneficiaries) 
                    FROM claims c 
                    WHERE c.billing_provider_npi = p.npi
                ), 0),
                total_claims = COALESCE((
                    SELECT COUNT(*) 
                    FROM claims c 
                    WHERE c.billing_provider_npi = p.npi
                ), 0),
                total_amount = COALESCE((
                    SELECT SUM(c.amount) 
                    FROM claims c 
                    WHERE c.billing_provider_npi = p.npi
                ), 0)
            WHERE npi IS NOT NULL
        """))
        
        # Update claims with derived data
        await conn.execute(text("""
            UPDATE claims SET
                hcpcs_code = billing_code,
                claim_month = TO_CHAR(claim_date, 'YYYY-MM')
            WHERE billing_provider_npi IS NOT NULL
            AND hcpcs_code IS NULL
        """))
        
        logger.info("✅ Safe migration completed!")

async def validate_safe_migration():
    """Validate that safe migration was successful"""
    
    logger.info("🔍 Validating safe migration...")
    
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
        
        logger.info(f"📊 Safe Migration Results:")
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
        
        # Check modern columns
        result = await session.execute(text("""
            SELECT COUNT(*) FROM providers WHERE total_amount > 0
        """))
        providers_with_totals = result.scalar()
        
        result = await session.execute(text("""
            SELECT COUNT(*) FROM claims WHERE hcpcs_code IS NOT NULL
        """))
        claims_with_hcpcs = result.scalar()
        
        logger.info(f"✅ Modern columns populated:")
        logger.info(f"  Providers with totals: {providers_with_totals:,}")
        logger.info(f"  Claims with HCPCS: {claims_with_hcpcs:,}")
        
        logger.info("✅ Safe migration validation completed!")

async def main():
    """Main safe migration workflow"""
    
    try:
        # 1. Safe migration
        await safe_migration()
        
        # 2. Validate migration
        await validate_safe_migration()
        
        logger.info("🎉 SAFE migration to v2 completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Safe migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
