"""Data loader: download, parse, chunk, and validate large datasets."""

import hashlib
import logging
import os
import zipfile
from typing import Generator, Optional, Union

import pandas as pd
import requests
from tqdm import tqdm

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


class MedicaidDataLoader:
    """Enhanced data loader with automatic download and verification.
    
    Supports:
    - Automatic download from URL if file doesn't exist
    - SHA-256 checksum verification
    - Progress bar for downloads
    - Auto-detection of zip/csv/parquet formats
    
    Example:
        loader = MedicaidDataLoader(
            file_path="data/medicaid_claims.zip",
            url="https://example.com/data.zip",
            expected_checksum="abc123..."
        )
        df = loader.ensure_data()
    """
    
    def __init__(
        self,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        expected_checksum: Optional[str] = None
    ):
        """Initialize the loader.
        
        Args:
            file_path: Path where the dataset should be stored
            url: URL to download from if file doesn't exist
            expected_checksum: Expected SHA-256 checksum for verification
        """
        self.file_path = file_path or os.getenv(
            "MEDICAID_DATASET_PATH",
            "data/medicaid_claims.zip"
        )
        self.url = url
        self.expected_checksum = expected_checksum
        
    def ensure_data(self) -> pd.DataFrame:
        """Download if not exists, verify checksum, and load data.
        
        Returns:
            DataFrame with the loaded data
            
        Raises:
            RuntimeError: If download fails
            ValueError: If checksum verification fails
            FileNotFoundError: If file doesn't exist and no URL provided
        """
        # Download if necessary
        if not os.path.exists(self.file_path):
            if not self.url:
                raise FileNotFoundError(
                    f"Dataset not found at {self.file_path} and no URL provided"
                )
            logger.info("Dataset not found locally, downloading from %s", self.url)
            self._download_file()
        else:
            logger.info("Dataset found at %s", self.file_path)
        
        # Verify checksum if provided
        if self.expected_checksum:
            logger.info("Verifying checksum...")
            self._verify_checksum()
        
        # Load and return data
        return detect_and_load(self.file_path)
    
    def _download_file(self) -> None:
        """Stream download with progress bar.
        
        Raises:
            RuntimeError: If download fails
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path) or ".", exist_ok=True)
        
        try:
            response = requests.get(self.url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            logger.info("Downloading %s (%.2f GB)...", 
                       os.path.basename(self.file_path),
                       total_size / (1024**3))
            
            with open(self.file_path, 'wb') as f:
                with tqdm(
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=os.path.basename(self.file_path)
                ) as pbar:
                    for data in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                        f.write(data)
                        pbar.update(len(data))
            
            logger.info("Download complete: %s", self.file_path)
            
        except requests.RequestException as exc:
            # Clean up partial download
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
            raise RuntimeError(f"Failed to download dataset: {exc}") from exc
    
    def _verify_checksum(self) -> None:
        """Verify SHA-256 checksum of downloaded file.
        
        Raises:
            ValueError: If checksum doesn't match
        """
        logger.info("Computing SHA-256 checksum...")
        
        sha256_hash = hashlib.sha256()
        with open(self.file_path, "rb") as f:
            # Read in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        actual_checksum = sha256_hash.hexdigest()
        
        if actual_checksum != self.expected_checksum:
            logger.error(
                "Checksum mismatch!\nExpected: %s\nActual:   %s",
                self.expected_checksum,
                actual_checksum
            )
            raise ValueError(
                f"Checksum verification failed. Expected {self.expected_checksum}, "
                f"got {actual_checksum}"
            )
        
        logger.info("Checksum verified: %s", actual_checksum[:16] + "...")
    
    def get_checksum(self) -> str:
        """Calculate SHA-256 checksum of the current file.
        
        Useful for getting the checksum of a newly downloaded file.
        
        Returns:
            SHA-256 checksum as hex string
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        sha256_hash = hashlib.sha256()
        with open(self.file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        checksum = sha256_hash.hexdigest()
        logger.info("Checksum for %s: %s", self.file_path, checksum)
        return checksum

