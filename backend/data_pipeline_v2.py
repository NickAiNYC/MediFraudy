"""
Modern async data loading pipeline for 227M+ claims
"""

import asyncio
import aiofiles
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any
import logging
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor
import time

from database_v2 import async_engine, AsyncSessionLocal
from config import settings

logger = logging.getLogger(__name__)

class ModernDataLoader:
    """Production-ready data loader for massive Medicaid datasets"""
    
    def __init__(self):
        self.batch_size = settings.BATCH_SIZE
        self.max_workers = settings.MAX_WORKERS
        self.chunk_size = settings.CHUNK_SIZE
        
    async def create_optimized_schema(self):
        """Create optimized schema for massive datasets"""
        async with async_engine.begin() as conn:
            # Providers table with proper indexing
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS providers (
                    id BIGSERIAL PRIMARY KEY,
                    npi BIGINT UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    address TEXT,
                    city VARCHAR(100),
                    state CHAR(2),
                    zip_code VARCHAR(10),
                    facility_type VARCHAR(100),
                    specialty VARCHAR(100),
                    licensed_capacity INTEGER,
                    total_beneficiaries BIGINT DEFAULT 0,
                    total_claims BIGINT DEFAULT 0,
                    total_amount DECIMAL(15,2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Claims table optimized for analytics
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS claims (
                    id BIGSERIAL PRIMARY KEY,
                    provider_id BIGINT REFERENCES providers(id),
                    claim_id VARCHAR(50),
                    beneficiary_id VARCHAR(50),
                    billing_code VARCHAR(20) NOT NULL,
                    amount DECIMAL(12,2) NOT NULL,
                    claim_date DATE NOT NULL,
                    submitted_date TIMESTAMP,
                    service_category VARCHAR(100),
                    units INTEGER DEFAULT 1,
                    place_of_service VARCHAR(50),
                    modifiers JSONB DEFAULT '[]',
                    billing_provider_npi BIGINT,
                    servicing_provider_npi BIGINT,
                    hcpcs_code VARCHAR(20),
                    claim_month VARCHAR(20),
                    unique_beneficiaries INTEGER,
                    claim_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Performance indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_claims_provider_id ON claims(provider_id)",
                "CREATE INDEX IF NOT EXISTS idx_claims_billing_code ON claims(billing_code)",
                "CREATE INDEX IF NOT EXISTS idx_claims_claim_date ON claims(claim_date)",
                "CREATE INDEX IF NOT EXISTS idx_claims_amount ON claims(amount)",
                "CREATE INDEX IF NOT EXISTS idx_providers_npi ON providers(npi)",
                "CREATE INDEX IF NOT EXISTS idx_providers_state_city ON providers(state, city)",
                "CREATE INDEX IF NOT EXISTS idx_claims_billing_npi ON claims(billing_provider_npi)",
                "CREATE INDEX IF NOT EXISTS idx_claims_hcpcs ON claims(hcpcs_code)"
            ]
            
            for index_sql in indexes:
                await conn.execute(text(index_sql))
                
        logger.info("✅ Optimized schema created with performance indexes")
    
    async def load_chunk_async(self, chunk_data: List[Dict[str, Any]]) -> int:
        """Async chunk loading with proper error handling"""
        if not chunk_data:
            return 0
            
        async with AsyncSessionLocal() as session:
            try:
                # Bulk insert with proper SQL
                values = []
                for row in chunk_data:
                    values.append(f"({row['billing_npi']}, '{row['servicing_npi']}', '{row['hcpcs_code']}', '{row['claim_month']}', {row['beneficiaries']}, {row['claims']}, {row['amount']})")
                
                sql = f"""
                    INSERT INTO claims (billing_provider_npi, servicing_provider_npi, hcpcs_code, claim_month, unique_beneficiaries, claim_count, amount)
                    VALUES {','.join(values)}
                    ON CONFLICT DO NOTHING
                """
                
                await session.execute(text(sql))
                await session.commit()
                return len(chunk_data)
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Chunk insert failed: {e}")
                return 0
    
    async def process_csv_stream(self, file_path: str):
        """Stream process CSV file for memory efficiency"""
        total_processed = 0
        chunk = []
        
        async with aiofiles.open(file_path, 'r') as f:
            # Skip header
            await f.readline()
            
            async for line in f:
                try:
                    # Parse CSV line
                    parts = line.strip().split(',')
                    if len(parts) < 7:
                        continue
                        
                    chunk.append({
                        'billing_npi': parts[0].strip('"'),
                        'servicing_npi': parts[1].strip('"'),
                        'hcpcs_code': parts[2].strip('"'),
                        'claim_month': parts[3].strip('"'),
                        'beneficiaries': int(parts[4]),
                        'claims': int(parts[5]),
                        'amount': float(parts[6])
                    })
                    
                    # Process chunk when full
                    if len(chunk) >= self.batch_size:
                        loaded = await self.load_chunk_async(chunk)
                        total_processed += loaded
                        chunk = []
                        
                        if total_processed % 10000 == 0:
                            logger.info(f"✅ Processed {total_processed:,} claims")
                            
                except (ValueError, IndexError) as e:
                    logger.warning(f"Skipping malformed line: {e}")
                    continue
            
            # Process final chunk
            if chunk:
                loaded = await self.load_chunk_async(chunk)
                total_processed += loaded
        
        return total_processed
    
    async def create_providers_from_claims(self):
        """Create provider records from loaded claims"""
        async with AsyncSessionLocal() as session:
            # Create providers from unique NPIs
            await session.execute(text("""
                INSERT INTO providers (npi, name, city, state, specialty, total_beneficiaries, total_claims, total_amount)
                SELECT 
                    billing_provider_npi,
                    'Provider ' || billing_provider_npi,
                    'NEW YORK',
                    'NY',
                    'MEDICAID',
                    SUM(unique_beneficiaries),
                    SUM(claim_count),
                    SUM(amount)
                FROM claims 
                WHERE billing_provider_npi IS NOT NULL
                GROUP BY billing_provider_npi
                ON CONFLICT (npi) DO UPDATE SET
                    total_beneficiaries = EXCLUDED.total_beneficiaries,
                    total_claims = EXCLUDED.total_claims,
                    total_amount = EXCLUDED.total_amount,
                    updated_at = CURRENT_TIMESTAMP
            """))
            
            await session.commit()
            
            # Link claims to providers
            await session.execute(text("""
                UPDATE claims 
                SET provider_id = providers.id 
                FROM providers 
                WHERE claims.billing_provider_npi = providers.npi
                AND claims.provider_id IS NULL
            """))
            
            await session.commit()
            
        logger.info("✅ Provider records created and linked")
    
    async def load_dataset(self, zip_path: str, sample_size: int = None):
        """Main loading method with progress tracking"""
        start_time = time.time()
        
        logger.info(f"🚀 Starting modern data load from {zip_path}")
        
        # Create optimized schema
        await self.create_optimized_schema()
        
        # Extract and process CSV
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zf:
            csv_path = 'medicaid-provider-spending.csv'
            
            # Extract to temp file for streaming
            zf.extract(csv_path, '/tmp/')
            
            # Process with streaming
            total_claims = await self.process_csv_stream('/tmp/' + csv_path)
            
            # Create providers
            await self.create_providers_from_claims()
            
            # Cleanup
            os.remove('/tmp/' + csv_path)
        
        # Final statistics
        elapsed = time.time() - start_time
        rate = total_claims / elapsed if elapsed > 0 else 0
        
        logger.info(f"🎉 Load completed!")
        logger.info(f"📊 Claims loaded: {total_claims:,}")
        logger.info(f"⚡ Rate: {rate:,.0f} claims/second")
        logger.info(f"⏱️  Time: {elapsed:.1f} seconds")
        
        return total_claims

# Singleton instance
modern_loader = ModernDataLoader()
