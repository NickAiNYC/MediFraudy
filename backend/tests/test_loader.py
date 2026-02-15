"""Tests for data ingestion loader and validator."""

import os
import tempfile
import zipfile

import pandas as pd
import pytest

from data_ingestion.loader import load_csv_chunks, validate_schema, detect_and_load
from data_ingestion.validator import check_nulls, check_duplicates, check_value_ranges
from data_ingestion.transformer import (
    normalize_npi,
    normalize_state,
    clean_currency,
    filter_state,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_csv(tmp_path):
    """Create a small CSV file for testing."""
    path = tmp_path / "test.csv"
    path.write_text(
        "npi,name,state,amount,billing_code\n"
        "1234567890,Provider A,NY,100.50,97110\n"
        "0000000001,Provider B,NY,200.00,97530\n"
        "9876543210,Provider C,CA,50.75,99213\n"
    )
    return str(path)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "npi": ["1234567890", "1", "9876543210"],
        "name": ["Provider A", "Provider B", "Provider C"],
        "state": [" ny ", "NY", "ca"],
        "amount": ["$1,000.50", "200", "50.75"],
        "billing_code": ["97110", "97530", "99213"],
    })


# ---------------------------------------------------------------------------
# Loader tests
# ---------------------------------------------------------------------------

class TestLoadCSVChunks:
    def test_loads_all_rows(self, sample_csv):
        chunks = list(load_csv_chunks(sample_csv, chunk_size=10))
        assert len(chunks) == 1
        assert len(chunks[0]) == 3

    def test_respects_chunk_size(self, sample_csv):
        chunks = list(load_csv_chunks(sample_csv, chunk_size=2))
        assert len(chunks) == 2

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            list(load_csv_chunks("/nonexistent/path.csv"))


class TestValidateSchema:
    def test_valid_schema(self, sample_csv):
        df = pd.read_csv(sample_csv)
        assert validate_schema(df, ["npi", "name", "state"]) is True

    def test_missing_columns(self, sample_csv):
        df = pd.read_csv(sample_csv)
        with pytest.raises(ValueError, match="Missing required columns"):
            validate_schema(df, ["npi", "nonexistent_column"])


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------

class TestCheckNulls:
    def test_no_nulls(self, sample_df):
        result = check_nulls(sample_df, ["npi", "name"])
        assert result == {"npi": 0, "name": 0}

    def test_with_nulls(self):
        df = pd.DataFrame({"a": [1, None, 3], "b": [None, None, 3]})
        result = check_nulls(df, ["a", "b"])
        assert result["a"] == 1
        assert result["b"] == 2


class TestCheckDuplicates:
    def test_no_duplicates(self, sample_df):
        assert check_duplicates(sample_df, ["npi"]) == 0

    def test_with_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2]})
        assert check_duplicates(df, ["a"]) == 1


class TestCheckValueRanges:
    def test_within_range(self):
        df = pd.DataFrame({"val": [10, 20, 30]})
        result = check_value_ranges(df, "val", min_val=0, max_val=100)
        assert result == {"below_min": 0, "above_max": 0}

    def test_out_of_range(self):
        df = pd.DataFrame({"val": [-5, 20, 200]})
        result = check_value_ranges(df, "val", min_val=0, max_val=100)
        assert result == {"below_min": 1, "above_max": 1}


# ---------------------------------------------------------------------------
# Transformer tests
# ---------------------------------------------------------------------------

class TestNormalizeNPI:
    def test_pads_short_npi(self, sample_df):
        result = normalize_npi(sample_df.copy())
        assert result["npi"].iloc[1] == "0000000001"

    def test_keeps_valid_npi(self, sample_df):
        result = normalize_npi(sample_df.copy())
        assert result["npi"].iloc[0] == "1234567890"


class TestNormalizeState:
    def test_uppercases_and_trims(self, sample_df):
        result = normalize_state(sample_df.copy())
        assert result["state"].iloc[0] == "NY"
        assert result["state"].iloc[2] == "CA"


class TestCleanCurrency:
    def test_removes_symbols(self, sample_df):
        result = clean_currency(sample_df.copy())
        assert result["amount"].iloc[0] == pytest.approx(1000.50)
        assert result["amount"].iloc[1] == pytest.approx(200.0)


class TestFilterState:
    def test_filters_correctly(self):
        df = pd.DataFrame({"state": ["NY", "NY", "CA"]})
        result = filter_state(df, state="NY")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# detect_and_load tests
# ---------------------------------------------------------------------------

class TestDetectAndLoad:
    def test_loads_plain_csv(self, sample_csv):
        df = detect_and_load(sample_csv)
        assert len(df) == 3
        assert "npi" in df.columns

    def test_loads_csv_from_zip(self, tmp_path):
        csv_path = tmp_path / "inner.csv"
        csv_path.write_text(
            "npi,name,state,amount,billing_code\n"
            "1234567890,Provider A,NY,100.50,97110\n"
        )
        zip_path = str(tmp_path / "data.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(str(csv_path), "inner.csv")

        df = detect_and_load(zip_path)
        assert len(df) == 1
        assert df["npi"].iloc[0] == 1234567890

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            detect_and_load("/nonexistent/file.csv")

    def test_raises_on_empty_zip(self, tmp_path):
        zip_path = str(tmp_path / "empty.zip")
        with zipfile.ZipFile(zip_path, "w"):
            pass  # empty archive
        with pytest.raises(ValueError, match="No CSV or Parquet"):
            detect_and_load(zip_path)
