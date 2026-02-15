"""Tests for analytics modules (statistical, comparison, patterns, pattern_of_life)."""

import numpy as np
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models import Base, Provider, Claim, Anomaly
from app.analytics.statistical import calculate_billing_stats, detect_outliers, detect_yoy_trends
from app.analytics.comparison import compare_provider_to_peers
from app.analytics.patterns import detect_fraud_patterns
from app.analytics.pattern_of_life import (
    ElitePatternOfLifeAnalyzer,
    comprehensive_pattern_analysis,
    detect_capacity_violations,
    detect_kickback_patterns,
    analyze_behavioral_patterns,
    analyze_nyc_elderly_care_facilities
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_provider(db_session: Session):
    """Create a sample provider for testing."""
    provider = Provider(
        npi="1234567890",
        name="Test Nursing Home",
        facility_type="nursing_facility",
        city="Brooklyn",
        state="NY",
        zip_code="11201",
        licensed_capacity=100
    )
    db_session.add(provider)
    db_session.commit()
    return provider


@pytest.fixture
def sample_claims(db_session: Session, sample_provider: Provider):
    """Create sample claims for testing."""
    claims = []
    base_date = datetime(2023, 1, 1)
    
    # Create 12 months of normal claims
    for month in range(12):
        for _ in range(50):  # 50 claims per month
            claim = Claim(
                provider_id=sample_provider.id,
                claim_id=f"CLM{month}_{_}",
                beneficiary_id=f"BEN{_ % 10}",  # Concentrated beneficiaries
                procedure_code="T2024",  # Adult day care code
                amount=200.0,
                service_date=base_date + timedelta(days=month*30 + _),
                units=1
            )
            claims.append(claim)
    
    # Add some weekend claims
    for i in range(20):
        claim = Claim(
            provider_id=sample_provider.id,
            claim_id=f"WKND{i}",
            beneficiary_id=f"BEN{i % 5}",
            procedure_code="T2024",
            amount=200.0,
            service_date=base_date + timedelta(days=i*7 + 5),  # Saturdays
            units=1
        )
        claims.append(claim)
    
    db_session.add_all(claims)
    db_session.commit()
    return claims


@pytest.fixture
def high_risk_provider(db_session: Session):
    """Create a provider with high-risk patterns (Queens/Brooklyn style)."""
    provider = Provider(
        npi="9999999999",
        name="High Risk Facility",
        facility_type="adult_day_care",
        city="Queens",
        state="NY",
        zip_code="11375",
        licensed_capacity=50
    )
    db_session.add(provider)
    db_session.commit()
    
    claims = []
    base_date = datetime(2020, 1, 1)
    
    # Pattern 1: Capacity violations (billing > 50 patients/day)
    for day in range(100):
        # 60 patients some days (exceeds 50 capacity)
        patient_count = 60 if day % 3 == 0 else 30
        for p in range(patient_count):
            claim = Claim(
                provider_id=provider.id,
                claim_id=f"RISK{day}_{p}",
                beneficiary_id=f"BEN{p % 5}",  # Super concentrated (only 5 patients)
                procedure_code="T2024",
                amount=250.0,
                service_date=base_date + timedelta(days=day),
                units=1
            )
            claims.append(claim)
    
    # Pattern 2: Weekend billing
    for day in range(50):
        if day % 7 >= 5:  # Weekend
            for _ in range(20):
                claim = Claim(
                    provider_id=provider.id,
                    claim_id=f"WEEKEND{day}_{_}",
                    beneficiary_id=f"BEN{_ % 3}",
                    procedure_code="T2024",
                    amount=250.0,
                    service_date=base_date + timedelta(days=day),
                    units=1
                )
                claims.append(claim)
    
    db_session.add_all(claims)
    db_session.commit()
    return provider


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
        assert abs(z - 2.0) < 0.1  # Should be exactly 2.0

    def test_zero_std_no_crash(self):
        """When all values are equal, std is 0 — must not divide by zero."""
        values = np.array([100, 100, 100])
        std = np.std(values)
        assert std == 0
        
        # Division guard (what your code should do)
        mean = np.mean(values)
        z = (100 - mean) / std if std > 0 else 0.0
        assert z == 0.0


class TestPatternHelpers:
    """Validate pattern detection thresholds."""

    def test_high_volume_threshold(self):
        """If a provider has 2× the average, it should be flagged."""
        monthly_counts = [5, 5, 5, 5, 5, 5, 5, 80, 90, 100]
        avg = sum(monthly_counts) / len(monthly_counts)
        flagged = [c for c in monthly_counts if c > avg * 2]
        assert len(flagged) == 3  # last three months
        
        # Calculate percentage increase
        last_3_avg = sum(monthly_counts[-3:]) / 3
        first_7_avg = sum(monthly_counts[:7]) / 7
        assert last_3_avg > first_7_avg * 10  # 10x increase

    def test_weekend_ratio(self):
        """30% weekend billing threshold."""
        total = 100
        weekend = 35
        ratio = weekend / total
        assert ratio > 0.30
        assert ratio == 0.35

    def test_capacity_violation_detection(self):
        """Test capacity violation logic."""
        licensed = 50
        daily_counts = [30, 45, 60, 55, 40, 65, 35]
        violations = [d for d in daily_counts if d > licensed]
        assert len(violations) == 3  # 60, 55, 65
        assert max(violations) == 65


class TestComparisonHelpers:
    """Validate peer comparison logic."""

    def test_peer_z_score(self):
        peer_avgs = np.array([100, 110, 90, 105, 95])
        provider_avg = 200
        mean = np.mean(peer_avgs)
        std = np.std(peer_avgs)
        z = (provider_avg - mean) / std
        assert z > 3  # clearly above peers
        assert z > 5  # Actually ~6.7


# ---------------------------------------------------------------------------
# Integration tests (require database)
# ---------------------------------------------------------------------------

class TestStatisticalIntegration:
    """Test statistical functions with real database."""

    def test_calculate_billing_stats(self, db_session: Session, sample_provider: Provider, sample_claims):
        """Test billing statistics calculation."""
        stats = calculate_billing_stats(db_session, state="NY")
        assert stats is not None
        assert "mean" in stats
        assert "std" in stats
        assert stats["count"] > 0

    def test_detect_outliers(self, db_session: Session, sample_provider: Provider, sample_claims):
        """Test outlier detection."""
        outliers = detect_outliers(db_session, z_threshold=2.0, state="NY")
        assert outliers is not None
        # Should find some outliers (our test data has them)


class TestPatternOfLifeIntegration:
    """Test POL analyzer with real database."""

    def test_pol_analyzer_initialization(self, db_session: Session):
        """Test that POL analyzer can be created."""
        analyzer = ElitePatternOfLifeAnalyzer(db_session)
        assert analyzer is not None
        assert analyzer.weights is not None
        assert len(analyzer.weights) == 6

    def test_pol_analysis_normal_provider(self, db_session: Session, sample_provider: Provider):
        """Test POL analysis on normal provider (should be low risk)."""
        analyzer = ElitePatternOfLifeAnalyzer(db_session)
        result = analyzer.analyze_provider(sample_provider.id)
        
        assert "error" not in result
        assert result["risk_score"] is not None
        assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
        assert "indicators" in result

    def test_pol_analysis_high_risk(self, db_session: Session, high_risk_provider: Provider):
        """Test POL analysis on high-risk provider (should detect patterns)."""
        analyzer = ElitePatternOfLifeAnalyzer(db_session)
        result = analyzer.analyze_provider(high_risk_provider.id)
        
        assert "error" not in result
        assert result["risk_score"] >= 50  # Should be medium-high
        assert result["risk_level"] in ["MEDIUM", "HIGH"]
        
        # Check specific indicators
        indicators = result["indicators"]
        assert "capacity_exceed" in indicators
        assert indicators["capacity_exceed"]["score"] > 10  # Should detect capacity violations
        
        assert "referral_concentration" in indicators
        assert indicators["referral_concentration"]["score"] > 5  # Should detect concentration

    def test_capacity_violations_detection(self, db_session: Session, high_risk_provider: Provider):
        """Test capacity violation endpoint."""
        violations = detect_capacity_violations(db_session, high_risk_provider.id, lookback_days=365)
        
        assert violations is not None
        assert "violations" in violations or "count" in violations
        # Our test data should have violations

    def test_kickback_patterns_detection(self, db_session: Session, high_risk_provider: Provider):
        """Test kickback pattern detection."""
        patterns = detect_kickback_patterns(db_session, high_risk_provider.id, lookback_days=365)
        
        assert patterns is not None
        # Should detect beneficiary concentration

    def test_behavioral_patterns(self, db_session: Session, high_risk_provider: Provider):
        """Test behavioral pattern detection."""
        patterns = analyze_behavioral_patterns(db_session, high_risk_provider.id, lookback_days=365)
        
        assert patterns is not None
        # Should detect weekend billing

    def test_nyc_sweep(self, db_session: Session, sample_provider: Provider, high_risk_provider: Provider):
        """Test NYC elderly care sweep."""
        results = analyze_nyc_elderly_care_facilities(db_session, min_risk_score=30, limit=10)
        
        assert results is not None
        assert "facilities" in results
        assert len(results["facilities"]) >= 1
        
        # High-risk provider should be in results
        high_risk_found = any(f["id"] == high_risk_provider.id for f in results["facilities"])
        assert high_risk_found

    def test_comprehensive_pattern_analysis(self, db_session: Session, high_risk_provider: Provider):
        """Test comprehensive pattern analysis endpoint."""
        result = comprehensive_pattern_analysis(db_session, high_risk_provider.id, lookback_days=365)
        
        assert result is not None
        assert "risk_score" in result
        assert "risk_level" in result
        assert "capacity_analysis" in result or "indicators" in result


class TestFraudPatternsIntegration:
    """Test fraud pattern detection."""

    def test_detect_fraud_patterns(self, db_session: Session, high_risk_provider: Provider):
        """Test fraud pattern detection."""
        patterns = detect_fraud_patterns(db_session, provider_id=high_risk_provider.id)
        
        assert patterns is not None
        # Should detect some patterns


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_provider_not_found(self, db_session: Session):
        """Test handling of non-existent provider."""
        analyzer = ElitePatternOfLifeAnalyzer(db_session)
        result = analyzer.analyze_provider(99999)
        
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_provider_with_no_claims(self, db_session: Session, sample_provider: Provider):
        """Test provider with no claims data."""
        analyzer = ElitePatternOfLifeAnalyzer(db_session)
        result = analyzer.analyze_provider(sample_provider.id)
        
        # Should handle gracefully
        assert result is not None
        assert "error" in result or result["risk_score"] == 0

    def test_malformed_dates(self, db_session: Session):
        """Test handling of malformed date data."""
        # This would need a fixture with bad dates
        pass
