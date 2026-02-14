"""FastAPI application for Medicaid Whistleblower Analytics."""

import logging
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import settings
from database import get_db, engine, Base
from models import Provider, Claim, Anomaly, Case, TimelineEvent
from analytics.statistical import (
    calculate_billing_stats,
    detect_outliers,
    detect_yoy_trends,
)
from analytics.comparison import compare_provider_to_peers
from analytics.patterns import detect_fraud_patterns

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    logger.info("Starting Medicaid Whistleblower Analytics API")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down API")


app = FastAPI(
    title="Medicaid Whistleblower Analytics",
    description="Analyze HHS DOGE Medicaid dataset for billing anomalies in NYC elderly care facilities",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health ---


@app.get("/health")
async def health_check():
    """Return service health status."""
    return {"status": "healthy"}


# --- Providers ---


@app.get("/api/providers")
def list_providers(
    search: Optional[str] = None,
    facility_type: Optional[str] = None,
    state: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Search and list providers with optional filters."""
    query = db.query(Provider)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            Provider.name.ilike(pattern) | Provider.npi.ilike(pattern)
        )
    if facility_type:
        query = query.filter(Provider.facility_type == facility_type)
    if state:
        query = query.filter(Provider.state == state)
    providers = query.offset(skip).limit(limit).all()
    return {"providers": [_provider_dict(p) for p in providers], "count": query.count()}


@app.get("/api/providers/{provider_id}")
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    """Get detailed information for a single provider."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _provider_dict(provider)


# --- Anomalies ---


@app.get("/api/anomalies")
def list_anomalies(
    min_z_score: float = Query(3.0, ge=0),
    billing_code: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List detected anomalies with filters."""
    query = db.query(Anomaly).filter(Anomaly.z_score >= min_z_score)
    if billing_code:
        query = query.filter(Anomaly.billing_code == billing_code)
    anomalies = query.order_by(Anomaly.z_score.desc()).offset(skip).limit(limit).all()
    return {"anomalies": [_anomaly_dict(a) for a in anomalies], "count": query.count()}


# --- Analytics ---


@app.get("/api/analytics/stats")
def get_billing_stats(
    billing_code: Optional[str] = None,
    state: str = "NY",
    db: Session = Depends(get_db),
):
    """Get billing statistics for a given state and optional code."""
    return calculate_billing_stats(db, state=state, billing_code=billing_code)


@app.get("/api/analytics/outliers")
def get_outliers(
    z_threshold: float = Query(3.0, ge=1.0),
    state: str = "NY",
    db: Session = Depends(get_db),
):
    """Detect outlier providers based on z-score threshold."""
    return detect_outliers(db, z_threshold=z_threshold, state=state)


@app.get("/api/analytics/trends")
def get_trends(
    billing_code: Optional[str] = None,
    state: str = "NY",
    db: Session = Depends(get_db),
):
    """Detect year-over-year billing trends."""
    return detect_yoy_trends(db, state=state, billing_code=billing_code)


@app.get("/api/analytics/compare/{provider_id}")
def compare_provider(provider_id: int, db: Session = Depends(get_db)):
    """Compare a provider against their peers."""
    return compare_provider_to_peers(db, provider_id)


@app.get("/api/analytics/fraud-patterns")
def get_fraud_patterns(
    provider_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Detect known fraud patterns."""
    return detect_fraud_patterns(db, provider_id=provider_id)


# --- Cases ---


@app.get("/api/cases")
def list_cases(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List whistleblower investigation cases."""
    query = db.query(Case)
    if status:
        query = query.filter(Case.status == status)
    cases = query.offset(skip).limit(limit).all()
    return {"cases": [_case_dict(c) for c in cases], "count": query.count()}


@app.post("/api/cases")
def create_case(
    case_id: str,
    facility_id: int,
    whistleblower_notes: str = "",
    db: Session = Depends(get_db),
):
    """Create a new investigation case."""
    case = Case(
        case_id=case_id,
        facility_id=facility_id,
        whistleblower_notes=whistleblower_notes,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return _case_dict(case)


@app.post("/api/cases/{case_id}/timeline")
def add_timeline_event(
    case_id: int,
    event_date: date,
    description: str,
    evidence_type: str = "",
    db: Session = Depends(get_db),
):
    """Add a timeline event to a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    event = TimelineEvent(
        case_id=case_id,
        event_date=event_date,
        description=description,
        evidence_type=evidence_type,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {
        "id": event.id,
        "event_date": str(event.event_date),
        "description": event.description,
        "evidence_type": event.evidence_type,
    }


@app.get("/api/export/provider/{provider_id}")
def export_provider_report(provider_id: int, db: Session = Depends(get_db)):
    """Export a summary report for a provider (JSON, suitable for PDF generation)."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    anomalies = (
        db.query(Anomaly).filter(Anomaly.provider_id == provider_id).all()
    )
    claims_count = (
        db.query(Claim).filter(Claim.provider_id == provider_id).count()
    )
    return {
        "provider": _provider_dict(provider),
        "total_claims": claims_count,
        "anomalies": [_anomaly_dict(a) for a in anomalies],
        "generated_at": str(date.today()),
    }


# --- Helpers ---


def _provider_dict(p: Provider) -> dict:
    return {
        "id": p.id,
        "npi": p.npi,
        "name": p.name,
        "address": p.address,
        "city": p.city,
        "state": p.state,
        "zip_code": p.zip_code,
        "facility_type": p.facility_type,
        "licensed_capacity": p.licensed_capacity,
    }


def _anomaly_dict(a: Anomaly) -> dict:
    return {
        "id": a.id,
        "provider_id": a.provider_id,
        "billing_code": a.billing_code,
        "z_score": a.z_score,
        "anomaly_type": a.anomaly_type,
        "notes": a.notes,
        "detected_at": str(a.detected_at) if a.detected_at else None,
    }


def _case_dict(c: Case) -> dict:
    return {
        "id": c.id,
        "case_id": c.case_id,
        "facility_id": c.facility_id,
        "status": c.status,
        "whistleblower_notes": c.whistleblower_notes,
        "evidence_summary": c.evidence_summary,
        "created_at": str(c.created_at) if c.created_at else None,
        "updated_at": str(c.updated_at) if c.updated_at else None,
    }
