"""Tests for pattern-of-life analytics module."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from analytics.pattern_of_life import (
    analyze_behavioral_patterns,
    detect_capacity_violations,
    detect_kickback_patterns,
    comprehensive_pattern_analysis,
    analyze_nyc_elderly_care_facilities,
)
from models import Provider, Claim, Base


# Create in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def test_db():
    """Create test database session."""
    # Create new tables for each test
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    yield db
    db.close()


@pytest.fixture
def sample_provider(test_db: Session):
    """Create a sample provider for testing."""
    provider = Provider(
        npi="1234567890",
        name="Test Nursing Home",
        facility_type="Nursing Home",
        city="New York",
        state="NY",
        zip_code="10001",
        licensed_capacity=50
    )
    test_db.add(provider)
    test_db.commit()
    test_db.refresh(provider)
    return provider


def test_analyze_behavioral_patterns_no_claims(test_db, sample_provider):
    """Test behavioral analysis with no claims."""
    result = analyze_behavioral_patterns(test_db, sample_provider.id)
    
    assert result["provider_id"] == sample_provider.id
    assert result["risk_score"] == 0
    assert len(result["findings"]) == 0


def test_analyze_behavioral_patterns_weekend_billing(test_db, sample_provider):
    """Test detection of unusual weekend billing patterns."""
    # Create weekend claims (Saturday and Sunday) - use recent dates
    base_date = datetime.utcnow() - timedelta(days=90)  # 90 days ago
    
    for i in range(30):
        day_offset = i % 7
        claim_date = base_date + timedelta(days=day_offset)
        
        claim = Claim(
            provider_id=sample_provider.id,
            beneficiary_id=f"BENEF{i % 10}",
            billing_code="99213",
            amount=100.0,
            claim_date=claim_date.date(),
            submitted_date=claim_date
        )
        test_db.add(claim)
    
    test_db.commit()
    
    result = analyze_behavioral_patterns(test_db, sample_provider.id)
    
    assert result["provider_id"] == sample_provider.id
    assert result["total_claims_analyzed"] > 0
    # Weekend ratio should be ~2/7 = 28.5%, which should trigger findings
    assert result["risk_score"] > 0


def test_detect_capacity_violations_no_capacity(test_db, sample_provider):
    """Test capacity detection when no capacity is set."""
    # Remove capacity
    sample_provider.licensed_capacity = None
    test_db.commit()
    
    result = detect_capacity_violations(test_db, sample_provider.id)
    
    assert "error" not in result
    assert result["risk_score"] == 0


def test_detect_capacity_violations_with_violation(test_db, sample_provider):
    """Test detection of capacity violations."""
    # Create claims for 60 unique beneficiaries on the same day
    # Licensed capacity is 50, so this is a violation
    violation_date = datetime.utcnow() - timedelta(days=30)  # Recent date
    
    for i in range(60):
        claim = Claim(
            provider_id=sample_provider.id,
            beneficiary_id=f"BENEF{i:03d}",
            billing_code="99213",
            amount=100.0,
            claim_date=violation_date.date(),
            submitted_date=violation_date
        )
        test_db.add(claim)
    
    test_db.commit()
    
    result = detect_capacity_violations(test_db, sample_provider.id)
    
    assert result["provider_id"] == sample_provider.id
    assert result["licensed_capacity"] == 50
    assert result["risk_score"] > 0
    assert len(result["findings"]) > 0
    
    # Check for capacity violation finding
    capacity_finding = next(
        (f for f in result["findings"] if f["type"] == "capacity_violation"),
        None
    )
    assert capacity_finding is not None
    assert capacity_finding["severity"] in ["critical", "high"]


def test_detect_kickback_patterns_no_data(test_db, sample_provider):
    """Test kickback detection with no claims."""
    result = detect_kickback_patterns(test_db, sample_provider.id)
    
    assert result["provider_id"] == sample_provider.id
    assert result["risk_score"] == 0


def test_detect_kickback_patterns_concentration(test_db, sample_provider):
    """Test detection of beneficiary concentration patterns."""
    # Create claims with high concentration (one beneficiary has many claims)
    base_date = datetime.utcnow() - timedelta(days=180)  # Recent date
    
    # High-frequency beneficiary
    for i in range(50):
        claim = Claim(
            provider_id=sample_provider.id,
            beneficiary_id="BENEF_HIGH_FREQ",
            billing_code="99213",
            amount=100.0,
            claim_date=(base_date + timedelta(days=i)).date(),
            submitted_date=base_date + timedelta(days=i)
        )
        test_db.add(claim)
    
    # Normal beneficiaries
    for i in range(10):
        claim = Claim(
            provider_id=sample_provider.id,
            beneficiary_id=f"BENEF{i}",
            billing_code="99213",
            amount=100.0,
            claim_date=(base_date + timedelta(days=i)).date(),
            submitted_date=base_date + timedelta(days=i)
        )
        test_db.add(claim)
    
    test_db.commit()
    
    result = detect_kickback_patterns(test_db, sample_provider.id)
    
    assert result["provider_id"] == sample_provider.id
    assert result["total_beneficiaries"] == 11  # 1 high freq + 10 normal
    assert result["risk_score"] > 0
    
    # Should detect concentration
    concentration_finding = next(
        (f for f in result["findings"] if f["type"] == "beneficiary_concentration"),
        None
    )
    assert concentration_finding is not None


def test_comprehensive_pattern_analysis(test_db, sample_provider):
    """Test comprehensive analysis combining all modules."""
    # Create test data
    base_date = datetime.utcnow() - timedelta(days=60)  # Recent date
    
    for i in range(50):
        claim = Claim(
            provider_id=sample_provider.id,
            beneficiary_id=f"BENEF{i % 10}",
            billing_code="99213",
            amount=100.0,
            claim_date=(base_date + timedelta(days=i)).date(),
            submitted_date=base_date + timedelta(days=i)
        )
        test_db.add(claim)
    
    test_db.commit()
    
    result = comprehensive_pattern_analysis(test_db, sample_provider.id)
    
    assert result["provider_id"] == sample_provider.id
    assert result["analysis_type"] == "comprehensive_pattern_of_life"
    assert "composite_risk_score" in result
    assert "severity" in result
    assert "analysis_modules" in result
    assert "behavioral" in result["analysis_modules"]
    assert "capacity_violations" in result["analysis_modules"]
    assert "kickback_indicators" in result["analysis_modules"]


def test_analyze_nyc_elderly_care_facilities(test_db):
    """Test NYC-wide facility sweep."""
    # Create multiple NYC providers
    facilities = [
        ("Test Nursing Home 1", "Nursing Home", "New York", "1234567890"),
        ("Test Adult Day Care", "Adult Day Care", "Brooklyn", "1234567891"),
        ("Test Home Health", "Home Health Agency", "Queens", "1234567892"),
    ]
    
    for name, facility_type, city, npi in facilities:
        provider = Provider(
            npi=npi,
            name=name,
            facility_type=facility_type,
            city=city,
            state="NY",
            zip_code="10001",
            licensed_capacity=50
        )
        test_db.add(provider)
    
    test_db.commit()
    
    result = analyze_nyc_elderly_care_facilities(test_db, min_risk_score=0, limit=10)
    
    assert result["analysis_type"] == "nyc_elderly_care_sweep"
    assert "providers_analyzed" in result
    assert "high_risk_facilities" in result
    assert "results" in result


def test_provider_not_found(test_db):
    """Test handling of non-existent provider."""
    result = analyze_behavioral_patterns(test_db, provider_id=99999)
    
    assert "error" in result
    assert result["error"] == "Provider not found"


def test_batch_submission_detection(test_db, sample_provider):
    """Test detection of suspicious batch submissions."""
    # Create claims all submitted at the same hour
    base_date = datetime.utcnow() - timedelta(days=45)  # Recent date, 2 PM
    
    for i in range(30):
        claim = Claim(
            provider_id=sample_provider.id,
            beneficiary_id=f"BENEF{i}",
            billing_code="99213",
            amount=100.0,
            claim_date=(base_date + timedelta(days=i)).date(),
            submitted_date=base_date  # All at same time
        )
        test_db.add(claim)
    
    test_db.commit()
    
    result = analyze_behavioral_patterns(test_db, sample_provider.id)
    
    # Should detect batch submission pattern
    batch_finding = next(
        (f for f in result["findings"] if f["type"] == "batch_submission_pattern"),
        None
    )
    assert batch_finding is not None
    assert batch_finding["severity"] == "medium"
