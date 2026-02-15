"""Tests for the evidence builder service."""

import pytest
from unittest.mock import MagicMock, patch


class TestLitigationNarrative:
    """Test the auto-generated litigation narrative."""

    def test_narrative_includes_provider_name(self):
        """Narrative must reference the provider by name."""
        from services.evidence_builder import _generate_litigation_narrative

        provider = MagicMock()
        provider.name = "Test Health LLC"
        provider.npi = "1234567890"
        provider.city = "Brooklyn"
        provider.state = "NY"

        risk = {"risk_score": 82, "risk_level": "HIGH", "drivers": ["Billing 4.8x peer avg"]}
        stats = {"peer_deviation_ratio": 4.8, "borough": "Brooklyn", "provider_total_billing": 5000000, "provider_claims": 1200}
        network = {"connected_entities": 3, "high_risk_connections": 1, "in_fraud_ring": False}
        anomalies = [{"z_score": 5.2, "billing_code": "97110"}]
        timeline = [{"flag": "spike", "month": "2025-06-01"}]

        narrative = _generate_litigation_narrative(
            provider, risk, stats, network, anomalies, timeline
        )

        assert "Test Health LLC" in narrative
        assert "82" in narrative
        assert "HIGH" in narrative

    def test_narrative_includes_billing_deviation(self):
        """Narrative should mention billing deviation when significant."""
        from services.evidence_builder import _generate_litigation_narrative

        provider = MagicMock()
        provider.name = "Fraud Corp"
        provider.npi = "9999999999"
        provider.city = "Queens"
        provider.state = "NY"

        risk = {"risk_score": 90, "risk_level": "HIGH", "drivers": []}
        stats = {"peer_deviation_ratio": 6.2, "borough": "Queens", "provider_total_billing": 8000000, "provider_claims": 2000}
        network = {"connected_entities": 0, "in_fraud_ring": False}
        anomalies = []
        timeline = []

        narrative = _generate_litigation_narrative(
            provider, risk, stats, network, anomalies, timeline
        )

        assert "6.2x" in narrative
        assert "Queens" in narrative

    def test_narrative_mentions_fraud_ring(self):
        """Narrative should mention fraud ring membership."""
        from services.evidence_builder import _generate_litigation_narrative

        provider = MagicMock()
        provider.name = "Ring Member Inc"
        provider.npi = "1111111111"
        provider.city = "Bronx"
        provider.state = "NY"

        risk = {"risk_score": 75, "risk_level": "HIGH", "drivers": []}
        stats = {"peer_deviation_ratio": 1.2}
        network = {
            "connected_entities": 5,
            "high_risk_connections": 3,
            "in_fraud_ring": True,
            "fraud_ring_info": {"ring_size": 4, "fraud_score": 88, "suspicion_level": "HIGH"},
        }
        anomalies = []
        timeline = []

        narrative = _generate_litigation_narrative(
            provider, risk, stats, network, anomalies, timeline
        )

        assert "fraud ring" in narrative.lower()
        assert "3 high-risk entities" in narrative

    def test_empty_data_produces_minimal_narrative(self):
        """Narrative should still generate with minimal data."""
        from services.evidence_builder import _generate_litigation_narrative

        provider = MagicMock()
        provider.name = "Minimal Provider"
        provider.npi = "0000000000"
        provider.city = None
        provider.state = None

        risk = {"risk_score": 10, "risk_level": "LOW", "drivers": []}
        stats = {}
        network = {"connected_entities": 0, "in_fraud_ring": False}
        anomalies = []
        timeline = []

        narrative = _generate_litigation_narrative(
            provider, risk, stats, network, anomalies, timeline
        )

        assert "Minimal Provider" in narrative
        assert len(narrative) > 50  # Should still have substance


class TestEvidencePackage:
    """Test the full evidence package generation."""

    def test_package_structure(self):
        """Evidence package must contain all required sections."""
        from services.evidence_builder import generate_case_package

        db = MagicMock()
        provider = MagicMock()
        provider.id = 1
        provider.npi = "1234567890"
        provider.name = "Test Provider"
        provider.address = "123 Main St"
        provider.city = "Brooklyn"
        provider.state = "NY"
        provider.facility_type = "nursing_facility"
        provider.licensed_capacity = 100

        db.query.return_value.filter.return_value.first.return_value = provider
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.join.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        with patch("services.network_analysis.get_network_summary") as mock_net:
            mock_net.return_value = {"connected_entities": 0, "in_fraud_ring": False}

            result = generate_case_package(db, 1)

        assert "provider" in result
        assert "risk_assessment" in result
        assert "statistical_comparison" in result
        assert "timeline" in result
        assert "claim_breakdown" in result
        assert "network_summary" in result
        assert "litigation_narrative" in result
        assert "disclaimer" in result

    def test_provider_not_found(self):
        """Should return error for non-existent provider."""
        from services.evidence_builder import generate_case_package

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = generate_case_package(db, 99999)
        assert "error" in result
