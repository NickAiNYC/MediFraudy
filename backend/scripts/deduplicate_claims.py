import os
import sys
import logging
from sqlalchemy import create_engine, text

# Add parent directory to path to import database module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def deduplicate_claims():
    """
    Remove duplicate claims caused by overlapping data ingestion processes.
    Keeps the row with the lowest ID (first inserted).
    """
    try:
        logger.info("Starting deduplication process...")
        logger.info("Identifying duplicates based on (claim_id, beneficiary_id, provider_id, claim_date)...")
        
        # This query deletes duplicates while keeping the one with the minimum ID
        # utilizing the CTID (Postgres physical location) or just a standard DELETE with USING
        
        # Method: DELETE using self-join
        # This is safe and standard for Postgres
        dedup_query = text("""
            DELETE FROM claims c1
            USING claims c2
            WHERE c1.id > c2.id
            AND c1.claim_id = c2.claim_id
            AND c1.beneficiary_id = c2.beneficiary_id
            AND c1.provider_id = c2.provider_id
            AND c1.claim_date = c2.claim_date;
        """)
        
        with engine.begin() as connection:
            logger.info("Executing delete query. This may take a while for large tables...")
            result = connection.execute(dedup_query)
            logger.info(f"Deduplication complete. Removed {result.rowcount} duplicate rows.")
            
    except Exception as e:
        logger.error(f"Error during deduplication: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    deduplicate_claims()
