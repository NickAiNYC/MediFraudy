"""Health check endpoint with database connectivity verification.

Provides a comprehensive health check that Railway, load balancers,
and monitoring systems can use to verify the service is operational.
"""

import logging

from fastapi import APIRouter
from sqlalchemy import text

from database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Return service health status with database connectivity check.

    Returns:
        200 with status "healthy" if all checks pass.
        503 with status "unhealthy" if database is unreachable.
    """
    from config import settings

    db_status = "connected"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Health check database failure: %s", e)
        db_status = "disconnected"

    status = "healthy" if db_status == "connected" else "unhealthy"
    status_code = 200 if status == "healthy" else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "version": "2.1.0",
            "environment": settings.ENVIRONMENT,
            "checks": {
                "database": db_status,
            },
        },
    )
