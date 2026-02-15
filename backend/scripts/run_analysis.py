#!/usr/bin/env python
"""Command-line interface for running Medicaid fraud analyses.

A powerful CLI tool for:
- Single provider Pattern-of-Life analysis
- NYC elderly care facility sweep
- Attorney package generation

Usage:
    # Run POL on a single provider
    python run_analysis.py --provider 12345

    # Run NYC sweep with minimum risk threshold
    python run_analysis.py --sweep --min-risk 70 --output high_risk.csv

    # Generate attorney packages for a case
    python run_analysis.py --export --case-id 5
"""

import argparse
import json
import sys
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

# Add parent directory to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, check_db_connection
from analytics.pattern_of_life import (
    comprehensive_pattern_analysis,
    analyze_nyc_elderly_care_facilities,
    get_provider_risk_summary,
)
from models import Provider, Case
from routes.export import generate_case_export_package


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


def format_risk_score(score: int, level: str) -> str:
    """Format risk score with color based on level."""
    if level == "HIGH":
        return f"{Colors.RED}{score}{Colors.END}"
    elif level == "MEDIUM":
        return f"{Colors.YELLOW}{score}{Colors.END}"
    else:
        return f"{Colors.GREEN}{score}{Colors.END}"


def analyze_single_provider(
    provider_id: int,
    days: int = 365,
    output_dir: str = "reports",
    verbose: bool = False
) -> Dict[str, Any]:
    """Run comprehensive analysis on a single provider."""
    print_header(f"ANALYZING PROVIDER {provider_id}")
    
    db = SessionLocal()
    try:
        # Check if provider exists
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            print_error(f"Provider {provider_id} not found")
            return {"error": "Provider not found"}
        
        print_info(f"Provider: {provider.name}")
        print_info(f"Type: {provider.facility_type}")
        print_info(f"Location: {provider.city}, {provider.state}")
        print_info(f"Lookback days: {days}")
        
        # Run analysis
        print_info("Running Pattern-of-Life analysis...")
        result = comprehensive_pattern_analysis(db, provider_id, days)
        
        if "error" in result:
            print_error(result["error"])
            return result
        
        # Print summary
        print_success("Analysis complete!")
        print(f"\n{Colors.BOLD}Risk Score:{Colors.END} "
              f"{format_risk_score(result['composite_risk_score'], result['severity'])}")
        print(f"{Colors.BOLD}Risk Level:{Colors.END} {result['severity']}")
        print(f"{Colors.BOLD}Findings:{Colors.END} {result['total_findings']}")
        
        # Print detailed findings if verbose
        if verbose and result.get('all_findings'):
            print(f"\n{Colors.BOLD}Detailed Findings:{Colors.END}")
            for i, finding in enumerate(result['all_findings'][:5], 1):
                print(f"  {i}. {finding.get('description', 'No description')}")
                if 'severity' in finding:
                    sev_color = (Colors.RED if finding['severity'] == 'critical' or finding['severity'] == 'high'
                                else Colors.YELLOW if finding['severity'] == 'medium'
                                else Colors.GREEN)
                    print(f"     Severity: {sev_color}{finding['severity']}{Colors.END}")
        
        # Print module breakdown
        print(f"\n{Colors.BOLD}Module Scores:{Colors.END}")
        for module, data in result.get('analysis_modules', {}).items():
            score_color = (Colors.RED if data['risk_level'] == 'HIGH'
                          else Colors.YELLOW if data['risk_level'] == 'MEDIUM'
                          else Colors.GREEN)
            print(f"  {module}: {score_color}{data['risk_score']} ({data['risk_level']}){Colors.END} "
                  f"- {data['findings_count']} findings")
        
        # Save to file
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_path / f"provider_{provider_id}_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(result, f, indent=2)
        
        print_success(f"Full report saved to {filename}")
        
        return result
        
    finally:
        db.close()


def run_nyc_sweep(
    min_risk: int = 50,
    limit: int = 100,
    output: Optional[str] = None,
    format: str = "both"
) -> Dict[str, Any]:
    """Run NYC elderly care facility sweep."""
    print_header(f"NYC ELDERLY CARE SWEEP (min risk: {min_risk})")
    
    db = SessionLocal()
    try:
        print_info("Analyzing all NYC elderly care facilities...")
        result = analyze_nyc_elderly_care_facilities(db, min_risk, limit)
        
        # Print summary
        print_success("Sweep complete!")
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
        if result.get('results'):
            print(f"\n{Colors.BOLD}Top High-Risk Facilities:{Colors.END}")
            for i, facility in enumerate(result['results'][:10], 1):
                risk_color = (Colors.RED if facility['severity'] == 'HIGH'
                            else Colors.YELLOW if facility['severity'] == 'MEDIUM'
                            else Colors.GREEN)
                print(f"  {i}. {facility['name']} - {facility['city']}")
                print(f"     Risk: {risk_color}{facility['risk_score']} ({facility['severity']}){Colors.END}")
                print(f"     Findings: {facility['findings_count']}")
        
        # Save output if requested
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(exist_ok=True, parents=True)
            
            if format in ["csv", "both"] and result.get('results'):
                df = pd.DataFrame(result['results'])
                csv_path = output_path.with_suffix('.csv') if not str(output_path).endswith('.csv') else output_path
                df.to_csv(csv_path, index=False)
                print_success(f"CSV saved to {csv_path}")
            
            if format in ["json", "both"]:
                json_path = output_path.with_suffix('.json') if not str(output_path).endswith('.json') else output_path
                with open(json_path, "w") as f:
                    json.dump(result, f, indent=2)
                print_success(f"JSON saved to {json_path}")
        
        return result
        
    finally:
        db.close()


def export_case(case_id: int, output_dir: str = "exports", format: str = "pdf") -> Dict[str, Any]:
    """Generate attorney package for a case."""
    print_header(f"EXPORTING CASE {case_id}")
    
    db = SessionLocal()
    try:
        # Check if case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            print_error(f"Case {case_id} not found")
            return {"error": "Case not found"}
        
        # Get provider info
        provider = db.query(Provider).filter(Provider.id == case.provider_id).first()
        
        print_info(f"Case ID: {case.case_id}")
        print_info(f"Provider: {provider.name if provider else 'Unknown'}")
        print_info(f"Status: {case.status}")
        print_info(f"Format: {format}")
        
        # Generate package
        print_info("Generating attorney package...")
        package = export_case_package(case_id, db, format=format)
        
        if "error" in package:
            print_error(package["error"])
            return package
        
        # Save to file
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            filename = output_path / f"case_{case_id}_{timestamp}.json"
            with open(filename, "w") as f:
                json.dump(package, f, indent=2)
            print_success(f"JSON package saved to {filename}")
        
        elif format == "pdf":
            if package.get("pdf_path"):
                print_success(f"PDF package saved to {package['pdf_path']}")
            else:
                print_warning("PDF generation not available")
        
        elif format == "both":
            # Save JSON
            json_path = output_path / f"case_{case_id}_{timestamp}.json"
            with open(json_path, "w") as f:
                json.dump(package, f, indent=2)
            print_success(f"JSON saved to {json_path}")
            
            # PDF path if available
            if package.get("pdf_path"):
                print_success(f"PDF saved to {package['pdf_path']}")
        
        # Print summary
        if package.get("pol_analysis"):
            pol = package["pol_analysis"]
            risk = pol.get('composite_risk_score', 0)
            level = pol.get('severity', 'UNKNOWN')
            print(f"\n{Colors.BOLD}Case Summary:{Colors.END}")
            print(f"  Risk Score: {format_risk_score(risk, level)}")
            print(f"  Findings: {pol.get('total_findings', 0)}")
        
        return package
        
    finally:
        db.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Medicaid Fraud Analysis CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run POL on a single provider
  python run_analysis.py --provider 12345
  
  # Run NYC sweep with minimum risk threshold
  python run_analysis.py --sweep --min-risk 70 --output high_risk.csv
  
  # Generate attorney packages for a case
  python run_analysis.py --export --case-id 5
        """
    )
    
    # Mutually exclusive main commands
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--provider", type=int, help="Analyze single provider by ID")
    group.add_argument("--sweep", action="store_true", help="Run NYC elderly care sweep")
    group.add_argument("--export", action="store_true", help="Export case package")
    
    # Provider analysis options
    parser.add_argument("--days", type=int, default=365, help="Lookback days (default: 365)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed findings")
    
    # Sweep options
    parser.add_argument("--min-risk", type=int, default=50, help="Minimum risk score for sweep (default: 50)")
    parser.add_argument("--limit", type=int, default=100, help="Max providers to analyze (default: 100)")
    parser.add_argument("--output", "-o", help="Output file path (for sweep results)")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both", 
                       help="Output format (default: both)")
    
    # Export options
    parser.add_argument("--case-id", type=int, help="Case ID to export")
    
    # Common options
    parser.add_argument("--output-dir", default="reports", help="Output directory (default: reports)")
    
    args = parser.parse_args()
    
    # Validate database connection first
    if not check_db_connection():
        print_error("Cannot connect to database. Is it running?")
        sys.exit(1)
    
    try:
        if args.provider:
            # Single provider analysis
            analyze_single_provider(
                provider_id=args.provider,
                days=args.days,
                output_dir=args.output_dir,
                verbose=args.verbose
            )
        
        elif args.sweep:
            # NYC sweep
            run_nyc_sweep(
                min_risk=args.min_risk,
                limit=args.limit,
                output=args.output,
                format=args.format
            )
        
        elif args.export:
            # Export case
            if not args.case_id:
                print_error("--case-id required with --export")
                sys.exit(1)
            
            export_case(
                case_id=args.case_id,
                output_dir=args.output_dir,
                format=args.format
            )
    
    except KeyboardInterrupt:
        print_warning("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
