#!/usr/bin/env python
"""Load Medicaid dataset into database."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, engine, Base
from data_ingestion.loader import MedicaidDataLoader
from data_ingestion.transformer import transform_medicaid_data
from models import Provider, Claim

def main():
    parser = argparse.ArgumentParser(description="Load Medicaid dataset")
    parser.add_argument("--file", help="Path to dataset file")
    parser.add_argument("--url", help="URL to download from")
    parser.add_argument("--sample", type=int, help="Load only N rows (for testing)")
    parser.add_argument("--chunksize", type=int, default=50000, help="Chunk size")
    parser.add_argument("--state", default="NY", help="Filter to state")
    
    args = parser.parse_args()
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Load data
    loader = MedicaidDataLoader(
        file_path=args.file,
        url=args.url,
    )
    
    print("Loading data...")
    df = loader.ensure_data(sample=args.sample)
    
    print(f"Loaded {len(df)} rows")
    
    # Transform
    print("Transforming data...")
    df = transform_medicaid_data(df, state=args.state)
    
    # Load into database (simplified - would need proper bulk insert)
    print("Loading into database...")
    # ... bulk insert logic ...
    
    print("Done!")

if __name__ == "__main__":
    main()
