"""
Railway-optimized data loader for 77M Medicaid claims.

Designed for Railway's constraints:
- 512MB RAM limit (free tier) / 8GB (pro)
- Ephemeral filesystem (need volumes)
- 10-minute request timeout
- Shared CPU

Strategy:
1. Stream from ZIP without full extraction
2. Process in 10k row chunks (max 50MB RAM per chunk)
3. Use Celery for async background loading
4. Track progress in Redis
5. Resume from last checkpoint on crash
"""

import os
import zipfile
import logging
import time
from typing import Generator, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from tqdm import tqdm

from database import SessionLocal, engine
from models import Provider, Claim
from config import settings

logger = logging.getLogger(__name__)


class RailwayDataLoader:
    """Memory-efficient data loader optimized for Railway deployment."""
    
    # Railway-specific limits
    MAX_CHUNK_SIZE = 10000  # 10k rows = ~30-50MB RAM
    BATCH_COMMIT_SIZE = 5000  # Commit every 5k rows
    CHECKPOINT_INTERVAL = 50000  # Save progress every 50k rows
    
    def __init__(
        self,
        zip_path: str,
        redis_client=None,
        progress_key: str = "data_load_progress"
    ):
        """
        Initialize Railway data loader.
        
        Args:
            zip_path: Path to the 3.6GB ZIP file
            redis_client: Redis client for progress tracking
            progress_key: Redis key for storing progress
        """
        self.zip_path = Path(zip_path)
        self.redis_client = redis_client
        self.progress_key = progress_key
        
        if not self.zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")
        
        # Get file info
        self.file_size = self.zip_path.stat().st_size
        logger.info(f"ZIP file size: {self.file_size / (1024**3):.2f} GB")
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current loading progress from Redis."""
        if not self.redis_client:
            return {"rows_loaded": 0, "last_checkpoint": 0, "status": "not_started"}
        
        try:
            import json
            progress_json = self.redis_client.get(self.progress_key)
            if progress_json:
                return json.loads(progress_json)
        except Exception as e:
            logger.warning(f"Failed to get progress from Redis: {e}")
        
        return {"rows_loaded": 0, "last_checkpoint": 0, "status": "not_started"}
    
    def save_progress(self, rows_loaded: int, status: str = "loading"):
        """Save loading progress to Redis."""
        if not self.redis_client:
            return
        
        try:
            import json
            progress = {
                "rows_loaded": rows_loaded,
                "last_checkpoint": rows_loaded,
                "status": status,
                "updated_at": datetime.utcnow().isoformat(),
                "file_size_gb": round(self.file_size / (1024**3), 2)
            }
            self.redis_client.setex(
                self.progress_key,
                86400,  # 24 hour expiry
                json.dumps(progress)
            )
        except Exception as e:
            logger.warning(f"Failed to save progress to Redis: {e}")
    
    def stream_csv_from_zip(
        self,
        chunk_size: int = MAX_CHUNK_SIZE,
        skip_rows: int = 0
    ) -> Generator[pd.DataFrame, None, None]:
        """
        Stream CSV from ZIP without extracting to disk.
        
        This is the KEY optimization - we never load the full file into memory.
        
        Args:
            chunk_size: Rows per chunk (default 10k for Railway)
            skip_rows: Skip first N rows (for resume capability)
            
        Yields:
            DataFrame chunks
        """
        logger.info(f"Streaming from ZIP: {self.zip_path}")
        
        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            # Find CSV file in ZIP
            csv_files = [f for f in zf.namelist() 
                        if f.endswith('.csv') and not f.startswith('__MACOSX')]
            
            if not csv_files:
                raise ValueError(f"No CSV files found in {self.zip_path}")
            
            csv_file = csv_files[0]
            logger.info(f"Found CSV: {csv_file}")
            
            # Get uncompressed size
            csv_info = zf.getinfo(csv_file)
            uncompressed_size = csv_info.file_size
            logger.info(f"Uncompressed CSV size: {uncompressed_size / (1024**3):.2f} GB")
            
            # Stream CSV from ZIP
            with zf.open(csv_file) as f:
                # Use pandas chunked reading
                reader = pd.read_csv(
                    f,
                    chunksize=chunk_size,
                    low_memory=False,
                    dtype={
                        'npi': str,
                        'provider_npi': str,
                        'billing_provider_npi_num': str,
                    },
                    on_bad_lines='skip'  # Skip malformed rows
                )
                
                chunk_num = 0
                rows_skipped = 0
                
                for chunk in reader:
                    chunk_num += 1
                    
                    # Skip chunks if resuming
                    if skip_rows > 0 and rows_skipped < skip_rows:
                        rows_skipped += len(chunk)
                        if rows_skipped >= skip_rows:
                            # Partial chunk after skip
                            remaining = rows_skipped - skip_rows
                            if remaining > 0:
                                yield chunk.tail(remaining)
                        continue
                    
                    yield chunk
                    
                    # Memory management: Force garbage collection every 10 chunks
                    if chunk_num % 10 == 0:
                        import gc
                        gc.collect()
    
    def process_chunk(
        self,
        df: pd.DataFrame,
        session,
        state_filter: Optional[str] = "NY"
    ) -> int:
        """
        Process a single chunk with minimal memory footprint.
        
        Args:
            df: DataFrame chunk
            session: Database session
            state_filter: Filter to specific state (default NY)
            
        Returns:
            Number of claims inserted
        """
        if df.empty:
            return 0
        
        # Clean and standardize column names
        df.columns = df.columns.str.lower().str.strip()
        
        # Map common column variations to standard names
        column_mapping = {
            'billing_provider_npi_num': 'npi',
            'provider_npi': 'npi',
            'rndrng_prvdr_npi': 'npi',
            'provider_last_name_org': 'name',
            'rndrng_prvdr_last_org_name': 'name',
            'provider_street1': 'address',
            'rndrng_prvdr_st1': 'address',
            'provider_city': 'city',
            'rndrng_prvdr_city': 'city',
            'provider_state': 'state',
            'rndrng_prvdr_state_abrvtn': 'state',
            'provider_zip': 'zip_code',
            'rndrng_prvdr_zip5': 'zip_code',
            'hcpcs_code': 'billing_code',
            'tot_srvcs': 'units',
            'tot_benes': 'beneficiary_count',
            'avg_sbmtd_chrg': 'amount',
            'avg_mdcr_pymt_amt': 'amount',
        }
        
        df = df.rename(columns=column_mapping)
        
        # Filter by state if specified
        if state_filter and 'state' in df.columns:
            df = df[df['state'] == state_filter]
            if df.empty:
                return 0
        
        # Ensure NPI exists
        if 'npi' not in df.columns:
            logger.warning("No NPI column found, skipping chunk")
            return 0
        
        # Clean NPI: remove non-digits, pad to 10 digits
        df['npi'] = df['npi'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(10)
        df = df[df['npi'].str.len() == 10]  # Valid NPIs only
        
        if df.empty:
            return 0
        
        # Extract and upsert providers
        provider_cols = ['npi', 'name', 'address', 'city', 'state', 'zip_code']
        existing_cols = [col for col in provider_cols if col in df.columns]
        
        if 'npi' in existing_cols:
            providers_df = df[existing_cols].drop_duplicates(subset=['npi'])
            
            # Fill missing columns
            for col in provider_cols:
                if col not in providers_df.columns:
                    providers_df[col] = None
            
            # Upsert providers
            npi_to_id = self._upsert_providers(session, providers_df)
            
            # Map provider IDs to claims
            df['provider_id'] = df['npi'].map(npi_to_id)
            df = df.dropna(subset=['provider_id'])
            
            # Insert claims
            claims_inserted = self._insert_claims(session, df)
            
            return claims_inserted
        
        return 0
    
    def _upsert_providers(self, session, providers_df: pd.DataFrame) -> Dict[str, int]:
        """Upsert providers and return NPI -> ID mapping."""
        if providers_df.empty:
            return {}
        
        # Prepare records
        records = providers_df.to_dict(orient='records')
        
        # Bulk upsert using PostgreSQL INSERT ... ON CONFLICT
        stmt = insert(Provider).values(records)
        stmt = stmt.on_conflict_do_nothing(index_elements=['npi'])
        
        session.execute(stmt)
        session.commit()
        
        # Fetch IDs for this batch
        npis = providers_df['npi'].tolist()
        rows = session.query(Provider.id, Provider.npi).filter(
            Provider.npi.in_(npis)
        ).all()
        
        return {row.npi: row.id for row in rows}
    
    def _insert_claims(self, session, df: pd.DataFrame) -> int:
        """Insert claims with minimal memory usage."""
        # Prepare claim columns
        claim_cols = {
            'provider_id': 'provider_id',
            'billing_code': 'billing_code',
            'amount': 'amount',
            'units': 'units',
            'beneficiary_count': 'beneficiary_id',  # Reuse field
        }
        
        # Filter to available columns
        available_cols = {k: v for k, v in claim_cols.items() if k in df.columns}
        
        if 'provider_id' not in available_cols:
            return 0
        
        claims_df = df[list(available_cols.keys())].copy()
        claims_df = claims_df.rename(columns=available_cols)
        
        # Convert amount to numeric
        if 'amount' in claims_df.columns:
            claims_df['amount'] = pd.to_numeric(claims_df['amount'], errors='coerce')
        
        # Bulk insert
        records = claims_df.to_dict(orient='records')
        
        if records:
            session.bulk_insert_mappings(Claim, records)
            session.commit()
        
        return len(records)
    
    def load_data(
        self,
        state_filter: str = "NY",
        resume: bool = True,
        max_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Load data with Railway optimizations.
        
        Args:
            state_filter: Filter to specific state
            resume: Resume from last checkpoint
            max_rows: Limit total rows (for testing)
            
        Returns:
            Loading statistics
        """
        start_time = time.time()
        
        # Get resume point
        skip_rows = 0
        if resume:
            progress = self.get_progress()
            skip_rows = progress.get('last_checkpoint', 0)
            if skip_rows > 0:
                logger.info(f"Resuming from row {skip_rows:,}")
        
        session = SessionLocal()
        total_claims = 0
        total_providers = 0
        chunks_processed = 0
        
        try:
            self.save_progress(skip_rows, "loading")
            
            # Stream and process chunks
            for chunk in self.stream_csv_from_zip(
                chunk_size=self.MAX_CHUNK_SIZE,
                skip_rows=skip_rows
            ):
                try:
                    claims_inserted = self.process_chunk(chunk, session, state_filter)
                    total_claims += claims_inserted
                    chunks_processed += 1
                    
                    # Save checkpoint
                    if chunks_processed % (self.CHECKPOINT_INTERVAL // self.MAX_CHUNK_SIZE) == 0:
                        rows_processed = skip_rows + (chunks_processed * self.MAX_CHUNK_SIZE)
                        self.save_progress(rows_processed, "loading")
                        logger.info(f"Checkpoint: {rows_processed:,} rows processed, {total_claims:,} claims inserted")
                    
                    # Check max rows limit
                    if max_rows and total_claims >= max_rows:
                        logger.info(f"Reached max rows limit: {max_rows:,}")
                        break
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {chunks_processed}: {e}")
                    session.rollback()
                    continue
            
            # Get final counts
            total_providers = session.query(Provider).count()
            
            # Mark complete
            self.save_progress(
                skip_rows + (chunks_processed * self.MAX_CHUNK_SIZE),
                "completed"
            )
            
            elapsed = time.time() - start_time
            
            stats = {
                "status": "completed",
                "total_claims": total_claims,
                "total_providers": total_providers,
                "chunks_processed": chunks_processed,
                "elapsed_seconds": round(elapsed, 2),
                "rows_per_second": round(total_claims / elapsed, 2) if elapsed > 0 else 0
            }
            
            logger.info(f"Load complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Fatal error during load: {e}", exc_info=True)
            self.save_progress(
                skip_rows + (chunks_processed * self.MAX_CHUNK_SIZE),
                "failed"
            )
            raise
        finally:
            session.close()


def estimate_load_time(file_size_gb: float, chunk_size: int = 10000) -> Dict[str, Any]:
    """
    Estimate loading time for Railway deployment.
    
    Args:
        file_size_gb: Size of uncompressed CSV in GB
        chunk_size: Rows per chunk
        
    Returns:
        Time estimates
    """
    # Assumptions based on Railway shared CPU
    rows_per_gb = 5_000_000  # ~5M rows per GB for typical Medicaid data
    rows_per_second = 500  # Conservative estimate on Railway
    
    total_rows = file_size_gb * rows_per_gb
    total_seconds = total_rows / rows_per_second
    
    return {
        "estimated_rows": int(total_rows),
        "estimated_seconds": int(total_seconds),
        "estimated_hours": round(total_seconds / 3600, 2),
        "chunks": int(total_rows / chunk_size),
        "recommendation": "Run as background Celery task with resume capability"
    }
