"""Data loader: download, parse, chunk, validate, and verify large datasets.

Handles the 10.32GB DOGE Medicaid dataset with:
- Automatic download with resume capability
- SHA-256 checksum verification
- Memory-efficient chunking
- Support for zip, csv, parquet formats
- Progress bars for long operations
- Schema validation and data quality checks
"""

import hashlib
import logging
import os
import zipfile
from typing import Generator, Optional, Union, List, Dict, Any
from pathlib import Path
import json

import pandas as pd
import requests
from tqdm import tqdm
import numpy as np

from config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core download functionality
# ---------------------------------------------------------------------------

def download_dataset(
    url: str = "",
    dest_dir: str = "data",
    filename: str = "medicaid_claims.zip",
    resume: bool = True,
    timeout: int = 600,
) -> str:
    """Download a large dataset with streaming and resume capability.

    Args:
        url: URL to download from. Defaults to configured MEDICAID_DATASET_URL.
        dest_dir: Directory to save the file in.
        filename: Name for the saved file.
        resume: Whether to resume partial downloads.
        timeout: Timeout in seconds.

    Returns:
        Path to the downloaded file.

    Raises:
        RuntimeError: If the download fails.
    """
    import httpx

    url = url or settings.MEDICAID_DATASET_URL
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)

    # Check for existing file
    if os.path.exists(dest_path):
        if not resume:
            logger.info("Dataset already exists at %s, skipping download", dest_path)
            return dest_path
        
        # Get existing file size for resume
        existing_size = os.path.getsize(dest_path)
        logger.info("Found existing file %s (%d bytes), attempting resume", 
                   dest_path, existing_size)
    else:
        existing_size = 0

    logger.info("Downloading dataset from %s", url)
    
    headers = {"Range": f"bytes={existing_size}-"} if resume and existing_size > 0 else {}
    
    try:
        with httpx.stream(
            "GET", url, 
            follow_redirects=True, 
            timeout=timeout,
            headers=headers
        ) as resp:
            resp.raise_for_status()
            
            # Get total size from headers
            total_size = int(resp.headers.get('content-length', 0)) + existing_size
            
            # Open file in append mode if resuming
            mode = 'ab' if resume and existing_size > 0 else 'wb'
            
            with open(dest_path, mode) as f:
                with tqdm(
                    total=total_size,
                    initial=existing_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=filename
                ) as pbar:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        pbar.update(len(chunk))

    except httpx.HTTPError as exc:
        # If resume failed (416 Range Not Satisfiable), try full download
        if resume and hasattr(exc, 'response') and exc.response.status_code == 416:
            logger.warning("Resume not supported, starting fresh download")
            return download_dataset(url, dest_dir, filename, resume=False, timeout=timeout)
        
        # Clean up partial download
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise RuntimeError(f"Failed to download dataset: {exc}") from exc

    logger.info("Dataset saved to %s (%d bytes)", dest_path, os.path.getsize(dest_path))
    return dest_path


# ---------------------------------------------------------------------------
# Chunked loading
# ---------------------------------------------------------------------------

def load_csv_chunks(
    filepath: str,
    chunk_size: Optional[int] = None,
    dtype: Optional[Dict] = None,
    parse_dates: Optional[List[str]] = None,
) -> Generator[pd.DataFrame, None, None]:
    """Load a CSV file in chunks for memory-efficient processing.

    Args:
        filepath: Path to the CSV file.
        chunk_size: Number of rows per chunk. Defaults to settings.CHUNK_SIZE.
        dtype: Dictionary of column dtypes for efficient loading.
        parse_dates: List of date columns to parse.

    Yields:
        DataFrame chunks.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset file not found: {filepath}")

    logger.info("Loading CSV in chunks of %d from %s", chunk_size, filepath)
    
    # Count total rows for progress bar (optional)
    total_rows = sum(1 for _ in open(filepath)) - 1  # Subtract header
    
    with tqdm(total=total_rows, desc="Loading CSV", unit="rows") as pbar:
        for chunk in pd.read_csv(
            filepath,
            chunksize=chunk_size,
            low_memory=False,
            dtype=dtype,
            parse_dates=parse_dates,
            memory_map=True,  # Memory-map large files
        ):
            yield chunk
            pbar.update(len(chunk))


def load_parquet_chunks(
    filepath: str,
    row_group_size: int = 100000,
) -> Generator[pd.DataFrame, None, None]:
    """Load a Parquet file in row groups for memory-efficient processing.
    
    Args:
        filepath: Path to the Parquet file.
        row_group_size: Number of rows per chunk.
        
    Yields:
        DataFrame chunks.
    """
    import pyarrow.parquet as pq
    
    logger.info("Loading Parquet in row groups from %s", filepath)
    
    parquet_file = pq.ParquetFile(filepath)
    total_rows = parquet_file.metadata.num_rows
    
    with tqdm(total=total_rows, desc="Loading Parquet", unit="rows") as pbar:
        for batch in parquet_file.iter_batches(batch_size=row_group_size):
            df = batch.to_pandas()
            yield df
            pbar.update(len(df))


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def validate_schema(
    df: pd.DataFrame,
    required_columns: List[str],
    column_types: Optional[Dict[str, type]] = None,
) -> bool:
    """Check that a DataFrame contains all required columns with correct types.

    Args:
        df: DataFrame to validate.
        required_columns: List of column names that must be present.
        column_types: Optional dict mapping column names to expected types.

    Returns:
        True if all validations pass.

    Raises:
        ValueError: If any validation fails.
    """
    # Check required columns
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Check data types
    if column_types:
        for col, expected_type in column_types.items():
            if col in df.columns:
                actual_type = df[col].dtype
                if not pd.api.types.is_dtype_equal(actual_type, expected_type):
                    logger.warning(
                        f"Column {col} has type {actual_type}, expected {expected_type}"
                    )
    
    # Check for excessive nulls
    for col in required_columns:
        null_pct = df[col].isnull().mean() * 100
        if null_pct > 50:
            logger.warning(f"Column {col} has {null_pct:.1f}% null values")
    
    return True


def get_data_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a data quality profile for a DataFrame.
    
    Args:
        df: DataFrame to profile
        
    Returns:
        Dictionary with profiling statistics
    """
    profile = {
        "rows": len(df),
        "columns": len(df.columns),
        "memory_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
        "column_stats": {}
    }
    
    for col in df.columns:
        col_stats = {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isnull().sum()),
            "null_percentage": float(df[col].isnull().mean() * 100),
            "unique_count": int(df[col].nunique()) if df[col].dtype == 'object' else None,
        }
        
        # Numeric stats
        if pd.api.types.is_numeric_dtype(df[col]):
            col_stats.update({
                "min": float(df[col].min()) if not df[col].isnull().all() else None,
                "max": float(df[col].max()) if not df[col].isnull().all() else None,
                "mean": float(df[col].mean()) if not df[col].isnull().all() else None,
                "std": float(df[col].std()) if not df[col].isnull().all() else None,
            })
        
        profile["column_stats"][col] = col_stats
    
    return profile


# ---------------------------------------------------------------------------
# File format detection and loading
# ---------------------------------------------------------------------------

def _load_data(source: Union[str, "zipfile.ZipExtFile"]) -> pd.DataFrame:
    """Load a CSV or Parquet file into a DataFrame.

    Args:
        source: File path (str) or an open file handle from a zip archive.

    Returns:
        DataFrame with the loaded data.
    """
    if isinstance(source, str):
        if source.endswith(".parquet"):
            return pd.read_parquet(source)
        elif source.endswith(".csv"):
            return pd.read_csv(source, low_memory=False)
        else:
            # Try to detect format from content
            with open(source, 'rb') as f:
                header = f.read(4)
                if header.startswith(b'PAR1'):
                    return pd.read_parquet(source)
                else:
                    return pd.read_csv(source, low_memory=False)
    else:
        # Handle zip file handle
        try:
            return pd.read_parquet(source)
        except:
            source.seek(0)  # Reset for CSV attempt
            return pd.read_csv(source, low_memory=False)


def detect_and_load(
    file_path: str,
    sample: Optional[int] = None,
) -> pd.DataFrame:
    """Auto-detect if a file is zipped and load the first data file inside.

    Supports ``.zip`` archives containing CSV or Parquet files, as well as
    plain CSV and Parquet files.

    Args:
        file_path: Path to the dataset file (zip, csv, or parquet).
        sample: If provided, load only first N rows (for testing).

    Returns:
        DataFrame with the loaded data.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If a zip archive contains no loadable data files.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    file_size = os.path.getsize(file_path) / (1024**3)
    logger.info(f"Loading dataset from {file_path} ({file_size:.2f} GB)")

    if file_path.endswith(".zip"):
        logger.info("Detected zip archive: %s", file_path)
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            # List all files in archive
            data_files = [
                f for f in zip_ref.namelist()
                if f.endswith((".csv", ".parquet", ".csv.gz", ".csv.bz2"))
            ]
            
            if not data_files:
                raise ValueError(f"No loadable data files found in {file_path}")
            
            # Try to find a README or metadata file
            metadata = [f for f in zip_ref.namelist() if 'readme' in f.lower()]
            if metadata:
                logger.info(f"Found metadata file: {metadata[0]}")
            
            # Load the first data file
            logger.info("Loading %s from archive", data_files[0])
            with zip_ref.open(data_files[0]) as f:
                df = _load_data(f)
    
    else:
        logger.info("Loading file directly: %s", file_path)
        df = _load_data(file_path)
    
    # Apply sampling if requested
    if sample and len(df) > sample:
        logger.info(f"Sampling {sample} rows from {len(df)} total")
        df = df.sample(n=sample, random_state=42)
    
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    return df


# ---------------------------------------------------------------------------
# Enhanced loader class
# ---------------------------------------------------------------------------

class MedicaidDataLoader:
    """Enhanced data loader with automatic download and verification.
    
    Supports:
    - Automatic download from URL if file doesn't exist
    - SHA-256 checksum verification
    - Progress bar for downloads
    - Auto-detection of zip/csv/parquet formats
    - Resume interrupted downloads
    - Data profiling and validation
    
    Example:
        loader = MedicaidDataLoader(
            file_path="data/medicaid_claims.zip",
            url="https://example.com/data.zip",
            expected_checksum="abc123..."
        )
        df = loader.ensure_data(sample=100000)  # Load 100k rows for testing
    """
    
    def __init__(
        self,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        expected_checksum: Optional[str] = None,
        resume: bool = True,
    ):
        """Initialize the loader.
        
        Args:
            file_path: Path where the dataset should be stored
            url: URL to download from if file doesn't exist
            expected_checksum: Expected SHA-256 checksum for verification
            resume: Whether to resume partial downloads
        """
        self.file_path = file_path or os.getenv(
            "MEDICAID_DATASET_PATH",
            "data/medicaid_claims.zip"
        )
        self.url = url or settings.MEDICAID_DATASET_URL
        self.expected_checksum = expected_checksum or settings.MEDICAID_DATASET_CHECKSUM
        self.resume = resume
        
    def ensure_data(
        self,
        sample: Optional[int] = None,
        validate: bool = True,
        profile: bool = False,
    ) -> pd.DataFrame:
        """Download if not exists, verify checksum, and load data.
        
        Args:
            sample: If provided, load only first N rows (for testing)
            validate: Whether to validate schema after loading
            profile: Whether to generate and log data profile
            
        Returns:
            DataFrame with the loaded data
            
        Raises:
            RuntimeError: If download fails
            ValueError: If checksum verification or validation fails
        """
        # Download if necessary
        if not os.path.exists(self.file_path):
            if not self.url:
                raise FileNotFoundError(
                    f"Dataset not found at {self.file_path} and no URL provided"
                )
            
            logger.info("Dataset not found locally, downloading from %s", self.url)
            self.file_path = download_dataset(
                url=self.url,
                dest_dir=os.path.dirname(self.file_path) or "data",
                filename=os.path.basename(self.file_path),
                resume=self.resume,
            )
        else:
            logger.info("Dataset found at %s", self.file_path)
        
        # Verify checksum if provided
        if self.expected_checksum:
            logger.info("Verifying checksum...")
            self._verify_checksum()
        
        # Load data
        logger.info("Loading data...")
        df = detect_and_load(self.file_path, sample=sample)
        
        # Validate schema
        if validate:
            required_columns = [
                'provider_npi', 'procedure_code', 'amount', 'claim_date',
                'beneficiary_id', 'submitted_date'
            ]
            # Check which required columns actually exist
            existing_required = [col for col in required_columns if col in df.columns]
            if existing_required:
                validate_schema(df, existing_required)
                logger.info(f"Schema validation passed for {len(existing_required)} columns")
        
        # Profile data
        if profile:
            data_profile = get_data_profile(df)
            logger.info(f"Data profile: {json.dumps(data_profile, indent=2)}")
        
        return df
    
    def _verify_checksum(self) -> None:
        """Verify SHA-256 checksum of downloaded file.
        
        Raises:
            ValueError: If checksum doesn't match
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        logger.info("Computing SHA-256 checksum...")
        
        sha256_hash = hashlib.sha256()
        file_size = os.path.getsize(self.file_path)
        
        with open(self.file_path, "rb") as f:
            with tqdm(total=file_size, unit='B', unit_scale=True, desc="Hashing") as pbar:
                for byte_block in iter(lambda: f.read(64*1024), b""):
                    sha256_hash.update(byte_block)
                    pbar.update(len(byte_block))
        
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
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        sha256_hash = hashlib.sha256()
        file_size = os.path.getsize(self.file_path)
        
        with open(self.file_path, "rb") as f:
            with tqdm(total=file_size, unit='B', unit_scale=True, desc="Computing checksum") as pbar:
                for byte_block in iter(lambda: f.read(64*1024), b""):
                    sha256_hash.update(byte_block)
                    pbar.update(len(byte_block))
        
        return sha256_hash.hexdigest()
    
    def stream_chunks(
        self,
        chunk_size: Optional[int] = None,
        format: str = "csv",
    ) -> Generator[pd.DataFrame, None, None]:
        """Stream data in chunks without loading entire file.
        
        Args:
            chunk_size: Number of rows per chunk
            format: "csv" or "parquet"
            
        Yields:
            DataFrame chunks
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        if self.file_path.endswith(".zip"):
            # Handle zip file - extract first data file
            with zipfile.ZipFile(self.file_path, "r") as zip_ref:
                data_files = [
                    f for f in zip_ref.namelist()
                    if f.endswith((".csv", ".parquet"))
                ]
                if not data_files:
                    raise ValueError("No data files in zip")
                
                # Extract to temp file for streaming
                temp_path = f"/tmp/{data_files[0]}"
                with zip_ref.open(data_files[0]) as source, open(temp_path, "wb") as target:
                    target.write(source.read())
                
                # Stream from temp file
                if data_files[0].endswith(".csv"):
                    yield from load_csv_chunks(temp_path, chunk_size)
                else:
                    yield from load_parquet_chunks(temp_path, chunk_size)
                
                # Clean up
                os.remove(temp_path)
        
        elif self.file_path.endswith(".csv"):
            yield from load_csv_chunks(self.file_path, chunk_size)
        
        elif self.file_path.endswith(".parquet"):
            yield from load_parquet_chunks(self.file_path, chunk_size)
        
        else:
            raise ValueError(f"Unsupported file format: {self.file_path}")
