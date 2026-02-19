#!/usr/bin/env python3
"""
Simple data loading endpoint added to main.py
"""

import os
import zipfile
import csv
import psycopg2
from pathlib import Path
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

class LoadRequest(BaseModel):
    zip_path: str = "/tmp/medicaid_claims.zip"
    max_rows: Optional[int] = None

class LoadResponse(BaseModel):
    status: str
    message: str
    claims_loaded: int = 0
    providers_created: int = 0

def create_simple_load_router():
    """Create a simple router for data loading."""
    router = APIRouter()
    
    @router.post("/load-data", response_model=LoadResponse)
    async def load_medicaid_data(request: LoadRequest):
        """Load Medicaid data from ZIP file without authentication."""
        
        try:
            # Get database URL
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                return LoadResponse(
                    status="error",
                    message="DATABASE_URL not set"
                )
            
            # Check if ZIP exists
            zip_path = Path(request.zip_path)
            if not zip_path.exists():
                return LoadResponse(
                    status="error", 
                    message=f"ZIP file not found: {request.zip_path}"
                )
            
            # Connect to database
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            # Create tables if they don't exist
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
            
            # Extract and load CSV
            with zipfile.ZipFile(zip_path, 'r') as zf:
                with zf.open('medicaid-provider-spending.csv') as f:
                    # Skip header
                    f.readline()
                    
                    total_rows = 0
                    batch_size = 1000
                    batch = []
                    
                    for line_num, line in enumerate(f):
                        if request.max_rows and total_rows >= request.max_rows:
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
            
            # Get final counts
            cur.execute("SELECT COUNT(*) FROM claims")
            claims_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM providers")
            providers_count = cur.fetchone()[0]
            
            cur.close()
            conn.close()
            
            return LoadResponse(
                status="success",
                message=f"Loaded {total_rows:,} claims successfully",
                claims_loaded=claims_count,
                providers_created=providers_count
            )
            
        except Exception as e:
            logger.error(f"Data loading failed: {e}")
            return LoadResponse(
                status="error",
                message=str(e)
            )
    
    return router
