#!/usr/bin/env python
"""
NYC Elderly Care Facility Sweep
Runs Pattern-of-Life analysis on all NYC-area elderly care facilities
Outputs ranked list of highest-risk facilities for attorney review

Usage:
    python nyc_elderly_sweep.py --min-risk 70 --output high_risk_facilities.csv
    python nyc_elderly_sweep.py --limit 200 --format json
    python nyc_elderly_sweep.py --verbose --include-details
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Add parent directory to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, check_db_connection
from app.models import Provider
from app.analytics.pattern_of_life import (
    comprehensive_pattern_analysis,
    get_provider_risk_summary,
    analyze_nyc_elderly_care_facilities,
)
from app.analytics.pattern_of_life import POLResult

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Colors:
    """Terminal colors for pretty output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def get_nyc_facilities(db, facility_types: Optional[List[str]] = None, limit: Optional[int] = None):
    """Get all elderly care facilities in NYC area."""
    
    # NYC boroughs
    nyc_boroughs = ["New York", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    
    # Target facility types (case-insensitive)
    if facility_types is None:
        facility_types = [
            "Nursing Home",
            "Adult Day Care",
            "Home Health Agency",
            "Skilled Nursing Facility",
            "Rehabilitation Facility",
            "Assisted Living",
            "Long Term Care",
            "Adult Day Health Care",
            "Home Care",
        ]
    
    # Build query
    query = db.query(Provider).filter(Provider.state == "NY")
    
    # Filter by NYC boroughs
    borough_filters = []
    for borough in nyc_boroughs:
        borough_filters.append(Provider.city.ilike(f"%{borough}%"))
    from sqlalchemy import or_
    query = query.filter(or_(*borough_filters))
    
    # Filter by facility type
    type_filters = []
    for ft in facility_types:
        type_filters.append(Provider.facility_type.ilike(f"%{ft}%"))
    query = query.filter(or_(*type_filters))
    
    # Apply limit if specified
    if limit:
        query = query.limit(limit)
    
    return query.all()


def sweep_nyc_elderly(
    min_risk: int = 50,
    output: str = "nyc_sweep_results.csv",
    limit: Optional[int] = None,
    format: str = "csv",
    verbose: bool = False,
    use_cache: bool = True,
    include_details: bool = False
) -> List[Dict[str, Any]]:
    """
    Run comprehensive sweep of NYC elderly care facilities.
    
    Args:
        min_risk: Minimum risk score to include in results (0-100)
        output: Output file path
        limit: Maximum number of facilities to analyze
        format: Output format ('csv', 'json', or 'both')
        verbose: Print detailed progress
        use_cache: Use cached POL results if available
        include_details: Include full analysis details in output
        
    Returns:
        List of high-risk facilities with their risk scores
    """
    print_header(f"NYC ELDERLY CARE FACILITY SWEEP")
    print_info(f"Minimum risk threshold: {min_risk}")
    print_info(f"Output file: {output}")
    if limit:
        print_info(f"Limit: {limit} facilities")
    
    db = SessionLocal()
    try:
        # Check if we can use the built-in sweep function
        if not include_details and not verbose:
            # Use the optimized sweep function from pattern_of_life
            print_info("Running optimized sweep...")
            result = analyze_nyc_elderly_care_facilities(db, min_risk, limit or 100)
            
            facilities = result.get("results", [])
            
            # Print summary
            print_success(f"Sweep complete!")
            print(f"\n{Colors.BOLD}Summary:{Colors.END}")
            print(f"  Providers analyzed: {result['providers_analyzed']}")
            print(f"  High-risk facilities: {Colors.RED}{result['high_risk_facilities']}{Colors.END}")
            
            if 'risk_distribution' in result:
                dist = result['risk_distribution']
                print(f"  Risk distribution:")
                print(f"    {Colors.RED}HIGH: {dist.get('HIGH', 0)}{Colors.END}")
                print(f"    {Colors.YELLOW}MEDIUM: {dist.get('MEDIUM', 0)}{Colors.END}")
                print(f"    {Colors.GREEN}LOW: {dist.get('LOW', 0)}{Colors.END}")
            
            # Show top results
            if facilities:
                print(f"\n{Colors.BOLD}Top High-Risk Facilities:{Colors.END}")
                for i, facility in enumerate(facilities[:10], 1):
                    risk_color = (Colors.RED if facility['severity'] == 'HIGH'
                                else Colors.YELLOW if facility['severity'] == 'MEDIUM'
                                else Colors.GREEN)
                    print(f"  {i}. {facility['name']} - {facility['city']}")
                    print(f"     Risk: {risk_color}{facility['risk_score']} ({facility['severity']}){Colors.END}")
                    print(f"     Findings: {facility['findings_count']}")
            
            # Save results
            _save_results(result.get("results", []), output, format)
            
            return facilities
        
        # Manual sweep (more detailed)
        print_info("Fetching NYC facilities...")
        facilities = get_nyc_facilities(db, limit=limit)
        
        if not facilities:
            print_error("No facilities found")
            return []
        
        print_info(f"Found {len(facilities)} facilities. Analyzing...")
        
        results = []
        total = len(facilities)
        
        for idx, facility in enumerate(facilities, 1):
            if verbose:
                print_info(f"[{idx}/{total}] Analyzing {facility.name}...")
            
            try:
                # Check cache first
                if use_cache:
                    cached = db.query(POLResult).filter(
                        POLResult.provider_id == facility.id,
                        POLResult.expires_at > datetime.utcnow()
                    ).first()
                    
                    if cached:
                        risk_score = cached.risk_score
                        risk_level = cached.risk_level
                        findings_count = len(cached.full_results.get("all_findings", [])) if cached.full_results else 0
                        
                        if verbose:
                            print(f"  Using cached result: {risk_score} ({risk_level})")
                    else:
                        # Run full analysis
                        analysis = comprehensive_pattern_analysis(db, facility.id, use_cache=True)
                        risk_score = analysis.get("composite_risk_score", 0)
                        risk_level = analysis.get("severity", "LOW")
                        findings_count = analysis.get("total_findings", 0)
                        
                        if verbose:
                            print(f"  Analysis complete: {risk_score} ({risk_level})")
                else:
                    # Skip cache
                    analysis = comprehensive_pattern_analysis(db, facility.id, use_cache=False)
                    risk_score = analysis.get("composite_risk_score", 0)
                    risk_level = analysis.get("severity", "LOW")
                    findings_count = analysis.get("total_findings", 0)
                
                # Only include if meets minimum risk
                if risk_score >= min_risk:
                    result = {
                        "provider_id": facility.id,
                        "npi": facility.npi,
                        "name": facility.name,
                        "facility_type": facility.facility_type,
                        "city": facility.city,
                        "address": facility.address,
                        "risk_score": risk_score,
                        "severity": risk_level,
                        "findings_count": findings_count,
                    }
                    
                    if include_details and not use_cache:
                        result["full_analysis"] = analysis
                    
                    results.append(result)
                    
                    if verbose:
                        print_success(f"  Added to results (score: {risk_score})")
                
            except Exception as e:
                logger.error(f"Error analyzing facility {facility.id}: {e}")
                if verbose:
                    print_error(f"  Analysis failed: {e}")
        
        # Sort by risk score descending
        results.sort(key=lambda x: x["risk_score"], reverse=True)
        
        # Print summary
        print_success(f"\nSweep complete! Found {len(results)} facilities with risk >= {min_risk}")
        
        # Calculate distribution
        high = sum(1 for r in results if r["severity"] == "HIGH")
        medium = sum(1 for r in results if r["severity"] == "MEDIUM")
        low = sum(1 for r in results if r["severity"] == "LOW")
        
        print(f"\n{Colors.BOLD}Risk Distribution:{Colors.END}")
        print(f"  {Colors.RED}HIGH: {high}{Colors.END}")
        print(f"  {Colors.YELLOW}MEDIUM: {medium}{Colors.END}")
        print(f"  {Colors.GREEN}LOW: {low}{Colors.END}")
        
        # Show top results
        if results:
            print(f"\n{Colors.BOLD}Top 10 High-Risk Facilities:{Colors.END}")
            for i, facility in enumerate(results[:10], 1):
                risk_color = (Colors.RED if facility['severity'] == 'HIGH'
                            else Colors.YELLOW if facility['severity'] == 'MEDIUM'
                            else Colors.GREEN)
                print(f"  {i}. {facility['name']}")
                print(f"     Location: {facility['city']}")
                print(f"     Type: {facility['facility_type']}")
                print(f"     Risk: {risk_color}{facility['risk_score']} ({facility['severity']}){Colors.END}")
                print(f"     Findings: {facility['findings_count']}")
                if i < len(results[:10]):
                    print()
        
        # Save results
        _save_results(results, output, format)
        
        return results
        
    finally:
        db.close()


def _save_results(results: List[Dict[str, Any]], output: str, format: str):
    """Save results to file(s)."""
    if not results:
        print_warning("No results to save")
        return
    
    output_path = Path(output)
    
    # Save CSV
    if format in ["csv", "both"]:
        csv_path = output_path.with_suffix('.csv') if not str(output_path).endswith('.csv') else output_path
        
        with open(csv_path, 'w', newline='') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
        
        print_success(f"CSV saved to {csv_path}")
    
    # Save JSON
    if format in ["json", "both"]:
        json_path = output_path.with_suffix('.json') if not str(output_path).endswith('.json') else output_path
        
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print_success(f"JSON saved to {json_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="NYC Elderly Care Facility Sweep",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic sweep - find facilities with risk >= 70
  python nyc_elderly_sweep.py --min-risk 70 --output high_risk.csv
  
  # Limit to 50 facilities, save as JSON
  python nyc_elderly_sweep.py --limit 50 --format json --output results.json
  
  # Verbose mode with full details
  python nyc_elderly_sweep.py --verbose --include-details --output full_report.json
        """
    )
    
    parser.add_argument("--min-risk", type=int, default=50,
                       help="Minimum risk score to include (0-100, default: 50)")
    parser.add_argument("--output", "-o", default="nyc_sweep_results.csv",
                       help="Output file path (default: nyc_sweep_results.csv)")
    parser.add_argument("--limit", type=int,
                       help="Maximum number of facilities to analyze")
    parser.add_argument("--format", choices=["csv", "json", "both"], default="csv",
                       help="Output format (default: csv)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Print detailed progress")
    parser.add_argument("--no-cache", action="store_true",
                       help="Don't use cached POL results")
    parser.add_argument("--include-details", action="store_true",
                       help="Include full analysis details in output (JSON only)")
    
    args = parser.parse_args()
    
    # Validate database connection
    if not check_db_connection():
        print_error("Cannot connect to database. Is it running?")
        sys.exit(1)
    
    try:
        sweep_nyc_elderly(
            min_risk=args.min_risk,
            output=args.output,
            limit=args.limit,
            format=args.format,
            verbose=args.verbose,
            use_cache=not args.no_cache,
            include_details=args.include_details
        )
    except KeyboardInterrupt:
        print_warning("\nSweep cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
