"""FastAPI application for MediFraudy — NYC Medicaid Fraud Intelligence Operating System.

Masterclass Engineered. Palantir-Weaponized. Built for Law Offices.

Primary users: Qui tam law firms, litigation boutiques, compliance groups,
whistleblower attorneys.

Core value: Turn raw Medicaid claims data into litigation-ready fraud intelligence.
"""

import logging
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional
import time
import sys
import uuid

from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from config import settings
from core.logging_config import setup_logging
from core.middleware import RateLimitMiddleware, AuditLoggingMiddleware
from database import get_db, engine, Base
from health import router as health_router
from models import (
    Provider, Claim, Anomaly, Case, TimelineEvent,
    InvestigationCase, ProviderScreening, PeerGroup,
    AssociationRule, ComplianceAudit, EVVLog
)
from routes.export import router as export_router
from routes import graph
from routes import nemt
from routes import cases
from routes import analytics_trigger
from routes import homecare
from routes.api_keys import router as api_keys_router
from routes.data_quality import router as data_quality_router
from api.v1.routes.intelligence import router as intelligence_router
from api.v1.routes.auth import router as auth_router
from api.v1.routes.agent import router as agent_router
from health import router as health_router
from analytics.statistical import (
    calculate_billing_stats,
    detect_outliers,
    detect_yoy_trends,
)
from analytics.comparison import compare_provider_to_peers
from analytics.patterns import detect_fraud_patterns
from analytics.pattern_of_life import (
    comprehensive_pattern_analysis,
    analyze_nyc_elderly_care_facilities,
    detect_capacity_violations,
    detect_kickback_patterns,
    analyze_behavioral_patterns,
)

# Sentry for error tracking
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration()
            ],
            traces_sample_rate=0.1,
            environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
            release=f"medifraudy@1.0.0"
        )
except ImportError:
    pass

# Structured logging setup
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events.
    Validates environment, connects to dependencies.
    """
    logger.info("Starting MediFraudy API...")
    
    # Validate critical environment variables
    required_vars = ["DATABASE_URL", "SECRET_KEY"]
    missing_vars = [var for var in required_vars if not getattr(settings, var.upper(), None)]
    if missing_vars and settings.ENVIRONMENT == "production":
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    # Test database connection
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        if settings.ENVIRONMENT == "production":
            sys.exit(1)
    
    # Create database tables on startup
    Base.metadata.create_all(bind=engine)
    
    logger.info("MediFraudy API started successfully")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down MediFraudy API...")
    engine.dispose()


app = FastAPI(
    title="MediFraudy — NYC Medicaid Fraud Intelligence Operating System",
    description=(
        "Enterprise-grade fraud intelligence for NYC Medicaid litigation. "
        "4-layer detection engine, graph intelligence, litigation automation, "
        "and evidence generation for qui tam / whistleblower law firms."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# Include health router first (no middleware)
app.include_router(health_router)

# CORS Middleware
cors_origins = settings.CORS_ORIGINS
if isinstance(cors_origins, str):
    cors_origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"]
)

# Trusted Host Middleware (prevent host header attacks)
if not settings.DEBUG:
    allowed_hosts = ["*"] if cors_origins == ["*"] else [origin.replace("https://", "").replace("http://", "") for origin in cors_origins]
    try:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )
    except:
        pass  # TrustedHostMiddleware may not be available in all environments

# Request ID and timing middleware
@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    """Add request ID and timing to all requests"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 1.0:
        logger.warning(
            f"Slow request: {request.method} {request.url.path} "
            f"took {process_time:.2f}s"
        )
    
    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler with Sentry logging"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Report to Sentry
    try:
        if settings.SENTRY_DSN:
            import sentry_sdk
            sentry_sdk.capture_exception(exc)
    except:
        pass
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# Enterprise middleware — rate limiting & audit logging
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=120,
    enabled=not settings.is_development,
)
app.add_middleware(
    AuditLoggingMiddleware,
    enabled=True,
)


# Include routers
app.include_router(export_router, prefix="/api")
app.include_router(graph.router)
app.include_router(nemt.router)
app.include_router(cases.router)
app.include_router(analytics_trigger.router)
app.include_router(homecare.router)
app.include_router(intelligence_router)
app.include_router(auth_router)
app.include_router(agent_router)


# --- Root Endpoint ---

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "MediFraudy API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/api/docs" if settings.DEBUG else None
    }


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
    limit: Optional[int] = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Detect known fraud patterns.
    
    If provider_id is not specified, scans the top 'limit' providers by claim volume.
    """
    return detect_fraud_patterns(db, provider_id=provider_id, limit=limit)


@app.get("/api/analytics/pattern-of-life/{provider_id}")
def get_pattern_of_life(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Run comprehensive pattern-of-life analysis for a provider."""
    return comprehensive_pattern_analysis(db, provider_id, lookback_days)


@app.get("/api/analytics/capacity-violations/{provider_id}")
def get_capacity_violations(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Detect capacity violations (Queens case pattern)."""
    return detect_capacity_violations(db, provider_id, lookback_days)


@app.get("/api/analytics/kickback-patterns/{provider_id}")
def get_kickback_patterns(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Detect kickback scheme indicators (Brooklyn case pattern)."""
    return detect_kickback_patterns(db, provider_id, lookback_days)


@app.get("/api/analytics/behavioral-patterns/{provider_id}")
def get_behavioral_patterns(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Analyze behavioral patterns (weekend billing, batch submissions)."""
    return analyze_behavioral_patterns(db, provider_id, lookback_days)


@app.get("/api/analytics/nyc-elderly-care-sweep")
def get_nyc_sweep(
    min_risk_score: int = Query(50, ge=0, le=100),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Analyze all NYC elderly care facilities for pattern-of-life anomalies."""
    return analyze_nyc_elderly_care_facilities(db, min_risk_score, limit)


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
    provider_id: int,
    whistleblower_notes: str = "",
    db: Session = Depends(get_db),
):
    """Create a new investigation case."""
    case = Case(
        case_id=case_id,
        provider_id=provider_id,
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
        "provider_id": c.provider_id,
        "status": c.status,
        "whistleblower_notes": c.whistleblower_notes,
        "evidence_summary": c.evidence_summary,
        "created_at": str(c.created_at) if c.created_at else None,
        "updated_at": str(c.updated_at) if c.updated_at else None,
    }


if __name__ == "__main__":
    import uvicorn
    import os
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.DEBUG
    )
