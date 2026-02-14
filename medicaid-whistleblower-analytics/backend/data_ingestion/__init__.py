"""Data ingestion package for Medicaid claims dataset.

This package handles downloading, loading, validating, and transforming
the 10.32GB HHS DOGE Medicaid dataset with memory-efficient processing.

Modules:
    loader.py      - Download and load large CSV/Parquet/ZIP files
    validator.py   - Schema validation and data quality checks
    transformer.py - Data cleaning and feature engineering
"""

import logging
from typing import Optional, Generator, List, Dict, Any, Union

# Import from loader.py
from .loader import (
    download_dataset,
    load_csv_chunks,
    validate_schema as validate_schema_loader,
    detect_and_load,
    MedicaidDataLoader,
    load_parquet_chunks,
    get_data_profile,
)

# Import from validator.py
try:
    from .validator import (
        validate_schema as validate_schema_validator,
        check_nulls,
        check_duplicates,
        check_value_ranges,
        check_date_consistency,
        check_cross_field_consistency,
        generate_data_quality_report,
        quick_validate,
        RULES as VALIDATOR_RULES,
    )
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    # Define placeholders
    def validate_schema_validator(*args, **kwargs):
        raise NotImplementedError("validator.py not yet implemented")
    
    def check_nulls(*args, **kwargs):
        raise NotImplementedError("validator.py not yet implemented")
    
    def check_duplicates(*args, **kwargs):
        raise NotImplementedError("validator.py not yet implemented")
    
    def check_value_ranges(*args, **kwargs):
        raise NotImplementedError("validator.py not yet implemented")
    
    def check_date_consistency(*args, **kwargs):
        raise NotImplementedError("validator.py not yet implemented")
    
    def check_cross_field_consistency(*args, **kwargs):
        raise NotImplementedError("validator.py not yet implemented")
    
    def generate_data_quality_report(*args, **kwargs):
        raise NotImplementedError("validator.py not yet implemented")
    
    def quick_validate(*args, **kwargs):
        raise NotImplementedError("validator.py not yet implemented")
    
    VALIDATOR_RULES = []

# Import from transformer.py
try:
    from .transformer import (
        normalize_npi,
        normalize_state,
        clean_currency,
        normalize_dates,
        clean_categorical,
        filter_state,
        filter_date_range,
        filter_billing_codes,
        add_date_features,
        add_claim_features,
        add_kickback_features,
        add_capacity_features,
        transform_medicaid_data,
    )
    TRANSFORMER_AVAILABLE = True
except ImportError:
    TRANSFORMER_AVAILABLE = False
    # Define placeholders
    def normalize_npi(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def normalize_state(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def clean_currency(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def normalize_dates(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def clean_categorical(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def filter_state(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def filter_date_range(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def filter_billing_codes(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def add_date_features(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def add_claim_features(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def add_kickback_features(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def add_capacity_features(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")
    
    def transform_medicaid_data(*args, **kwargs):
        raise NotImplementedError("transformer.py not yet implemented")

# ---------------------------------------------------------------------------
# Package metadata
# ---------------------------------------------------------------------------

__version__ = "0.1.0"
__author__ = "Medicaid Whistleblower Analytics"
__all__ = [
    # Loader functions
    'download_dataset',
    'load_csv_chunks',
    'load_parquet_chunks',
    'detect_and_load',
    'MedicaidDataLoader',
    'get_data_profile',
    
    # Validator functions
    'validate_schema',
    'check_nulls',
    'check_duplicates',
    'check_value_ranges',
    'check_date_consistency',
    'check_cross_field_consistency',
    'generate_data_quality_report',
    'quick_validate',
    'VALIDATOR_RULES',
    
    # Transformer functions
    'normalize_npi',
    'normalize_state',
    'clean_currency',
    'normalize_dates',
    'clean_categorical',
    'filter_state',
    'filter_date_range',
    'filter_billing_codes',
    'add_date_features',
    'add_claim_features',
    'add_kickback_features',
    'add_capacity_features',
    'transform_medicaid_data',
]

# ---------------------------------------------------------------------------
# Convenience wrapper for validate_schema (handles both loader and validator)
# ---------------------------------------------------------------------------

def validate_schema(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    column_types: Optional[Dict[str, type]] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Validate DataFrame schema with enhanced checks.
    
    This is a convenience function that uses the validator implementation
    if available, otherwise falls back to the basic loader validation.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        column_types: Dict mapping column names to expected types
        strict: If True, raise error on validation failure
        
    Returns:
        Dictionary with validation results
    """
    if VALIDATOR_AVAILABLE:
        return validate_schema_validator(df, required_columns, column_types, strict)
    else:
        # Fall back to basic validation
        cols = required_columns or []
        passed = validate_schema_loader(df, cols)
        return {
            "passed": passed,
            "missing_columns": [],
            "message": "Basic validation only (validator.py not available)"
        }

# ---------------------------------------------------------------------------
# Package-level utility functions
# ---------------------------------------------------------------------------

def get_available_modules() -> Dict[str, bool]:
    """Return dictionary of available submodules."""
    return {
        "loader": True,  # Always available
        "validator": VALIDATOR_AVAILABLE,
        "transformer": TRANSFORMER_AVAILABLE,
    }


def print_module_status() -> None:
    """Print status of all data ingestion modules."""
    print(f"\n{'='*60}")
    print(f"Data Ingestion Package v{__version__}")
    print(f"{'='*60}\n")
    
    modules = [
        ("loader.py", True, "Download, chunk loading, ZIP support"),
        ("validator.py", VALIDATOR_AVAILABLE, "Schema validation, data quality"),
        ("transformer.py", TRANSFORMER_AVAILABLE, "Cleaning, feature engineering"),
    ]
    
    for module, available, description in modules:
        status = "✅" if available else "⏳"
        print(f"  {status} {module:<15} - {description}")
    
    print(f"\n{'='=60}\n")


def get_pipeline_steps() -> List[Dict[str, str]]:
    """Return recommended pipeline steps for data ingestion."""
    steps = [
        {
            "step": "download",
            "function": "download_dataset()",
            "description": "Download dataset from URL"
        },
        {
            "step": "validate_schema",
            "function": "validate_schema()",
            "description": "Check required columns and types"
        },
        {
            "step": "load_chunks",
            "function": "load_csv_chunks() or detect_and_load()",
            "description": "Load data in memory-efficient chunks"
        },
        {
            "step": "quality_check",
            "function": "quick_validate()",
            "description": "Basic data quality checks"
        },
        {
            "step": "transform",
            "function": "transform_medicaid_data()",
            "description": "Clean and engineer features"
        },
        {
            "step": "full_validation",
            "function": "generate_data_quality_report()",
            "description": "Comprehensive quality report"
        },
    ]
    return steps

# ---------------------------------------------------------------------------
# Initialize - print status when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print_module_status()
    
    print("\nRecommended pipeline:")
    for i, step in enumerate(get_pipeline_steps(), 1):
        print(f"  {i}. {step['step']:<15} - {step['function']}")
        print(f"     {step['description']}")
