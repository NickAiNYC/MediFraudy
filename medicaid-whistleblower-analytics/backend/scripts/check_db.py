#!/usr/bin/env python
"""Check database connection and stats."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import check_db_connection, get_db_stats, engine
from models import Provider, Claim, Anomaly

def main():
    print("Checking database connection...")
    if not check_db_connection():
        print("❌ Database connection failed")
        sys.exit(1)
    print("✅ Database connected")
    
    # Get connection pool stats
    stats = get_db_stats()
    print(f"\nConnection pool:")
    print(f"  Size: {stats['size']}")
    print(f"  Checked in: {stats['checked_in_connections']}")
    print(f"  Overflow: {stats['overflow']}")
    
    # Count records
    with engine.connect() as conn:
        provider_count = conn.execute("SELECT COUNT(*) FROM providers").scalar()
        claim_count = conn.execute("SELECT COUNT(*) FROM claims").scalar()
        anomaly_count = conn.execute("SELECT COUNT(*) FROM anomalies").scalar()
    
    print(f"\nRecords:")
    print(f"  Providers: {provider_count}")
    print(f"  Claims: {claim_count}")
    print(f"  Anomalies: {anomaly_count}")

if __name__ == "__main__":
    main()
