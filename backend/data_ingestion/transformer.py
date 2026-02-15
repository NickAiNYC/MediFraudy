"""Data transformation and cleaning utilities for Medicaid claims data.

Provides comprehensive data cleaning, normalization, and feature engineering
for fraud detection pipelines. Handles:
- NPI normalization (10-digit zero-padded)
- Date standardization
- Currency cleaning
- Categorical encoding
- Feature engineering for fraud indicators
"""

import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core cleaning functions
# ---------------------------------------------------------------------------

def normalize_npi(
    df: pd.DataFrame,
    column: str = "provider_npi",
    new_column: Optional[str] = None
) -> pd.DataFrame:
    """Normalize NPI numbers to 10-digit zero-padded strings.

    Args:
        df: DataFrame containing NPI data.
        column: Name of the NPI column.
        new_column: If provided, create new column instead of replacing.

    Returns:
        DataFrame with normalized NPI column.
    """
    target_col = new_column or column
    
    if column in df.columns:
        # Convert to string, strip, remove non-digits
        df[target_col] = (
            df[column]
            .astype(str)
            .str.strip()
            .str.replace(r"\D", "", regex=True)  # Remove non-digits
            .str.zfill(10)  # Zero-pad to 10 digits
        )
        
        # Log invalid NPIs (not 10 digits)
        invalid_mask = df[target_col].str.len() != 10
        if invalid_mask.any():
            invalid_count = invalid_mask.sum()
            logger.warning(f"Found {invalid_count} invalid NPIs (not 10 digits)")
            
            # Replace invalid with NaN
            df.loc[invalid_mask, target_col] = pd.NA
    
    return df


def normalize_state(
    df: pd.DataFrame,
    column: str = "provider_state",
    new_column: Optional[str] = None
) -> pd.DataFrame:
    """Normalize state codes to uppercase 2-letter abbreviations.

    Args:
        df: DataFrame containing state data.
        column: Name of the state column.
        new_column: If provided, create new column instead of replacing.

    Returns:
        DataFrame with normalized state column.
    """
    target_col = new_column or column
    
    if column in df.columns:
        # Convert to string, strip, uppercase, take first 2 chars
        df[target_col] = (
            df[column]
            .astype(str)
            .str.strip()
            .str.upper()
            .str[:2]
        )
        
        # US state codes (for validation)
        us_states = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
            'DC', 'PR', 'VI', 'GU', 'MP', 'AS'
        }
        
        # Flag invalid states
        invalid_mask = ~df[target_col].isin(us_states)
        if invalid_mask.any():
            invalid_count = invalid_mask.sum()
            logger.warning(f"Found {invalid_count} invalid state codes")
    
    return df


def clean_currency(
    df: pd.DataFrame,
    column: str = "amount",
    new_column: Optional[str] = None
) -> pd.DataFrame:
    """Remove currency symbols and convert to float.

    Args:
        df: DataFrame containing monetary data.
        column: Name of the amount column.
        new_column: If provided, create new column instead of replacing.

    Returns:
        DataFrame with cleaned currency column.
    """
    target_col = new_column or column
    
    if column in df.columns:
        # Convert to string, remove currency symbols and commas
        df[target_col] = (
            df[column]
            .astype(str)
            .str.replace(r"[$,\s]", "", regex=True)
            .str.replace(r"[()]", "-", regex=True)  # Handle parentheses for negatives
            .str.strip()
        )
        
        # Convert to numeric
        df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
        
        # Log issues
        invalid_mask = df[target_col].isna() & df[column].notna()
        if invalid_mask.any():
            invalid_count = invalid_mask.sum()
            logger.warning(f"Could not parse {invalid_count} currency values in column '{column}'")
    
    return df


def normalize_dates(
    df: pd.DataFrame,
    column: str,
    new_column: Optional[str] = None,
    format: Optional[str] = None,
    errors: str = 'coerce'
) -> pd.DataFrame:
    """Normalize date columns to datetime.

    Args:
        df: DataFrame containing date data.
        column: Name of the date column.
        new_column: If provided, create new column instead of replacing.
        format: Expected date format (e.g., '%Y-%m-%d').
        errors: How to handle parsing errors ('coerce', 'raise', 'ignore').

    Returns:
        DataFrame with normalized date column.
    """
    target_col = new_column or column
    
    if column in df.columns:
        # Parse dates
        if format:
            df[target_col] = pd.to_datetime(df[column], format=format, errors=errors)
        else:
            df[target_col] = pd.to_datetime(df[column], errors=errors)
        
        # Log issues
        if errors == 'coerce':
            invalid_mask = df[target_col].isna() & df[column].notna()
            if invalid_mask.any():
                invalid_count = invalid_mask.sum()
                logger.warning(f"Could not parse {invalid_count} dates in column '{column}'")
    
    return df


def clean_categorical(
    df: pd.DataFrame,
    column: str,
    new_column: Optional[str] = None,
    lowercase: bool = True,
    strip: bool = True,
    replace_missing: Optional[str] = None
) -> pd.DataFrame:
    """Clean categorical/text columns.

    Args:
        df: DataFrame containing categorical data.
        column: Name of the column to clean.
        new_column: If provided, create new column instead of replacing.
        lowercase: Convert to lowercase.
        strip: Strip whitespace.
        replace_missing: Value to replace missing/empty with.

    Returns:
        DataFrame with cleaned categorical column.
    """
    target_col = new_column or column
    
    if column in df.columns:
        # Convert to string
        df[target_col] = df[column].astype(str)
        
        # Clean
        if strip:
            df[target_col] = df[target_col].str.strip()
        
        if lowercase:
            df[target_col] = df[target_col].str.lower()
        
        # Handle missing
        if replace_missing is not None:
            df[target_col] = df[target_col].replace(['nan', 'none', ''], replace_missing)
    
    return df


# ---------------------------------------------------------------------------
# Filtering functions
# ---------------------------------------------------------------------------

def filter_state(
    df: pd.DataFrame,
    state: str = "NY",
    column: str = "provider_state"
) -> pd.DataFrame:
    """Filter DataFrame to a single state.

    Args:
        df: DataFrame to filter.
        state: Two-letter state code.
        column: Name of the state column.

    Returns:
        Filtered DataFrame.
    """
    if column in df.columns:
        filtered = df[df[column] == state].copy()
        logger.info(f"Filtered to {state}: {len(filtered)} rows from {len(df)}")
        return filtered
    else:
        logger.warning(f"State column '{column}' not found, returning original")
        return df.copy()


def filter_date_range(
    df: pd.DataFrame,
    date_column: str,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None
) -> pd.DataFrame:
    """Filter DataFrame to a date range.

    Args:
        df: DataFrame to filter.
        date_column: Name of the date column.
        start_date: Start date (inclusive).
        end_date: End date (inclusive).

    Returns:
        Filtered DataFrame.
    """
    if date_column not in df.columns:
        logger.warning(f"Date column '{date_column}' not found")
        return df.copy()
    
    # Ensure datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
        df = normalize_dates(df, date_column)
    
    filtered = df.copy()
    
    if start_date:
        start = pd.to_datetime(start_date)
        filtered = filtered[filtered[date_column] >= start]
    
    if end_date:
        end = pd.to_datetime(end_date)
        filtered = filtered[filtered[date_column] <= end]
    
    logger.info(f"Date filter applied: {len(filtered)} rows from {len(df)}")
    return filtered


def filter_billing_codes(
    df: pd.DataFrame,
    codes: List[str],
    column: str = "procedure_code",
    exclude: bool = False
) -> pd.DataFrame:
    """Filter DataFrame to specific billing codes.

    Args:
        df: DataFrame to filter.
        codes: List of billing codes to include/exclude.
        column: Name of the code column.
        exclude: If True, exclude these codes instead of include.

    Returns:
        Filtered DataFrame.
    """
    if column not in df.columns:
        logger.warning(f"Code column '{column}' not found")
        return df.copy()
    
    if exclude:
        filtered = df[~df[column].isin(codes)].copy()
        logger.info(f"Excluded {len(codes)} codes: {len(filtered)} rows remaining")
    else:
        filtered = df[df[column].isin(codes)].copy()
        logger.info(f"Filtered to {len(codes)} codes: {len(filtered)} rows")
    
    return filtered


# ---------------------------------------------------------------------------
# Feature engineering for fraud detection
# ---------------------------------------------------------------------------

def add_date_features(
    df: pd.DataFrame,
    date_column: str,
    features: Optional[List[str]] = None
) -> pd.DataFrame:
    """Add derived date features for fraud detection.

    Features:
    - year, month, day, dayofweek, quarter
    - is_weekend, is_holiday (simplified)
    - days_since_previous_claim (grouped by provider)

    Args:
        df: DataFrame with date column.
        date_column: Name of the date column.
        features: List of features to add (default: all).

    Returns:
        DataFrame with added date features.
    """
    if date_column not in df.columns:
        logger.warning(f"Date column '{date_column}' not found")
        return df
    
    # Ensure datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
        df = normalize_dates(df, date_column)
    
    feature_map = {
        'year': lambda d: d.dt.year,
        'month': lambda d: d.dt.month,
        'day': lambda d: d.dt.day,
        'dayofweek': lambda d: d.dt.dayofweek,
        'quarter': lambda d: d.dt.quarter,
        'is_weekend': lambda d: (d.dt.dayofweek >= 5).astype(int),
        'week': lambda d: d.dt.isocalendar().week,
    }
    
    if features is None:
        features = list(feature_map.keys())
    
    for feature in features:
        if feature in feature_map:
            col_name = f"{date_column}_{feature}"
            df[col_name] = feature_map[feature](df[date_column])
    
    return df


def add_claim_features(
    df: pd.DataFrame,
    group_by: List[str] = ['provider_npi'],
    date_column: str = 'claim_date'
) -> pd.DataFrame:
    """Add claim-level features for fraud detection.

    Features:
    - claim_count_by_provider (rolling)
    - days_since_last_claim
    - claims_per_day
    - avg_claim_amount_rolling

    Args:
        df: DataFrame with claims data.
        group_by: Columns to group by (usually provider).
        date_column: Date column for ordering.

    Returns:
        DataFrame with added claim features.
    """
    if date_column not in df.columns:
        logger.warning(f"Date column '{date_column}' not found")
        return df
    
    # Ensure datetime and sort
    if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
        df = normalize_dates(df, date_column)
    
    df = df.sort_values([*group_by, date_column])
    
    # Rolling claim count
    for group in group_by:
        df[f'{group}_claim_count'] = df.groupby(group).cumcount() + 1
    
    # Days since last claim
    if len(group_by) == 1:
        df['days_since_last_claim'] = (
            df.groupby(group_by[0])[date_column]
            .diff()
            .dt.days
        )
    
    # Rolling average amount (last 5 claims)
    if 'amount' in df.columns and len(group_by) == 1:
        df['avg_amount_last_5'] = (
            df.groupby(group_by[0])['amount']
            .transform(lambda x: x.rolling(5, min_periods=1).mean())
        )
    
    return df


def add_kickback_features(
    df: pd.DataFrame,
    beneficiary_col: str = 'beneficiary_id',
    provider_col: str = 'provider_npi',
    date_col: str = 'claim_date'
) -> pd.DataFrame:
    """Add features for kickback detection.

    Features:
    - beneficiary_claim_count (total per provider)
    - beneficiary_concentration_score
    - days_between_claims_per_beneficiary

    Args:
        df: DataFrame with claims.
        beneficiary_col: Beneficiary identifier column.
        provider_col: Provider identifier column.
        date_col: Date column.

    Returns:
        DataFrame with added kickback features.
    """
    if not all(col in df.columns for col in [beneficiary_col, provider_col]):
        logger.warning("Missing beneficiary or provider columns")
        return df
    
    # Count claims per beneficiary per provider
    claim_counts = df.groupby([provider_col, beneficiary_col]).size().reset_index(name='beneficiary_claim_count')
    df = df.merge(claim_counts, on=[provider_col, beneficiary_col])
    
    # Calculate concentration score (how many beneficiaries account for most claims)
    provider_stats = df.groupby(provider_col).agg({
        beneficiary_col: 'nunique',
        'beneficiary_claim_count': 'sum'
    }).reset_index()
    
    provider_stats['avg_claims_per_beneficiary'] = (
        provider_stats['beneficiary_claim_count'] / provider_stats[beneficiary_col]
    )
    
    df = df.merge(
        provider_stats[[provider_col, 'avg_claims_per_beneficiary']],
        on=provider_col
    )
    
    # Flag high-concentration beneficiaries
    df['high_concentration'] = (
        df['beneficiary_claim_count'] > df['avg_claims_per_beneficiary'] * 3
    ).astype(int)
    
    return df


def add_capacity_features(
    df: pd.DataFrame,
    provider_col: str = 'provider_npi',
    date_col: str = 'claim_date',
    capacity_col: Optional[str] = None
) -> pd.DataFrame:
    """Add features for capacity violation detection.

    Features:
    - patients_per_day (unique beneficiaries)
    - claims_per_day
    - capacity_violation_flag (if capacity data available)

    Args:
        df: DataFrame with claims.
        provider_col: Provider identifier.
        date_col: Date column.
        capacity_col: Column with licensed capacity (if available).

    Returns:
        DataFrame with added capacity features.
    """
    if date_col not in df.columns:
        return df
    
    # Ensure date
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df = normalize_dates(df, date_col)
    
    # Daily patient counts
    daily_patients = df.groupby(
        [provider_col, df[date_col].dt.date]
    )[beneficiary_col].nunique().reset_index()
    daily_patients.columns = [provider_col, 'service_date', 'patients_per_day']
    
    df = df.merge(daily_patients, on=[provider_col], how='left')
    
    # Capacity violation flag
    if capacity_col and capacity_col in df.columns:
        df['capacity_violation'] = (
            df['patients_per_day'] > df[capacity_col]
        ).astype(int)
    
    return df


# ---------------------------------------------------------------------------
# Complete transformation pipeline
# ---------------------------------------------------------------------------

def transform_medicaid_data(
    df: pd.DataFrame,
    state: Optional[str] = "NY",
    add_fraud_features: bool = True
) -> pd.DataFrame:
    """Complete transformation pipeline for Medicaid claims data.

    Args:
        df: Raw DataFrame.
        state: Filter to this state (None for all).
        add_fraud_features: Whether to add fraud detection features.

    Returns:
        Transformed DataFrame ready for analysis.
    """
    logger.info(f"Starting transformation: {len(df)} rows")
    
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # Standardize column names (if needed)
    df.columns = [col.lower().strip() for col in df.columns]
    
    # Core cleaning
    if 'provider_npi' in df.columns:
        df = normalize_npi(df, 'provider_npi')
    
    if 'provider_state' in df.columns:
        df = normalize_state(df, 'provider_state')
    elif 'state' in df.columns:
        df = normalize_state(df, 'state', 'provider_state')
    
    if 'amount' in df.columns:
        df = clean_currency(df, 'amount')
    
    # Date normalization
    for date_col in ['claim_date', 'submitted_date']:
        if date_col in df.columns:
            df = normalize_dates(df, date_col)
            df = add_date_features(df, date_col, ['year', 'month', 'is_weekend'])
    
    # Filter to target state
    if state and 'provider_state' in df.columns:
        df = filter_state(df, state)
    
    # Add fraud detection features
    if add_fraud_features:
        if 'beneficiary_id' in df.columns:
            df = add_kickback_features(df)
        
        if all(col in df.columns for col in ['provider_npi', 'claim_date']):
            df = add_claim_features(df)
        
        if 'licensed_capacity' in df.columns:
            # This would need provider-level capacity data merged in
            pass
    
    logger.info(f"Transformation complete: {len(df)} rows, {len(df.columns)} columns")
    return df
