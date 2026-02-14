"""Shared pytest fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import random

from models import Base, Provider, Claim

@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def sample_provider(db_session):
    """Create sample provider."""
    provider = Provider(
        npi="1234567890",
        name="Test Nursing Home",
        facility_type="nursing_facility",
        city="Brooklyn",
        state="NY",
        licensed_capacity=100
    )
    db_session.add(provider)
    db_session.commit()
    return provider

@pytest.fixture
def sample_claims(db_session, sample_provider):
    """Create sample claims."""
    claims = []
    for i in range(100):
        claim = Claim(
            provider_id=sample_provider.id,
            claim_id=f"CLM{i}",
            beneficiary_id=f"BEN{random.randint(1,20)}",
            billing_code=f"CODE{random.randint(1,10)}",
            amount=random.uniform(100, 500),
            claim_date=datetime.now() - timedelta(days=random.randint(1,365))
        )
        claims.append(claim)
    
    db_session.add_all(claims)
    db_session.commit()
    return claims
