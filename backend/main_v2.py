"""
Modern FastAPI application with 2026 architecture patterns
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from sqlalchemy import text

from fastapi import FastAPI, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from config import settings
from database_v2 import async_engine, get_async_db, check_database_health
from data_pipeline_v2 import modern_loader
from cache_manager import cache_manager, cached, cache_analytics_dashboard, get_cached_analytics_dashboard

# Configure Sentry for production
if settings.SENTRY_DSN and settings.ENVIRONMENT == "production":
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT
    )

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
DATA_LOAD_COUNT = Counter('data_loads_total', 'Total data loads')

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting MediFraudy v2.0")
    
    # Connect Redis cache
    await cache_manager.connect()
    
    # Database health check
    db_health = await check_database_health()
    logger.info(f"📊 Database status: {db_health['status']}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down MediFraudy v2.0")
    await cache_manager.disconnect()

# Modern FastAPI app
app = FastAPI(
    title="MediFraudy API v2.0",
    description="Modern Medicaid Fraud Intelligence Platform",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Middleware stack
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["backend-production-1380.up.railway.app", "test"]
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add performance headers and metrics"""
    start_time = time.time()
    
    response = await call_next(request)
    
    # Metrics
    process_time = time.time() - start_time
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    REQUEST_DURATION.observe(process_time)
    
    # Headers
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = str(uuid.uuid4())
    
    return response

# Dependencies

# Health endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check"""
    db_health = await check_database_health()
    
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_health,
        "timestamp": time.time()
    }

@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint"""
    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    
    return generate_latest()

# Modern API endpoints
@app.get("/api/v2/providers", tags=["Providers"])
async def get_providers_v2(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    """Get providers with modern filtering and pagination"""
    
    # Build query dynamically
    query = "SELECT * FROM providers WHERE 1=1"
    params = {}
    
    if state:
        query += " AND state = :state"
        params["state"] = state
    
    if city:
        query += " AND city ILIKE :city"
        params["city"] = f"%{city}%"
    
    query += " ORDER BY total_amount DESC LIMIT :limit OFFSET :skip"
    params["limit"] = limit
    params["skip"] = skip
    
    result = await db.execute(text(query), params)
    providers = result.fetchall()
    
    return {
        "providers": [row._asdict() for row in providers],
        "total": len(providers),
        "skip": skip,
        "limit": limit
    }

@app.get("/api/v2/analytics/dashboard", tags=["Analytics"])
async def get_dashboard_v2(
    db: AsyncSession = Depends(get_async_db)
):
    """Modern analytics dashboard with real-time metrics and caching"""
    
    # Try cache first
    cached_data = await get_cached_analytics_dashboard()
    if cached_data:
        logger.info("📊 Analytics dashboard served from cache")
        return cached_data
    
    # Optimized queries for dashboard
    queries = {
        "providers": "SELECT COUNT(*) FROM providers",
        "claims": "SELECT COUNT(*) FROM claims", 
        "total_billed": "SELECT COALESCE(SUM(amount), 0) FROM claims",
        "avg_claim_amount": "SELECT COALESCE(AVG(amount), 0) FROM claims",
        "top_states": """
            SELECT state, COUNT(*) as provider_count, SUM(total_amount) as total_amount
            FROM providers 
            WHERE state IS NOT NULL
            GROUP BY state 
            ORDER BY total_amount DESC 
            LIMIT 5
        """
    }
    
    results = {}
    for key, query in queries.items():
        result = await db.execute(text(query))
        if key == "top_states":
            results[key] = [row._asdict() for row in result.fetchall()]
        else:
            results[key] = result.scalar()
    
    dashboard_data = {
        "providers": results["providers"],
        "claims": results["claims"],
        "total_billed": float(results["total_billed"]),
        "avg_claim_amount": float(results["avg_claim_amount"]),
        "top_states": results["top_states"],
        "timestamp": time.time()
    }
    
    # Cache the result
    await cache_analytics_dashboard(dashboard_data)
    logger.info("📊 Analytics dashboard cached for 5 minutes")
    
    return dashboard_data

@app.post("/api/v2/data/load", tags=["Data"])
async def load_data_v2(
    background_tasks: BackgroundTasks,
    sample_size: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    """Modern data loading endpoint with background processing"""
    
    # Start background loading task
    background_tasks.add_task(
        load_data_background,
        sample_size=sample_size
    )
    
    DATA_LOAD_COUNT.inc()
    
    return {
        "status": "loading_started",
        "message": "Data loading started in background",
        "sample_size": sample_size
    }

async def load_data_background(sample_size: Optional[int] = None):
    """Background data loading task"""
    try:
        logger.info(f"🚀 Starting background data load (sample: {sample_size})")
        
        # Use modern loader
        claims_loaded = await modern_loader.load_dataset(
            zip_path="/tmp/medicaid_claims.zip",
            sample_size=sample_size
        )
        
        logger.info(f"✅ Background load completed: {claims_loaded:,} claims")
        
    except Exception as e:
        logger.error(f"❌ Background load failed: {e}")
        raise

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request.headers.get("X-Request-ID"),
            "timestamp": time.time()
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main_v2:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=1,  # Single worker for async
        reload=settings.DEBUG,
        access_log=settings.DEBUG
    )
