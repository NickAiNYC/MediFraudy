
import pytest
from unittest.mock import MagicMock
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Provider, Claim
from analytics.member_profiling import MemberProfiler

# Setup in-memory DB
engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()

def test_identify_high_cost_members(db_session):
    # Setup Data
    # 10 Providers
    providers = [Provider(npi=f"123456789{i}", name=f"Prov {i}") for i in range(10)]
    db_session.add_all(providers)
    db_session.commit()
    provider_ids = [p.id for p in providers]

    # 1 Normal Member (Low cost)
    for i in range(5):
        db_session.add(Claim(
            provider_id=provider_ids[0],
            beneficiary_id="NORMAL_MEM",
            billing_code="99213",
            amount=100.0,
            claim_date=date(2024, 1, 1)
        ))
    
    # 1 High Cost Member (Identity Theft Victim?)
    for i in range(50):
        db_session.add(Claim(
            provider_id=provider_ids[1],
            beneficiary_id="HIGH_COST_MEM",
            billing_code="99213",
            amount=1000.0, # High amount
            claim_date=date(2024, 1, 1)
        ))
        
    db_session.commit()
    
    # Run Profiler
    profiler = MemberProfiler(db_session)
    
    # Mock global stats to avoid SQLite STDDEV error
    profiler.global_stats = {
        "avg_cost": 200.0,
        "std_cost": 100.0,
        "avg_prov": 1.2,
        "std_prov": 0.5
    }
    
    high_risk = profiler.identify_high_risk_members(z_threshold=2.0)
    
    assert len(high_risk) > 0
    assert high_risk[0]['beneficiary_id'] == "HIGH_COST_MEM"
    assert high_risk[0]['risk_factor'] == "high_cost"

def test_identify_doctor_shoppers(db_session):
    # Setup Data
    providers = [Provider(npi=f"987654321{i}", name=f"Prov {i}") for i in range(10)]
    db_session.add_all(providers)
    db_session.commit()
    
    # Shopper visits all 10 providers
    for p in providers:
        db_session.add(Claim(
            provider_id=p.id,
            beneficiary_id="SHOPPER_MEM",
            billing_code="99213",
            amount=50.0,
            claim_date=date(2024, 1, 1)
        ))
        
    # Normal members visit 1 provider
    for i in range(20):
        db_session.add(Claim(
            provider_id=providers[0].id,
            beneficiary_id=f"LOYAL_{i}",
            billing_code="99213",
            amount=50.0,
            claim_date=date(2024, 1, 1)
        ))
        
    db_session.commit()
    
    profiler = MemberProfiler(db_session)
    # Mock global stats to avoid SQLite STDDEV error
    profiler.global_stats = {
        "avg_cost": 50.0,
        "std_cost": 10.0,
        "avg_prov": 1.0,
        "std_prov": 0.5
    }

    shoppers = profiler.identify_doctor_shoppers(z_threshold=2.0)
    
    assert len(shoppers) > 0
    assert shoppers[0]['beneficiary_id'] == "SHOPPER_MEM"
    assert shoppers[0]['unique_providers'] == 10

def test_identify_pill_mill_patients(db_session):
    # This test mocks the DB execution because SQLite doesn't support STDDEV
    profiler = MemberProfiler(db_session)
    
    # Create a mock result proxy
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        ("PILL_SEEKER", 50, 5000.0, 10)
    ]
    
    # Mock the execute method on the session
    # Note: SQLAlchemy session.execute is what we call
    db_session.execute = MagicMock(return_value=mock_result)
    
    suspects = profiler.identify_pill_mill_patients(drug_codes=["J2270"])
    
    assert len(suspects) == 1
    assert suspects[0]["beneficiary_id"] == "PILL_SEEKER"
    assert suspects[0]["prescription_count"] == 50
    assert suspects[0]["provider_count"] == 10
