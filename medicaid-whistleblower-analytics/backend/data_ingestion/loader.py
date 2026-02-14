"""Data loader: download, parse, chunk, and validate large datasets."""

import logging
import os
import zipfile
from typing import Generator, Optional, Union

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


def _load_data(source: Union[str, "zipfile.ZipExtFile"]) -> pd.DataFrame:
    """Load a CSV or Parquet file into a DataFrame.

    Args:
        source: File path (str) or an open file handle from a zip archive.

    Returns:
        DataFrame with the loaded data.
    """
    if isinstance(source, str) and source.endswith(".parquet"):
        return pd.read_parquet(source)
    return pd.read_csv(source, low_memory=False)


def detect_and_load(file_path: str) -> pd.DataFrame:
    """Auto-detect if a file is zipped and load the first data file inside.

    Supports ``.zip`` archives containing CSV or Parquet files, as well as
    plain CSV and Parquet files.

    Args:
        file_path: Path to the dataset file (zip, csv, or parquet).

    Returns:
        DataFrame with the loaded data.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If a zip archive contains no loadable data files.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    if file_path.endswith(".zip"):
        logger.info("Detected zip archive: %s", file_path)
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            data_files = [
                f
                for f in zip_ref.namelist()
                if f.endswith(".csv") or f.endswith(".parquet")
            ]
            if not data_files:
                raise ValueError(f"No CSV or Parquet files found in {file_path}")
            logger.info("Loading %s from archive", data_files[0])
            with zip_ref.open(data_files[0]) as f:
                return _load_data(f)

    logger.info("Loading file directly: %s", file_path)
    return _load_data(file_path)
