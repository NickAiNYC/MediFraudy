"""Data ingestion: download and load large CSV datasets."""

import logging
import os
from typing import Generator, Optional

import pandas as pd

from config import settings

logger = logging.getLogger(__name__)


def download_dataset(
    url: str = "",
    dest_dir: str = "data",
    filename: str = "medicaid_claims.csv",
) -> str:
    """Download a large dataset with streaming to avoid memory issues.

    Args:
        url: URL to download from. Defaults to configured MEDICAID_DATASET_URL.
        dest_dir: Directory to save the file in.
        filename: Name for the saved file.

    Returns:
        Path to the downloaded file.

    Raises:
        RuntimeError: If the download fails.
    """
    import httpx

    url = url or settings.MEDICAID_DATASET_URL
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)

    if os.path.exists(dest_path):
        logger.info("Dataset already exists at %s, skipping download", dest_path)
        return dest_path

    logger.info("Downloading dataset from %s", url)
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=600) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to download dataset: {exc}") from exc

    logger.info("Dataset saved to %s", dest_path)
    return dest_path


def load_csv_chunks(
    filepath: str,
    chunk_size: Optional[int] = None,
) -> Generator[pd.DataFrame, None, None]:
    """Load a CSV file in chunks for memory-efficient processing.

    Args:
        filepath: Path to the CSV file.
        chunk_size: Number of rows per chunk. Defaults to settings.CHUNK_SIZE.

    Yields:
        DataFrame chunks.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset file not found: {filepath}")

    logger.info("Loading CSV in chunks of %d from %s", chunk_size, filepath)
    for chunk in pd.read_csv(filepath, chunksize=chunk_size, low_memory=False):
        yield chunk


def validate_schema(df: pd.DataFrame, required_columns: list[str]) -> bool:
    """Check that a DataFrame contains all required columns.

    Args:
        df: DataFrame to validate.
        required_columns: List of column names that must be present.

    Returns:
        True if all required columns are present.

    Raises:
        ValueError: If any required column is missing.
    """
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return True
