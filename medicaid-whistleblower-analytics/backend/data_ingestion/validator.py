"""Data validation utilities for integrity checks."""

import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def check_nulls(df: pd.DataFrame, critical_columns: list[str]) -> dict:
    """Report null counts for critical columns.

    Args:
        df: DataFrame to inspect.
        critical_columns: Columns where nulls indicate data quality issues.

    Returns:
        Dictionary mapping column names to their null counts.
    """
    results = {}
    for col in critical_columns:
        if col in df.columns:
            null_count = int(df[col].isna().sum())
            results[col] = null_count
            if null_count > 0:
                logger.warning("Column '%s' has %d null values", col, null_count)
    return results


def check_duplicates(df: pd.DataFrame, subset: list[str]) -> int:
    """Count duplicate rows based on a subset of columns.

    Args:
        df: DataFrame to inspect.
        subset: Columns to consider when identifying duplicates.

    Returns:
        Number of duplicate rows.
    """
    dupes = int(df.duplicated(subset=subset).sum())
    if dupes > 0:
        logger.warning("Found %d duplicate rows on columns %s", dupes, subset)
    return dupes


def check_value_ranges(
    df: pd.DataFrame, column: str, min_val: float = 0, max_val: float = np.inf
) -> dict:
    """Validate that numeric values fall within an expected range.

    Args:
        df: DataFrame to inspect.
        column: Column name to check.
        min_val: Minimum acceptable value.
        max_val: Maximum acceptable value.

    Returns:
        Dictionary with counts of out-of-range values.
    """
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}

    below = int((df[column] < min_val).sum())
    above = int((df[column] > max_val).sum())
    return {"below_min": below, "above_max": above}
