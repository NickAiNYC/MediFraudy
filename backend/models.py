"""SQLAlchemy ORM models for Medicaid analytics.

Includes core provider/claim data, fraud detection models for
Queens $120M and Brooklyn $68M case patterns, and whistleblower
case management.
"""

from datetime import datetime, timedelta

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Date,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates

from database import Base


class Provider(Base):
    """Healthcare provider record.

    Core entity representing a Medicaid billing provider (facility or individual).
    Licensed capacity is critical for Queens-style fraud detection.
    """

    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    npi = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(String(500))
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(10))
    facility_type = Column(String(100))
    specialty = Column(String(100))
    licensed_capacity = Column(Integer, nullable=True)  # NULL = unknown
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    claims = relationship("Claim", back_populates="provider", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="provider", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="provider", cascade="all, delete-orphan")
    kickback_indicators = relationship("KickbackIndicator", back_populates="provider", cascade="all, delete-orphan")
    capacity_violations = relationship("CapacityViolation", back_populates="provider", cascade="all, delete-orphan")
    pol_results = relationship("POLResult", back_populates="provider", cascade="all, delete-orphan", uselist=False)
    
    # Extended relationships
    screenings = relationship("ProviderScreening", back_populates="provider", cascade="all, delete-orphan")
    investigations = relationship("InvestigationCase", back_populates="provider", cascade="all, delete-orphan")

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_provider_location", "state", "city"),
        Index("idx_provider_type", "facility_type", "state"),
    )

    def __repr__(self):
        return f"<Provider id={self.id} npi={self.npi} name={self.name}>"


class Claim(Base):
    """Individual billing claim.

    Each row represents a single claim line. Beneficiary_id enables
    kickback detection (Brooklyn case). Submitted_date enables batch
    submission analysis.
    """

    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Identifiers
    claim_id = Column(String(50), index=True)  # Original claim ID from dataset
    beneficiary_id = Column(String(50), index=True)  # For kickback detection
    
    # Claim details
    billing_code = Column(String(20), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    claim_date = Column(Date, nullable=False, index=True)
    submitted_date = Column(DateTime)  # For batch submission detection
    service_category = Column(String(100))
    units = Column(Integer, default=1)
    place_of_service = Column(String(50))
    modifiers = Column(JSON, default=list)  # Code modifiers
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    provider = relationship("Provider", back_populates="claims")
    transport_details = relationship("TransportationTrip", back_populates="claim", uselist=False)


class Beneficiary(Base):
    """Medicaid beneficiary status tracking.
    
    Used to detect claims for ineligible patients (deceased, incarcerated).
    """
    __tablename__ = "beneficiaries"

    id = Column(String(50), primary_key=True)  # Matches claim.beneficiary_id
    status = Column(String(20), default='active')  # active, deceased, incarcerated
    status_date = Column(Date)  # Date of death/incarceration
    risk_score = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

class TransportationTrip(Base):
    """NEMT specific trip details.
    
    Stores geospatial data for analyzing mileage fraud and impossible routes.
    """
    __tablename__ = "transportation_trips"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), unique=True)
    
    # Geospatial data
    pickup_lat = Column(Float)
    pickup_lon = Column(Float)
    dropoff_lat = Column(Float)
    dropoff_lon = Column(Float)
    
    # Trip validation
    calculated_distance = Column(Float)  # Geodesic distance
    claimed_distance = Column(Float)     # Billed mileage
    is_group_ride = Column(Boolean, default=False)
    
    # Relationships
    claim = relationship("Claim", back_populates="transport_details")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_trip_claim", "claim_id"),
    )

    def __repr__(self):
        return f"<TransportationTrip id={self.id} claim_id={self.claim_id}>"


class Anomaly(Base):
    """Detected billing anomaly from statistical analysis.

    Stores outliers identified by z-score analysis for quick access
    in dashboards and exports.
    """

    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    billing_code = Column(String(20), nullable=False)
    z_score = Column(Float, nullable=False)
    anomaly_type = Column(String(100))  # e.g., "high_volume", "weekend_billing", "capacity"
    notes = Column(Text)
    
    # Evidence
    evidence = Column(JSON, default=dict)  # Supporting data (dates, amounts, etc.)
    
    # Timing
    detected_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    provider = relationship("Provider", back_populates="anomalies")

    __table_args__ = (
        Index("idx_anomaly_score", "z_score", "detected_at"),
    )

    def __repr__(self):
        return f"<Anomaly id={self.id} z={self.z_score:.2f}>"


class Case(Base):
    """Whistleblower investigation case.

    Tracks a potential False Claims Act case for a specific facility.
    Includes evidence timeline and whistleblower notes (encrypted in production).
    """

    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(50), unique=True, nullable=False)  # User-friendly ID
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    status = Column(String(50), default="open", index=True)  # open, under_seal, filed, settled
    whistleblower_notes = Column(Text)  # Encrypt in production
    evidence_summary = Column(Text)
    
    # Legal metadata
    filed_date = Column(Date, nullable=True)
    settlement_amount = Column(Float, nullable=True)
    relator_share = Column(Float, nullable=True)  # Percentage
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    provider = relationship("Provider", back_populates="cases")
    timeline_events = relationship("TimelineEvent", back_populates="case", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_case_status", "status", "created_at"),
    )

    def __repr__(self):
        return f"<Case id={self.id} case_id={self.case_id} status={self.status}>"


class TimelineEvent(Base):
    """Evidence timeline entry for a case.

    Chronological record of evidence, observations, and key dates
    for building a compelling FCA disclosure.
    """

    __tablename__ = "timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    
    event_date = Column(Date, nullable=False, index=True)
    description = Column(Text, nullable=False)
    evidence_type = Column(String(100))  # document, observation, data_export, etc.
    evidence_ref = Column(String(500))  # Path or reference to evidence file
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    case = relationship("Case", back_populates="timeline_events")

    __table_args__ = (
        Index("idx_timeline_case_date", "case_id", "event_date"),
    )

    def __repr__(self):
        return f"<TimelineEvent id={self.id} date={self.event_date}>"


class KickbackIndicator(Base):
    """Track patterns indicative of kickback schemes.

    Based on Brooklyn $68M case patterns: cash withdrawals near enrollment
    spikes, suspicious referral networks, and sudden patient enrollment increases.
    """

    __tablename__ = "kickback_indicators"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False, unique=True)
    
    # Core indicators
    beneficiary_concentration = Column(Float)  # 0-1, ratio from top 5% patients
    cash_withdrawal_pattern = Column(Boolean, default=False)  # If financial data available
    enrollment_spike_dates = Column(JSON, default=list)  # Dates of sudden increases
    
    # Network analysis
    referral_network = Column(JSON, default=dict)  # Map of referrer -> volume
    
    # Scoring
    risk_score = Column(Float, default=0.0)  # 0-100
    confidence = Column(String(20), default="low")  # high, medium, low
    
    notes = Column(Text)
    detected_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    provider = relationship("Provider", back_populates="kickback_indicators")

    def __repr__(self):
        return f"<KickbackIndicator provider={self.provider_id} score={self.risk_score}>"


class CapacityViolation(Base):
    """Track billing exceeding facility capacity.

    Based on Queens $120M case: facilities billing for more patients than
    their licensed capacity allows on a given day.
    """

    __tablename__ = "capacity_violations"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Violation details
    violation_date = Column(Date, nullable=False, index=True)
    licensed_capacity = Column(Integer, nullable=False)
    billed_patients = Column(Integer, nullable=False)
    excess_percentage = Column(Float)  # (billed - capacity) / capacity
    
    # Aggregates
    severity = Column(String(20))  # high, medium, low (based on excess %)
    notes = Column(Text)
    
    detected_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    provider = relationship("Provider", back_populates="capacity_violations")

    __table_args__ = (
        Index("idx_capacity_provider_date", "provider_id", "violation_date"),
        UniqueConstraint("provider_id", "violation_date", name="unique_provider_date_violation"),
    )

    def __repr__(self):
        return f"<CapacityViolation provider={self.provider_id} date={self.violation_date} excess={self.excess_percentage:.1f}%>"

    @validates('billed_patients')
    def validate_billed(self, key, billed):
        """Auto-calculate excess percentage."""
        if self.licensed_capacity and billed > self.licensed_capacity:
            self.excess_percentage = (billed - self.licensed_capacity) / self.licensed_capacity * 100
            self.severity = (
                "high" if self.excess_percentage > 50
                else "medium" if self.excess_percentage > 20
                else "low"
            )
        return billed


class POLResult(Base):
    """Cached Pattern-of-Life analysis results.

    Stores the 0-100 risk score and indicator breakdowns
    to avoid recomputing expensive POL analysis on every view.
    Expires after 7 days.
    """

    __tablename__ = "pol_results"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False, unique=True)
    
    # Overall score
    risk_score = Column(Integer, nullable=False)  # 0-100
    risk_level = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW
    
    # Individual indicator scores (denormalized for fast querying)
    sudden_spike_score = Column(Integer, default=0)  # 0-20
    max_code_abuse_score = Column(Integer, default=0)  # 0-15
    timing_anomaly_score = Column(Integer, default=0)  # 0-15
    capacity_exceed_score = Column(Integer, default=0)  # 0-25
    referral_concentration_score = Column(Integer, default=0)  # 0-15
    sustained_no_growth_score = Column(Integer, default=0)  # 0-10
    
    # Full JSON results for detailed views
    full_results = Column(JSON, default=dict)
    
    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    
    # Relationships
    provider = relationship("Provider", back_populates="pol_results")
    
    # New relationships for advanced features
    peer_group_id = Column(Integer, ForeignKey("peer_groups.id"), nullable=True)
    peer_group = relationship("PeerGroup", back_populates="providers")


class ProviderScreening(Base):
    """Provider vetting and screening records.
    
    Tracks background checks, license verification, and other screening steps.
    """
    __tablename__ = "provider_screenings"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    screening_type = Column(String(50)) # initial, revalidation, monthly_monitoring
    status = Column(String(20)) # pass, fail, pending
    check_date = Column(Date, default=datetime.utcnow)
    
    # Details
    license_verified = Column(Boolean, default=False)
    exclusion_list_check = Column(Boolean, default=False) # OIG LEIE, SAM, etc.
    criminal_background_check = Column(Boolean, default=False)
    site_visit_conducted = Column(Boolean, default=False)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to Provider (needs to be added to Provider class if bi-directional is desired)
    provider = relationship("Provider", back_populates="screenings")


class EVVLog(Base):
    """Electronic Visit Verification (EVV) GPS logs.
    
    Used to verify home care visits and detect "impossible travel" or ghost visits.
    """
    __tablename__ = "evv_gps_logs"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    beneficiary_id = Column(String(50), index=True)
    claim_id = Column(String(50), index=True) # Optional link to claim
    
    # GPS Data
    timestamp = Column(DateTime, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float) # GPS accuracy in meters
    
    # Metadata
    device_id = Column(String(100))
    action_type = Column(String(20)) # check_in, check_out, periodic
    
    created_at = Column(DateTime, default=datetime.utcnow)


class InvestigationCase(Base):
    """Integrated case management for investigators.
    
    Replaces/Extends the simpler 'Case' model with more workflow features.
    """
    __tablename__ = "investigation_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Workflow
    status = Column(String(30), default="new") # new, assigned, in_progress, legal_review, closed
    priority = Column(String(20), default="medium") # high, medium, low
    assigned_investigator_id = Column(String(50)) # User ID
    
    # Details
    description = Column(Text)
    detection_source = Column(String(50)) # e.g., "apriori_rule", "peer_profiling", "whistleblower"
    estimated_fraud_amount = Column(Float)
    
    # Dates
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    due_date = Column(Date, nullable=True)
    
    # Relationships
    provider = relationship("Provider", back_populates="investigations")
    audit_trail = relationship("ComplianceAudit", back_populates="case")


class PeerGroup(Base):
    """Peer groups for statistical profiling (Optum FADS style).
    
    Providers are grouped by specialty, geography, and size to establish baselines.
    """
    __tablename__ = "peer_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    
    # Grouping Criteria
    specialty = Column(String(100))
    taxonomy_code = Column(String(20))
    geographic_region = Column(String(50)) # State, County, or custom region
    
    # Statistical Baselines (stored as JSON for flexibility)
    # e.g., {"avg_cost_per_patient": 150.00, "std_dev": 25.00}
    baselines = Column(JSON, default=dict)
    
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    providers = relationship("POLResult", back_populates="peer_group")


class AssociationRule(Base):
    """Discovered association rules (Apriori algorithm).
    
    Represents patterns like "Procedure A -> Procedure B (90% confidence)".
    Used to flag claims that violate these rules or match suspicious patterns.
    """
    __tablename__ = "association_rules"

    id = Column(Integer, primary_key=True, index=True)
    
    antecedents = Column(JSON, nullable=False) # e.g., ["A0427"]
    consequents = Column(JSON, nullable=False) # e.g., ["A0425"]
    
    # Metrics
    support = Column(Float)
    confidence = Column(Float)
    lift = Column(Float)
    
    rule_type = Column(String(20), default="fraud_indicator") # fraud_indicator, normal_pattern
    description = Column(String(255))
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ComplianceAudit(Base):
    """Audit trail for compliance actions and case updates."""
    __tablename__ = "compliance_audits"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id"), nullable=True)
    user_id = Column(String(50))
    
    action = Column(String(100)) # e.g., "status_change", "document_upload"
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("InvestigationCase", back_populates="audit_trail")


class AuditLog(Base):
    """Access audit log — who accessed what provider/resource and when.

    Used for compliance tracking and security monitoring.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # e.g., "view_provider", "export_evidence"
    resource = Column(String(100), nullable=False)  # e.g., "provider", "case", "evidence"
    resource_id = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_audit_user_time", "user", "timestamp"),
        Index("idx_audit_resource", "resource", "resource_id"),
    )
