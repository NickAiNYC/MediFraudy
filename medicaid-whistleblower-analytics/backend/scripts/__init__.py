"""Medicaid Whistleblower Analytics - Command Line Scripts.

This package contains CLI tools for running analyses, exporting cases,
and managing the Medicaid fraud detection platform without the web UI.

Available scripts:
    run_analysis.py         - Run POL analysis on providers, NYC sweep, export cases
    nyc_elderly_sweep.py    - Dedicated NYC elderly care facility sweep
    export_cases.py         - Batch export attorney packages
    load_data.py            - Ingest Medicaid dataset into database
    check_db.py             - Database health check and statistics
    generate_reports.py     - Generate PDF/JSON reports for providers
    validate_data.py        - Validate dataset before loading
"""

# This file makes the scripts directory a Python package
# allowing imports like: from scripts.run_analysis import main

__version__ = "0.1.0"
__author__ = "Medicaid Whistleblower Analytics"
__license__ = "MIT"

# ---------------------------------------------------------------------------
# Import from run_analysis.py
# ---------------------------------------------------------------------------
from .run_analysis import (
    analyze_single_provider,
    run_nyc_sweep,
    export_case,
    format_risk_score,
    print_header,
    print_success,
    print_warning,
    print_error,
    print_info,
)

# ---------------------------------------------------------------------------
# Import from nyc_elderly_sweep.py
# ---------------------------------------------------------------------------
from .nyc_elderly_sweep import (
    sweep_nyc_elderly,
    get_nyc_facilities,
    Colors as SweepColors,  # Renamed to avoid conflict
)

# ---------------------------------------------------------------------------
# Import from export_cases.py
# ---------------------------------------------------------------------------
try:
    from .export_cases import (
        export_multiple_cases,
        generate_case_summary,
        batch_export_to_zip,
    )
    EXPORT_AVAILABLE = True
except ImportError:
    EXPORT_AVAILABLE = False
    # Define placeholder if script not yet created
    def export_multiple_cases(*args, **kwargs):
        raise NotImplementedError("export_cases.py not yet implemented")
    
    def generate_case_summary(*args, **kwargs):
        raise NotImplementedError("export_cases.py not yet implemented")
    
    def batch_export_to_zip(*args, **kwargs):
        raise NotImplementedError("export_cases.py not yet implemented")

# ---------------------------------------------------------------------------
# Import from load_data.py
# ---------------------------------------------------------------------------
try:
    from .load_data import (
        load_medicaid_dataset,
        ingest_chunks,
        validate_and_load,
    )
    LOAD_AVAILABLE = True
except ImportError:
    LOAD_AVAILABLE = False
    # Define placeholder if script not yet created
    def load_medicaid_dataset(*args, **kwargs):
        raise NotImplementedError("load_data.py not yet implemented")
    
    def ingest_chunks(*args, **kwargs):
        raise NotImplementedError("load_data.py not yet implemented")
    
    def validate_and_load(*args, **kwargs):
        raise NotImplementedError("load_data.py not yet implemented")

# ---------------------------------------------------------------------------
# Import from check_db.py
# ---------------------------------------------------------------------------
try:
    from .check_db import (
        check_database_health,
        get_database_stats,
        verify_connections,
        print_db_status,
    )
    CHECK_AVAILABLE = True
except ImportError:
    CHECK_AVAILABLE = False
    # Define placeholder if script not yet created
    def check_database_health(*args, **kwargs):
        raise NotImplementedError("check_db.py not yet implemented")
    
    def get_database_stats(*args, **kwargs):
        raise NotImplementedError("check_db.py not yet implemented")
    
    def verify_connections(*args, **kwargs):
        raise NotImplementedError("check_db.py not yet implemented")
    
    def print_db_status(*args, **kwargs):
        raise NotImplementedError("check_db.py not yet implemented")

# ---------------------------------------------------------------------------
# Import from generate_reports.py
# ---------------------------------------------------------------------------
try:
    from .generate_reports import (
        generate_provider_report,
        generate_batch_reports,
        create_attorney_package,
    )
    REPORTS_AVAILABLE = True
except ImportError:
    REPORTS_AVAILABLE = False
    # Define placeholder if script not yet created
    def generate_provider_report(*args, **kwargs):
        raise NotImplementedError("generate_reports.py not yet implemented")
    
    def generate_batch_reports(*args, **kwargs):
        raise NotImplementedError("generate_reports.py not yet implemented")
    
    def create_attorney_package(*args, **kwargs):
        raise NotImplementedError("generate_reports.py not yet implemented")

# ---------------------------------------------------------------------------
# Import from validate_data.py
# ---------------------------------------------------------------------------
try:
    from .validate_data import (
        validate_dataset,
        check_data_quality,
        preview_dataset,
    )
    VALIDATE_AVAILABLE = True
except ImportError:
    VALIDATE_AVAILABLE = False
    # Define placeholder if script not yet created
    def validate_dataset(*args, **kwargs):
        raise NotImplementedError("validate_data.py not yet implemented")
    
    def check_data_quality(*args, **kwargs):
        raise NotImplementedError("validate_data.py not yet implemented")
    
    def preview_dataset(*args, **kwargs):
        raise NotImplementedError("validate_data.py not yet implemented")

# ---------------------------------------------------------------------------
# Package-level utility functions
# ---------------------------------------------------------------------------

def get_available_scripts() -> list:
    """Return list of available scripts in the package."""
    scripts = [
        "run_analysis.py",
        "nyc_elderly_sweep.py",
    ]
    
    if EXPORT_AVAILABLE:
        scripts.append("export_cases.py")
    if LOAD_AVAILABLE:
        scripts.append("load_data.py")
    if CHECK_AVAILABLE:
        scripts.append("check_db.py")
    if REPORTS_AVAILABLE:
        scripts.append("generate_reports.py")
    if VALIDATE_AVAILABLE:
        scripts.append("validate_data.py")
    
    return scripts


def get_version() -> str:
    """Return package version."""
    return __version__


def print_help() -> None:
    """Print help information about available scripts."""
    print(f"\n{'='*60}")
    print(f"Medicaid Whistleblower Analytics - CLI Tools v{__version__}")
    print(f"{'='*60}\n")
    
    print("Available scripts:\n")
    
    scripts_info = [
        ("run_analysis.py", "Run POL analysis, NYC sweep, export cases"),
        ("nyc_elderly_sweep.py", "Dedicated NYC elderly care facility sweep"),
        ("export_cases.py", "Batch export attorney packages"),
        ("load_data.py", "Ingest Medicaid dataset into database"),
        ("check_db.py", "Database health check and statistics"),
        ("generate_reports.py", "Generate PDF/JSON reports for providers"),
        ("validate_data.py", "Validate dataset before loading"),
    ]
    
    for script, description in scripts_info:
        status = "✅" if script.replace('.py', '') in [
            s.replace('.py', '') for s in get_available_scripts()
        ] else "⏳"
        print(f"  {status} {script:<20} - {description}")
    
    print(f"\n{'='*60}")
    print("Run any script with --help for usage information:")
    print("  python scripts/run_analysis.py --help")
    print("  python scripts/nyc_elderly_sweep.py --help")
    print(f"{'='=60}\n")


# ---------------------------------------------------------------------------
# Package-level exports
# ---------------------------------------------------------------------------

__all__ = [
    # Version and metadata
    '__version__',
    '__author__',
    '__license__',
    'get_available_scripts',
    'get_version',
    'print_help',
    
    # From run_analysis.py
    'analyze_single_provider',
    'run_nyc_sweep',
    'export_case',
    'format_risk_score',
    'print_header',
    'print_success',
    'print_warning',
    'print_error',
    'print_info',
    
    # From nyc_elderly_sweep.py
    'sweep_nyc_elderly',
    'get_nyc_facilities',
    
    # From export_cases.py (if available)
    'export_multiple_cases',
    'generate_case_summary',
    'batch_export_to_zip',
    
    # From load_data.py (if available)
    'load_medicaid_dataset',
    'ingest_chunks',
    'validate_and_load',
    
    # From check_db.py (if available)
    'check_database_health',
    'get_database_stats',
    'verify_connections',
    'print_db_status',
    
    # From generate_reports.py (if available)
    'generate_provider_report',
    'generate_batch_reports',
    'create_attorney_package',
    
    # From validate_data.py (if available)
    'validate_dataset',
    'check_data_quality',
    'preview_dataset',
]

# ---------------------------------------------------------------------------
# Initialize - print help when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print_help()
