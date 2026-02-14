"""Medicaid Whistleblower Analytics - Command Line Scripts.

This package contains CLI tools for running analyses, exporting cases,
and managing the Medicaid fraud detection platform without the web UI.

Available scripts:
    run_analysis.py     - Run POL analysis on providers, NYC sweep, export cases
    export_cases.py     - Batch export attorney packages
    load_data.py        - Ingest Medicaid dataset into database
    check_db.py         - Database health check and statistics
"""

# This file makes the scripts directory a Python package
# allowing imports like: from scripts.run_analysis import main

__version__ = "0.1.0"
__author__ = "Medicaid Whistleblower Analytics"

# Export commonly used functions for easier imports
from .run_analysis import (
    analyze_single_provider,
    run_nyc_sweep,
    export_case,
)

__all__ = [
    'analyze_single_provider',
    'run_nyc_sweep',
    'export_case',
]
