"""Data transformation and cleaning utilities."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def normalize_npi(df: pd.DataFrame, column: str = "npi") -> pd.DataFrame:
    """Normalize NPI numbers to 10-digit zero-padded strings.

    Args:
        df: DataFrame containing NPI data.
        column: Name of the NPI column.

    Returns:
        DataFrame with normalized NPI column.
    """
    if column in df.columns:
        df[column] = df[column].astype(str).str.strip().str.zfill(10)
    return df


def normalize_state(df: pd.DataFrame, column: str = "state") -> pd.DataFrame:
    """Normalize state codes to uppercase 2-letter abbreviations.

    Args:
        df: DataFrame containing state data.
        column: Name of the state column.

    Returns:
        DataFrame with normalized state column.
    """
    if column in df.columns:
        df[column] = df[column].astype(str).str.strip().str.upper().str[:2]
    return df


def clean_currency(df: pd.DataFrame, column: str = "amount") -> pd.DataFrame:
    """Remove currency symbols and convert to float.

    Args:
        df: DataFrame containing monetary data.
        column: Name of the amount column.

    Returns:
        DataFrame with cleaned currency column.
    """
    if column in df.columns:
        df[column] = (
            df[column]
            .astype(str)
            .str.replace(r"[$,]", "", regex=True)
            .str.strip()
        )
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def filter_state(df: pd.DataFrame, state: str = "NY", column: str = "state") -> pd.DataFrame:
    """Filter DataFrame to a single state.

    Args:
        df: DataFrame to filter.
        state: Two-letter state code.
        column: Name of the state column.

    Returns:
        Filtered DataFrame.
    """
    if column in df.columns:
        return df[df[column] == state].copy()
    return df
