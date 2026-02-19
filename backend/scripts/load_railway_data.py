#!/usr/bin/env python3
"""
Railway-optimized data loader CLI script.

Usage:
    python load_railway_data.py --zip /data/medicaid_claims.zip --state NY
    python load_railway_data.py --zip /data/medicaid_claims.zip --max-rows 100000  # Test mode
    python load_railway_data.py --resume --task-id abc-123  # Resume from checkpoint
"""

import argparse
import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.railway_data_loader import RailwayDataLoader, estimate_load_time
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Load 77M Medicaid claims on Railway with streaming and resume capability"
    )
    parser.add_argument(
        "--zip",
        default="/data/medicaid_claims.zip",
        help="Path to ZIP file on Railway volume (default: /data/medicaid_claims.zip)"
    )
    parser.add_argument(
        "--state",
        default="NY",
        help="Filter to specific state (default: NY)"
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        help="Limit total rows for testing (e.g., 100000)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint"
    )
    parser.add_argument(
        "--estimate",
        action="store_true",
        help="Estimate loading time and exit"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=10000,
        help="Rows per chunk (default: 10000 for Railway)"
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    zip_path = Path(args.zip)
    if not zip_path.exists():
        logger.error(f"❌ ZIP file not found: {args.zip}")
        logger.info("\nTo upload file to Railway:")
        logger.info("1. railway run bash")
        logger.info("2. cd /data")
        logger.info("3. wget YOUR_DOWNLOAD_URL -O medicaid_claims.zip")
        logger.info("\nOr see RAILWAY_DATA_LOADING.md for detailed instructions")
        sys.exit(1)
    
    file_size_gb = zip_path.stat().st_size / (1024**3)
    logger.info(f"📦 ZIP file: {args.zip} ({file_size_gb:.2f} GB)")
    
    # Show estimate if requested
    if args.estimate:
        logger.info("\n📊 Estimating loading time...")
        estimate = estimate_load_time(file_size_gb * 3)  # Uncompressed is ~3x
        logger.info(f"   Estimated rows: {estimate['estimated_rows']:,}")
        logger.info(f"   Estimated time: {estimate['estimated_hours']:.1f} hours")
        logger.info(f"   Total chunks: {estimate['chunks']:,}")
        logger.info(f"\n💡 {estimate['recommendation']}")
        sys.exit(0)
    
    # Connect to Redis for progress tracking
    redis_client = None
    try:
        import redis
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        logger.info("✅ Redis connected for progress tracking")
    except Exception as e:
        logger.warning(f"⚠️  Redis not available: {e}")
        logger.warning("   Progress tracking disabled")
    
    # Initialize loader
    logger.info("\n🚀 Initializing Railway data loader...")
    loader = RailwayDataLoader(
        zip_path=str(zip_path),
        redis_client=redis_client,
        progress_key="data_load_progress:cli"
    )
    
    # Show current progress if resuming
    if args.resume:
        progress = loader.get_progress()
        if progress['status'] != 'not_started':
            logger.info(f"📍 Last checkpoint: {progress['last_checkpoint']:,} rows")
            logger.info(f"   Status: {progress['status']}")
            logger.info(f"   Resuming from checkpoint...")
        else:
            logger.info("   No previous progress found, starting fresh")
    
    # Start loading
    logger.info(f"\n⏳ Starting data load...")
    logger.info(f"   State filter: {args.state}")
    logger.info(f"   Chunk size: {args.chunk_size:,} rows")
    logger.info(f"   Resume: {args.resume}")
    if args.max_rows:
        logger.info(f"   Max rows: {args.max_rows:,} (TEST MODE)")
    logger.info("")
    
    try:
        stats = loader.load_data(
            state_filter=args.state,
            resume=args.resume,
            max_rows=args.max_rows
        )
        
        # Show results
        logger.info("\n" + "="*60)
        logger.info("✅ DATA LOAD COMPLETE!")
        logger.info("="*60)
        logger.info(f"   Total claims: {stats['total_claims']:,}")
        logger.info(f"   Total providers: {stats['total_providers']:,}")
        logger.info(f"   Chunks processed: {stats['chunks_processed']:,}")
        logger.info(f"   Elapsed time: {stats['elapsed_seconds']:.1f} seconds ({stats['elapsed_seconds']/3600:.2f} hours)")
        logger.info(f"   Speed: {stats['rows_per_second']:.1f} rows/second")
        logger.info("="*60)
        logger.info("\n🎉 Your MediFraudy platform now has REAL data!")
        logger.info("\nNext steps:")
        logger.info("1. Open your Railway app URL")
        logger.info("2. Go to 'Providers' tab to search real facilities")
        logger.info("3. Go to 'Fraud Rings' tab for network analysis")
        logger.info("4. Go to 'Pattern Analysis' for POL forensics")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Loading interrupted by user")
        logger.info("   Progress saved. Run with --resume to continue")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Loading failed: {e}", exc_info=True)
        logger.info("\n💡 Troubleshooting:")
        logger.info("   1. Check Railway logs: railway logs --service worker")
        logger.info("   2. Verify database connection: railway run psql $DATABASE_URL")
        logger.info("   3. Check memory usage: railway ps")
        logger.info("   4. See RAILWAY_DATA_LOADING.md for detailed help")
        sys.exit(1)


if __name__ == "__main__":
    main()
