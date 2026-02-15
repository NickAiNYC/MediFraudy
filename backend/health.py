"""
Health check endpoint for Railway and monitoring systems.
Tests critical dependencies: database, Redis, file system.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from datetime import datetime
import os
import psutil
from typing import Dict, Any

from database import SessionLocal
from config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Comprehensive health check endpoint.
    
    Returns:
        200: All systems operational
        503: One or more systems degraded
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
        "checks": {}
    }
    
    # Database connectivity check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["checks"]["database"] = "connected"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Redis connectivity check (if enabled)
    if settings.REDIS_URL:
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL, socket_timeout=5)
            redis_client.ping()
            health_status["checks"]["redis"] = "connected"
        except Exception as e:
            health_status["checks"]["redis"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
    
    # System resources check
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        health_status["checks"]["system"] = {
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "cpu_count": psutil.cpu_count()
        }
        
        # Warn if resources critical
        if memory.percent > 90 or disk.percent > 90:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["system"] = f"error: {str(e)}"
    
    # Response status code
    status_code = (
        status.HTTP_200_OK if health_status["status"] == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    
    return JSONResponse(content=health_status, status_code=status_code)


@router.get("/health/ready")
async def readiness_check() -> JSONResponse:
    """
    Kubernetes-style readiness probe.
    Checks if app is ready to receive traffic.
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return JSONResponse({"ready": True}, status_code=200)
    except:
        return JSONResponse({"ready": False}, status_code=503)


@router.get("/health/live")
async def liveness_check() -> JSONResponse:
    """
    Kubernetes-style liveness probe.
    Checks if app is alive (should restart if fails).
    """
    return JSONResponse({"alive": True}, status_code=200)
