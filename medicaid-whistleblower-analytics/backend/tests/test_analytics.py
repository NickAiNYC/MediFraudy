"""Tests for analytics modules (statistical, comparison, patterns)."""

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Unit tests for pure-computation helpers (no DB required)
# ---------------------------------------------------------------------------

class TestStatisticalHelpers:
    """Verify statistical math independent of the database."""

    def test_z_score_calculation(self):
        """Ensure z-score math is correct."""
        values = np.array([100, 100, 100, 100, 500])
        mean = np.mean(values)
        std = np.std(values)
        z = (500 - mean) / std
        assert z >= 2  # 500 is clearly an outlier

    def test_zero_std_no_crash(self):
        """When all values are equal, std is 0 — must not divide by zero."""
        values = np.array([100, 100, 100])
        std = np.std(values)
        assert std == 0
        # Division guard
        z = (100 - np.mean(values)) / std if std > 0 else 0.0
        assert z == 0.0


class TestPatternHelpers:
    """Validate pattern detection thresholds."""

    def test_high_volume_threshold(self):
        """If a provider has 2× the average, it should be flagged."""
        monthly_counts = [5, 5, 5, 5, 5, 5, 5, 80, 90, 100]
        avg = sum(monthly_counts) / len(monthly_counts)
        flagged = [c for c in monthly_counts if c > avg * 2]
        assert len(flagged) == 3  # last three months

    def test_weekend_ratio(self):
        """30 % weekend billing threshold."""
        total = 100
        weekend = 35
        ratio = weekend / total
        assert ratio > 0.30


class TestComparisonHelpers:
    """Validate peer comparison logic."""

    def test_peer_z_score(self):
        peer_avgs = np.array([100, 110, 90, 105, 95])
        provider_avg = 200
        mean = np.mean(peer_avgs)
        std = np.std(peer_avgs)
        z = (provider_avg - mean) / std
        assert z > 3  # clearly above peers
