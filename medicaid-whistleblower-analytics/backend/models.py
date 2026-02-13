"""SQLAlchemy ORM models for Medicaid analytics."""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Date,
)
from sqlalchemy.orm import relationship

from database import Base


class Provider(Base):
    """Healthcare provider record."""

    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    npi = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(String(500))
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(10))
    facility_type = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    claims = relationship("Claim", back_populates="provider")
    anomalies = relationship("Anomaly", back_populates="provider")
    cases = relationship("Case", back_populates="facility")


class Claim(Base):
    """Individual billing claim."""

    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    billing_code = Column(String(20), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    claim_date = Column(Date, nullable=False)
    service_category = Column(String(100))
    units = Column(Integer)

    provider = relationship("Provider", back_populates="claims")


class Anomaly(Base):
    """Detected billing anomaly."""

    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    billing_code = Column(String(20), nullable=False)
    z_score = Column(Float, nullable=False)
    anomaly_type = Column(String(100))
    notes = Column(Text)
    detected_at = Column(DateTime, default=datetime.utcnow)

    provider = relationship("Provider", back_populates="anomalies")


class Case(Base):
    """Whistleblower investigation case."""

    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(50), unique=True, nullable=False)
    facility_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    status = Column(String(50), default="open")
    whistleblower_notes = Column(Text)
    evidence_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    facility = relationship("Provider", back_populates="cases")
    timeline_events = relationship("TimelineEvent", back_populates="case")


class TimelineEvent(Base):
    """Evidence timeline entry for a case."""

    __tablename__ = "timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    event_date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    evidence_type = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="timeline_events")
