#!/usr/bin/env python
"""Export multiple cases as attorney-ready packages."""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import zipfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Case
from routes.export import generate_case_package

def main():
    parser = argparse.ArgumentParser(description="Export case packages")
    parser.add_argument("--case-ids", required=True, help="Comma-separated case IDs")
    parser.add_argument("--output", "-o", default="exports", help="Output directory")
    parser.add_argument("--format", choices=["json", "pdf", "both"], default="both")
    
    args = parser.parse_args()
    
    case_ids = [int(x.strip()) for x in args.case_ids.split(",")]
    out_dir = Path(args.output)
    out_dir.mkdir(exist_ok=True, parents=True)
    
    db = SessionLocal()
    
    try:
        for case_id in case_ids:
            case = db.query(Case).filter(Case.id == case_id).first()
            if not case:
                print(f"Case {case_id} not found")
                continue
            
            print(f"Exporting case {case_id}...")
            package = generate_case_package(db, case_id, format=args.format)
            
            if args.format in ["json", "both"]:
                json_path = out_dir / f"case_{case_id}_export.json"
                with open(json_path, "w") as f:
                    json.dump(package, f, indent=2)
                print(f"  JSON: {json_path}")
            
            if args.format in ["pdf", "both"] and package.get("pdf_path"):
                print(f"  PDF: {package['pdf_path']}")
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
