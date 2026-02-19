"""FastAPI application for MediFraudy — NYC Medicaid Fraud Intelligence Operating System.

Masterclass Engineered. Palantir-Weaponized. Built for Law Offices.

Primary users: Qui tam law firms, litigation boutiques, compliance groups,
whistleblower attorneys.

Core value: Turn raw Medicaid claims data into litigation-ready fraud intelligence.
"""

import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

# Import settings first
from config import settings

# Core modules
from core.logging_config import setup_logging
from core.middleware import RateLimitMiddleware, AuditLoggingMiddleware

# Database
from database import get_db, engine, Base

# Health check
from health import router as health_router

# Models (imported for metadata but not directly used)
from models import (
    Provider, Claim, Anomaly, Case, TimelineEvent,
    InvestigationCase, ProviderScreening, PeerGroup,
    AssociationRule, ComplianceAudit, EVVLog
)

# Routes
from routes.export import router as export_router
from routes import graph
from routes import nemt
from routes import cases
from routes import analytics_trigger
from routes import homecare
from routes.data_quality import router as data_quality_router
from routes.enrollment import router as enrollment_router

# API v1 routes
from api.v1.routes.intelligence import router as intelligence_router
from api.v1.routes.auth import router as auth_router
from api.v1.routes.agent import router as agent_router
from api.v1.routes.data_loading import router as data_loading_router
from simple_load_endpoint import create_simple_load_router

# Analytics modules
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
            release=f"medifraudy@2.0.0"
        )
except ImportError:
    pass

# Structured logging setup
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Replaces deprecated @app.on_event decorators.
    """
    logger.info("Starting MediFraudy API...")
    
    # Validate critical environment variables
    required_vars = ["DATABASE_URL", "SECRET_KEY", "JWT_SECRET_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars and settings.ENVIRONMENT == "production":
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    # Test database connection
    try:
        with engine.connect() as conn:
            # CRITICAL FIX: Wrap raw SQL in text() for SQLAlchemy 2.0 compatibility
            result = conn.execute(text("SELECT 1"))
            result.scalar()  # Fetch the result to ensure connection works
        logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        if settings.ENVIRONMENT == "production":
            sys.exit(1)
        # In development, continue anyway
        logger.warning("⚠️ Continuing despite database connection failure (development mode)")
    
    # Create database tables on startup (if they don't exist)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables verified/created")
    except Exception as e:
        logger.error(f"⚠️ Database table creation issue: {e}")
        # Non-fatal, tables may already exist
    
    logger.info("🚀 MediFraudy API started successfully")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down MediFraudy API...")
    engine.dispose()
    logger.info("✅ Database connections closed")


# Create FastAPI app with lifespan
app = FastAPI(
    title="MediFraudy — NYC Medicaid Fraud Intelligence Operating System",
    description=(
        "Enterprise-grade fraud intelligence for NYC Medicaid litigation. "
        "4-layer detection engine, graph intelligence, litigation automation, "
        "and evidence generation for qui tam / whistleblower law firms."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else "/docs",
    redoc_url="/api/redoc" if settings.DEBUG else "/redoc",
)

# Include health router first (no middleware)
app.include_router(health_router, prefix="/api/health", tags=["Health"])

# CORS Middleware - Dynamic origins from config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time", "X-Total-Count"]
)

# Trusted Host Middleware (prevent host header attacks)
if not settings.DEBUG:
    allowed_hosts = [
        "medifraudy-api-production.up.railway.app",
        "*.railway.app",
        "localhost",
        "127.0.0.1"
    ]
    try:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )
        logger.info("✅ TrustedHostMiddleware configured")
    except Exception as e:
        logger.warning(f"⚠️ Could not add TrustedHostMiddleware: {e}")


# Request ID and timing middleware
@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    """Add request ID and timing to all requests"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "request_id": request_id}
        )
    
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{process_time:.3f}s"
    
    # Log slow requests
    if process_time > 1.0:
        logger.warning(
            f"Slow request: {request.method} {request.url.path} "
            f"took {process_time:.2f}s (ID: {request_id})"
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
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(f"Unhandled exception: {exc} (Request ID: {request_id})", exc_info=True)
    
    # Report to Sentry
    try:
        if settings.SENTRY_DSN:
            import sentry_sdk
            sentry_sdk.set_tag("request_id", request_id)
            sentry_sdk.capture_exception(exc)
    except Exception as e:
        logger.debug(f"Sentry reporting failed: {e}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id
        }
    )


# Enterprise middleware — rate limiting & audit logging
if not settings.DEBUG:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=120,
        enabled=True,
    )
    app.add_middleware(
        AuditLoggingMiddleware,
        enabled=True,
    )
    logger.info("✅ Rate limiting and audit logging enabled")


# Include all routers
app.include_router(export_router, prefix="/api", tags=["Export"])
app.include_router(graph.router, prefix="/api", tags=["Graph", "FraudRings"])
app.include_router(nemt.router, prefix="/api", tags=["NEMT"])
app.include_router(cases.router, prefix="/api", tags=["Cases", "Investigation"])
app.include_router(analytics_trigger.router, prefix="/api", tags=["Analytics"])
app.include_router(homecare.router, prefix="/api", tags=["Home Care"])
app.include_router(data_quality_router, prefix="/api", tags=["Data Quality"])
app.include_router(enrollment_router, prefix="/api", tags=["Enrollment", "CMS"])
app.include_router(intelligence_router, prefix="/api/v1", tags=["Intelligence", "v1"])
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication", "v1"])
app.include_router(agent_router, prefix="/api/v1", tags=["AI Agent", "v1"])
app.include_router(data_loading_router, prefix="/api/v1/data-loading", tags=["Data Loading", "v1"])
app.include_router(create_simple_load_router(), prefix="/api/temp", tags=["Temporary Loader"])

# Include health router again at root for Railway healthcheck
app.include_router(health_router, prefix="/health", tags=["Health"])


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "service": "MediFraudy API",
        "version": "2.0.0",
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "/redoc",
        "health": "/health",
        "endpoints": {
            "providers": "/api/providers",
            "cases": "/api/cases",
            "fraud_rings": "/api/graph/fraud-rings",
            "intelligence": "/api/v1/intelligence",
            "auth": "/api/v1/auth",
            "agent": "/api/v1/agent"
        }
    }


# --- Simple ping endpoint for Railway healthcheck ---
@app.get("/ping", tags=["Health"])
async def ping():
    """Simple ping endpoint for Railway healthcheck"""
    return {"ping": "pong", "timestamp": time.time()}


@app.get("/api/admin/run-migration")
async def run_migration():
    """TEMPORARY - delete after running once"""
    import psycopg2
    import os
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        cur.execute("""
            ALTER TABLE claims 
            ADD COLUMN IF NOT EXISTS provider_id INTEGER REFERENCES providers(id)
        """)
        conn.commit()
        
        # Check what columns exist now
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'claims' 
            ORDER BY ordinal_position
        """)
        columns = [{"column": r[0], "type": r[1]} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return {"status": "done", "claims_columns": columns}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/ready", tags=["Health"])
async def ready():
    """Readiness probe - checks if app is ready to accept traffic"""
    try:
        # Quick database check
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={"status": "ready", "database": "connected"}
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "database": "disconnected"}
        )


# --- Providers Endpoints ---
@app.get("/api/providers", tags=["Providers"])
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
    total = query.count()
    providers = query.offset(skip).limit(limit).all()
    return {
        "providers": [_provider_dict(p) for p in providers],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@app.get("/api/providers/{provider_id}", tags=["Providers"])
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    """Get detailed information for a single provider."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _provider_dict(provider)


# --- Anomalies Endpoints ---
@app.get("/api/anomalies", tags=["Anomalies"])
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
    total = query.count()
    anomalies = query.order_by(Anomaly.z_score.desc()).offset(skip).limit(limit).all()
    return {
        "anomalies": [_anomaly_dict(a) for a in anomalies],
        "total": total,
        "skip": skip,
        "limit": limit
    }


# --- Analytics Endpoints ---
@app.get("/api/analytics/stats", tags=["Analytics"])
def get_billing_stats(
    billing_code: Optional[str] = None,
    state: str = "NY",
    db: Session = Depends(get_db),
):
    """Get billing statistics for a given state and optional code."""
    return calculate_billing_stats(db, state=state, billing_code=billing_code)


@app.get("/api/analytics/outliers", tags=["Analytics"])
def get_outliers(
    z_threshold: float = Query(3.0, ge=1.0),
    state: str = "NY",
    db: Session = Depends(get_db),
):
    """Detect outlier providers based on z-score threshold."""
    return detect_outliers(db, z_threshold=z_threshold, state=state)


@app.get("/api/analytics/trends", tags=["Analytics"])
def get_trends(
    billing_code: Optional[str] = None,
    state: str = "NY",
    db: Session = Depends(get_db),
):
    """Detect year-over-year billing trends."""
    return detect_yoy_trends(db, state=state, billing_code=billing_code)


@app.get("/api/analytics/compare/{provider_id}", tags=["Analytics"])
def compare_provider(provider_id: int, db: Session = Depends(get_db)):
    """Compare a provider against their peers."""
    return compare_provider_to_peers(db, provider_id)


@app.get("/api/analytics/fraud-patterns", tags=["Analytics"])
def get_fraud_patterns(
    provider_id: Optional[int] = None,
    limit: Optional[int] = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Detect known fraud patterns.
    
    If provider_id is not specified, scans the top 'limit' providers by claim volume.
    """
    return detect_fraud_patterns(db, provider_id=provider_id, limit=limit)


@app.get("/api/analytics/pattern-of-life/{provider_id}", tags=["Analytics"])
def get_pattern_of_life(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Run comprehensive pattern-of-life analysis for a provider."""
    return comprehensive_pattern_analysis(db, provider_id, lookback_days)


@app.get("/api/analytics/capacity-violations/{provider_id}", tags=["Analytics"])
def get_capacity_violations(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Detect capacity violations (Queens case pattern)."""
    return detect_capacity_violations(db, provider_id, lookback_days)


@app.get("/api/analytics/kickback-patterns/{provider_id}", tags=["Analytics"])
def get_kickback_patterns(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Detect kickback scheme indicators (Brooklyn case pattern)."""
    return detect_kickback_patterns(db, provider_id, lookback_days)


@app.get("/api/analytics/behavioral-patterns/{provider_id}", tags=["Analytics"])
def get_behavioral_patterns(
    provider_id: int,
    lookback_days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Analyze behavioral patterns (weekend billing, batch submissions)."""
    return analyze_behavioral_patterns(db, provider_id, lookback_days)


@app.get("/api/analytics/nyc-elderly-care-sweep", tags=["Analytics"])
def get_nyc_sweep(
    min_risk_score: int = Query(50, ge=0, le=100),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Analyze all NYC elderly care facilities for pattern-of-life anomalies."""
    return analyze_nyc_elderly_care_facilities(db, min_risk_score, limit)


# --- Cases Endpoints ---
@app.get("/api/cases", tags=["Cases"])
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
    total = query.count()
    cases = query.offset(skip).limit(limit).all()
    return {
        "cases": [_case_dict(c) for c in cases],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@app.post("/api/cases", tags=["Cases"])
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


@app.get("/api/cases/queue/investigation", tags=["Cases", "Investigation"])
def get_investigation_queue(
    sort_by: str = Query("priority", pattern="^(priority|created|risk)$"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get queue of cases needing investigation, prioritized by risk."""
    # This is a placeholder - implement based on your business logic
    cases = db.query(Case).filter(Case.status.in_(["new", "under_review"])).limit(limit).all()
    return {
        "queue": [_case_dict(c) for c in cases],
        "total": len(cases),
        "sort_by": sort_by
    }


@app.post("/api/cases/{case_id}/timeline", tags=["Cases"])
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


# --- Helper Functions ---
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
        "z_score": round(a.z_score, 2) if a.z_score else None,
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
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info"
    )
