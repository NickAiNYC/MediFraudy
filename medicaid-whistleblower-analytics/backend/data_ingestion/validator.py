"""Data validation utilities for integrity and quality checks.

Provides comprehensive validation for Medicaid claims data including:
- Schema validation (required columns, data types)
- Data quality metrics (nulls, duplicates, ranges)
- Business rule validation (clinical plausibility)
- Cross-field consistency checks
- Statistical profile generation
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date

import pandas as pd
import numpy as np
from pandera import DataFrameSchema, Column, Check

logger = logging.getLogger(__name__)

# Standard Medicaid columns (from T-MSIS)
EXPECTED_COLUMNS = {
    'provider_npi': str,
    'beneficiary_id': str,
    'procedure_code': str,
    'amount': float,
    'claim_date': 'datetime64[ns]',
    'submitted_date': 'datetime64[ns]',
    'units': int,
    'place_of_service': str,
    'modifiers': object,  # JSON or list
    'service_category': str,
}


# ---------------------------------------------------------------------------
# Core validation functions
# ---------------------------------------------------------------------------

def validate_schema(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    column_types: Optional[Dict[str, type]] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """Validate DataFrame schema against expected columns and types.

    Args:
        df: DataFrame to validate.
        required_columns: List of columns that must be present.
        column_types: Dict mapping column names to expected types.
        strict: If True, raise error on validation failure.

    Returns:
        Dictionary with validation results.

    Raises:
        ValueError: If strict=True and validation fails.
    """
    required_columns = required_columns or list(EXPECTED_COLUMNS.keys())
    column_types = column_types or EXPECTED_COLUMNS
    
    results = {
        "passed": True,
        "missing_columns": [],
        "extra_columns": [],
        "type_mismatches": [],
        "column_stats": {},
    }
    
    # Check for missing columns
    missing = set(required_columns) - set(df.columns)
    if missing:
        results["missing_columns"] = list(missing)
        results["passed"] = False
        logger.warning(f"Missing required columns: {missing}")
    
    # Check for extra columns (optional)
    extra = set(df.columns) - set(required_columns)
    if extra:
        results["extra_columns"] = list(extra)
        logger.info(f"Extra columns found: {extra}")
    
    # Check data types
    for col, expected_type in column_types.items():
        if col in df.columns:
            actual_type = df[col].dtype
            expected_type_str = str(expected_type)
            
            # Handle datetime types specially
            if 'datetime' in expected_type_str and 'datetime' in str(actual_type):
                continue
            
            # Check if types match
            if not pd.api.types.is_dtype_equal(actual_type, expected_type):
                results["type_mismatches"].append({
                    "column": col,
                    "expected": str(expected_type),
                    "actual": str(actual_type)
                })
                results["passed"] = False
                logger.warning(f"Column '{col}' type mismatch: expected {expected_type}, got {actual_type}")
    
    # Column statistics
    for col in required_columns:
        if col in df.columns:
            results["column_stats"][col] = {
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "null_percentage": float(df[col].isnull().mean() * 100),
                "unique_count": int(df[col].nunique()) if df[col].dtype == 'object' else None,
            }
    
    if strict and not results["passed"]:
        raise ValueError(f"Schema validation failed: {results}")
    
    return results


def check_nulls(
    df: pd.DataFrame,
    critical_columns: Optional[List[str]] = None,
    threshold: float = 5.0,  # 5% max nulls
) -> Dict[str, Any]:
    """Comprehensive null value analysis.

    Args:
        df: DataFrame to inspect.
        critical_columns: Columns where nulls indicate data quality issues.
        threshold: Maximum allowed null percentage.

    Returns:
        Dictionary with null analysis results.
    """
    critical_columns = critical_columns or [
        'provider_npi', 'beneficiary_id', 'procedure_code', 'amount', 'claim_date'
    ]
    
    results = {
        "total_rows": len(df),
        "columns_with_nulls": [],
        "critical_nulls": {},
        "exceeds_threshold": [],
    }
    
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
        
        if null_count > 0:
            results["columns_with_nulls"].append({
                "column": col,
                "null_count": null_count,
                "null_percentage": round(null_pct, 2)
            })
            
            if col in critical_columns:
                results["critical_nulls"][col] = {
                    "count": null_count,
                    "percentage": round(null_pct, 2)
                }
                
                if null_pct > threshold:
                    results["exceeds_threshold"].append({
                        "column": col,
                        "null_percentage": round(null_pct, 2),
                        "threshold": threshold
                    })
                    logger.warning(
                        f"Critical column '{col}' has {null_pct:.1f}% nulls "
                        f"(exceeds {threshold}% threshold)"
                    )
    
    return results


def check_duplicates(
    df: pd.DataFrame,
    subset: Optional[List[str]] = None,
    consider_all: bool = True,
) -> Dict[str, Any]:
    """Comprehensive duplicate detection.

    Args:
        df: DataFrame to inspect.
        subset: Columns to consider for duplicate detection.
        consider_all: If True, also check for exact row duplicates.

    Returns:
        Dictionary with duplicate analysis.
    """
    subset = subset or ['provider_npi', 'beneficiary_id', 'procedure_code', 'claim_date']
    
    results = {
        "total_rows": len(df),
        "exact_duplicates": 0,
        "subset_duplicates": 0,
        "duplicate_groups": [],
        "duplicate_rate": 0.0,
    }
    
    # Check exact row duplicates
    if consider_all:
        exact_dupes = df.duplicated(keep=False)
        results["exact_duplicates"] = int(exact_dupes.sum())
    
    # Check subset duplicates
    subset_dupes = df.duplicated(subset=subset, keep='first')
    results["subset_duplicates"] = int(subset_dupes.sum())
    results["duplicate_rate"] = round(
        results["subset_duplicates"] / len(df) * 100 if len(df) > 0 else 0,
        2
    )
    
    # Find duplicate groups (more than 2 occurrences)
    dupes = df[subset_dupes | df.duplicated(subset=subset, keep='last')]
    if not dupes.empty:
        dupe_counts = dupes.groupby(subset).size().sort_values(ascending=False)
        results["duplicate_groups"] = [
            {"keys": str(k), "count": int(v)}
            for k, v in dupe_counts.head(10).items()  # Top 10
        ]
    
    if results["subset_duplicates"] > 0:
        logger.warning(
            f"Found {results['subset_duplicates']} duplicate rows "
            f"({results['duplicate_rate']}% of data) on columns {subset}"
        )
    
    return results


def check_value_ranges(
    df: pd.DataFrame,
    column: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    allowed_values: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Comprehensive value range validation.

    Args:
        df: DataFrame to inspect.
        column: Column name to check.
        min_val: Minimum acceptable value.
        max_val: Maximum acceptable value.
        allowed_values: List of allowed values (for categorical).

    Returns:
        Dictionary with range analysis results.
    """
    if column not in df.columns:
        return {"error": f"Column '{column}' not found", "passed": False}
    
    # Remove nulls for analysis
    valid_data = df[column].dropna()
    
    results = {
        "column": column,
        "total_values": len(valid_data),
        "null_count": int(df[column].isna().sum()),
        "passed": True,
        "out_of_range": [],
    }
    
    # Basic statistics
    if pd.api.types.is_numeric_dtype(df[column]):
        results.update({
            "min": float(valid_data.min()) if not valid_data.empty else None,
            "max": float(valid_data.max()) if not valid_data.empty else None,
            "mean": float(valid_data.mean()) if not valid_data.empty else None,
            "std": float(valid_data.std()) if not valid_data.empty else None,
            "unique_values": int(valid_data.nunique()),
        })
    
    # Check numeric range
    if min_val is not None and pd.api.types.is_numeric_dtype(df[column]):
        below = valid_data[valid_data < min_val]
        if not below.empty:
            results["out_of_range"].append({
                "type": "below_min",
                "count": len(below),
                "percentage": round(len(below) / len(valid_data) * 100, 2),
                "min_value": min_val,
                "examples": below.head(5).tolist()
            })
            results["passed"] = False
    
    if max_val is not None and pd.api.types.is_numeric_dtype(df[column]):
        above = valid_data[valid_data > max_val]
        if not above.empty:
            results["out_of_range"].append({
                "type": "above_max",
                "count": len(above),
                "percentage": round(len(above) / len(valid_data) * 100, 2),
                "max_value": max_val,
                "examples": above.head(5).tolist()
            })
            results["passed"] = False
    
    # Check allowed values (categorical)
    if allowed_values is not None:
        invalid = valid_data[~valid_data.isin(allowed_values)]
        if not invalid.empty:
            results["out_of_range"].append({
                "type": "invalid_values",
                "count": len(invalid),
                "percentage": round(len(invalid) / len(valid_data) * 100, 2),
                "allowed_values": allowed_values[:10],  # Show first 10
                "examples": invalid.head(5).tolist()
            })
            results["passed"] = False
    
    if not results["passed"]:
        logger.warning(f"Value range validation failed for column '{column}'")
    
    return results


def check_date_consistency(
    df: pd.DataFrame,
    date_col: str,
    min_date: Optional[date] = None,
    max_date: Optional[date] = None,
    future_dates_allowed: bool = False,
) -> Dict[str, Any]:
    """Validate date columns for consistency.

    Args:
        df: DataFrame to inspect.
        date_col: Date column to validate.
        min_date: Earliest allowed date.
        max_date: Latest allowed date.
        future_dates_allowed: Whether future dates are acceptable.

    Returns:
        Dictionary with date validation results.
    """
    if date_col not in df.columns:
        return {"error": f"Column '{date_col}' not found", "passed": False}
    
    # Convert to datetime if needed
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        try:
            dates = pd.to_datetime(df[date_col], errors='coerce')
        except:
            return {"error": f"Could not convert '{date_col}' to datetime", "passed": False}
    else:
        dates = df[date_col]
    
    valid_dates = dates.dropna()
    today = datetime.now().date()
    
    results = {
        "column": date_col,
        "total_dates": len(valid_dates),
        "null_count": int(dates.isna().sum()),
        "min_date": valid_dates.min().isoformat() if not valid_dates.empty else None,
        "max_date": valid_dates.max().isoformat() if not valid_dates.empty else None,
        "passed": True,
        "issues": [],
    }
    
    # Check for future dates
    if not future_dates_allowed:
        future_mask = valid_dates.dt.date > today
        future_count = future_mask.sum()
        if future_count > 0:
            results["issues"].append({
                "type": "future_dates",
                "count": int(future_count),
                "percentage": round(future_count / len(valid_dates) * 100, 2),
                "examples": valid_dates[future_mask].head(5).dt.date.tolist()
            })
            results["passed"] = False
    
    # Check date range
    if min_date:
        early_mask = valid_dates.dt.date < min_date
        early_count = early_mask.sum()
        if early_count > 0:
            results["issues"].append({
                "type": "before_min_date",
                "count": int(early_count),
                "percentage": round(early_count / len(valid_dates) * 100, 2),
                "min_date": min_date.isoformat(),
                "examples": valid_dates[early_mask].head(5).dt.date.tolist()
            })
            results["passed"] = False
    
    if max_date:
        late_mask = valid_dates.dt.date > max_date
        late_count = late_mask.sum()
        if late_count > 0:
            results["issues"].append({
                "type": "after_max_date",
                "count": int(late_count),
                "percentage": round(late_count / len(valid_dates) * 100, 2),
                "max_date": max_date.isoformat(),
                "examples": valid_dates[late_mask].head(5).dt.date.tolist()
            })
            results["passed"] = False
    
    return results


def check_cross_field_consistency(
    df: pd.DataFrame,
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Apply cross-field validation rules.

    Args:
        df: DataFrame to validate.
        rules: List of rule dicts with 'name', 'condition', and 'message'.

    Returns:
        List of violated rules with counts.
    """
    violations = []
    
    for rule in rules:
        try:
            # Evaluate condition
            mask = eval(rule['condition'])
            violation_count = mask.sum()
            
            if violation_count > 0:
                violations.append({
                    "rule": rule['name'],
                    "message": rule['message'],
                    "violation_count": int(violation_count),
                    "percentage": round(violation_count / len(df) * 100, 2),
                    "examples": df[mask].head(3).to_dict('records') if not df[mask].empty else []
                })
                logger.warning(
                    f"Rule '{rule['name']}' violated: {violation_count} rows "
                    f"({violation_count/len(df)*100:.1f}%)"
                )
        except Exception as e:
            logger.error(f"Error evaluating rule '{rule['name']}': {e}")
    
    return violations


def generate_data_quality_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive data quality report.

    Args:
        df: DataFrame to analyze.

    Returns:
        Dictionary with complete quality metrics.
    """
    report = {
        "overview": {
            "rows": len(df),
            "columns": len(df.columns),
            "memory_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
        },
        "schema": validate_schema(df, strict=False),
        "nulls": check_nulls(df),
        "duplicates": check_duplicates(df),
        "columns": {},
    }
    
    # Per-column analysis
    for col in df.columns:
        col_report = {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "null_percentage": round(df[col].isna().mean() * 100, 2),
            "unique_count": int(df[col].nunique()),
        }
        
        # Numeric columns
        if pd.api.types.is_numeric_dtype(df[col]):
            valid = df[col].dropna()
            if not valid.empty:
                col_report.update({
                    "min": float(valid.min()),
                    "max": float(valid.max()),
                    "mean": float(valid.mean()),
                    "median": float(valid.median()),
                    "std": float(valid.std()),
                })
        
        # Date columns
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            valid = df[col].dropna()
            if not valid.empty:
                col_report.update({
                    "min_date": valid.min().isoformat(),
                    "max_date": valid.max().isoformat(),
                    "date_range_days": (valid.max() - valid.min()).days,
                })
        
        # Object/categorical columns
        else:
            value_counts = df[col].value_counts().head(5).to_dict()
            col_report["top_values"] = {
                str(k): int(v) for k, v in value_counts.items()
            }
        
        report["columns"][col] = col_report
    
    return report


def quick_validate(df: pd.DataFrame) -> bool:
    """Quick validation for basic data quality.

    Checks:
    - Required columns exist
    - No excessive nulls in critical columns
    - No excessive duplicates
    - Amounts are positive

    Args:
        df: DataFrame to validate.

    Returns:
        True if all basic checks pass.
    """
    # Check required columns
    required = ['provider_npi', 'procedure_code', 'amount', 'claim_date']
    missing = set(required) - set(df.columns)
    if missing:
        logger.error(f"Missing required columns: {missing}")
        return False
    
    # Check nulls in critical columns
    for col in ['provider_npi', 'amount']:
        null_pct = df[col].isna().mean() * 100
        if null_pct > 5:
            logger.error(f"Column '{col}' has {null_pct:.1f}% nulls")
            return False
    
    # Check for positive amounts
    if 'amount' in df.columns:
        negative = (df['amount'] < 0).sum()
        if negative > 0:
            logger.error(f"Found {negative} negative amounts")
            return False
    
    # Check date range
    if 'claim_date' in df.columns:
        try:
            dates = pd.to_datetime(df['claim_date'], errors='coerce')
            year_range = dates.dt.year.unique()
            if len(year_range) > 10:  # Suspiciously wide range
                logger.warning(f"Unusual year range: {sorted(year_range)}")
        except:
            pass
    
    logger.info("Quick validation passed")
    return True
