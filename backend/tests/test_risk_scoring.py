"""Tests for the fraud risk scoring engine."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from services.risk_scoring import (
    calculate_risk_score,
    batch_risk_scores,
    _billing_zscore_component,
    _temporal_spike_component,
    _behavioral_component,
    _network_risk_component,
    _nyc_specific_component,
    _historical_risk_component,
    WEIGHTS,
    RISK_CATEGORIES,
)


class TestRiskScoringWeights:
    """Test risk scoring weight configuration."""

    def test_weights_sum_to_one(self):
        """All weights must sum to 1.0 for proper normalization."""
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_all_weight_keys_present(self):
        """All expected 4-layer component keys must be present."""
        expected = {
            "statistical_anomaly", "behavioral_signals",
            "network_intelligence", "historical_risk",
        }
        assert set(WEIGHTS.keys()) == expected

    def test_weights_non_negative(self):
        """No weight should be negative."""
        for key, value in WEIGHTS.items():
            assert value >= 0, f"Weight {key} is negative: {value}"

    def test_layer_weights_match_spec(self):
        """Verify 4-layer weight allocation matches specification."""
        assert WEIGHTS["statistical_anomaly"] == 0.30
        assert WEIGHTS["behavioral_signals"] == 0.30
        assert WEIGHTS["network_intelligence"] == 0.25
        assert WEIGHTS["historical_risk"] == 0.15


class TestRiskCategories:
    """Test risk category labels."""

    def test_risk_categories_defined(self):
        """All risk levels must have category labels."""
        assert "HIGH" in RISK_CATEGORIES
        assert "REVIEW" in RISK_CATEGORIES
        assert "LOW" in RISK_CATEGORIES
        assert RISK_CATEGORIES["HIGH"] == "High Litigation Risk"


class TestRiskScoreBands:
    """Test risk score classification bands."""

    def test_low_risk_band(self):
        """Scores 0-39 should be LOW."""
        db = MagicMock()
        provider = MagicMock()
        provider.id = 1
        provider.name = "Test"
        provider.state = "NY"
        provider.facility_type = "nursing_facility"
        provider.licensed_capacity = None
        provider.npi = "1234567890"
        provider.city = "Brooklyn"

        db.query.return_value.filter.return_value.first.return_value = provider
        # Mock all sub-queries to return empty/zero
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.join.return_value.filter.return_value.first.return_value = None

        result = calculate_risk_score(db, 1)
        # With all zero sub-scores, score should be 0 (LOW)
        assert result["risk_score"] == 0
        assert result["risk_level"] == "LOW"
        assert result["category"] == "Low Risk"

    def test_result_includes_category(self):
        """Result should include a human-readable category."""
        db = MagicMock()
        provider = MagicMock()
        provider.id = 1
        provider.name = "Test"
        provider.state = "CA"
        provider.facility_type = None
        provider.licensed_capacity = None

        db.query.return_value.filter.return_value.first.return_value = provider
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.join.return_value.filter.return_value.first.return_value = None

        result = calculate_risk_score(db, 1)
        assert "category" in result
        assert "layer_details" in result

    def test_provider_not_found(self):
        """Should return error for non-existent provider."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = calculate_risk_score(db, 99999)
        assert "error" in result
        assert result["risk_score"] == 0
        assert result["category"] == "Insufficient Data"


class TestBillingZscoreComponent:
    """Test the billing z-score component."""

    def test_no_claims_returns_zero(self):
        """Provider with no claims should get zero score."""
        db = MagicMock()
        provider = MagicMock()
        provider.state = "NY"

        db.query.return_value.filter.return_value.first.return_value = (None, 0)

        score, drivers = _billing_zscore_component(
            db, provider, datetime.utcnow() - timedelta(days=365)
        )
        assert score == 0.0
        assert drivers == []


class TestNetworkRiskComponent:
    """Test the network risk component."""

    def test_no_anomalies_returns_zero(self):
        """Provider with no anomalies should get zero network risk."""
        db = MagicMock()
        provider = MagicMock()
        provider.id = 1

        db.query.return_value.filter.return_value.scalar.return_value = 0

        score, drivers = _network_risk_component(db, provider)
        assert score == 0.0
        assert len(drivers) == 0

    def test_anomalies_increase_score(self):
        """Anomalies should increase the network risk score."""
        db = MagicMock()
        provider = MagicMock()
        provider.id = 1

        # First call: anomaly_count, second call: high_z_count
        db.query.return_value.filter.return_value.scalar.side_effect = [5, 2]

        score, drivers = _network_risk_component(db, provider)
        assert score > 0
        assert any("anomalies" in d for d in drivers)


class TestNYCSpecificComponent:
    """Test the NYC-specific fraud signal component."""

    def test_non_ny_returns_zero(self):
        """Non-NY providers should get zero NYC-specific score."""
        db = MagicMock()
        provider = MagicMock()
        provider.state = "CA"

        score, drivers = _nyc_specific_component(
            db, provider, datetime.utcnow() - timedelta(days=365)
        )
        assert score == 0.0
        assert drivers == []
