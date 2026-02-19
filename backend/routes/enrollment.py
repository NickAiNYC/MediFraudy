from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.cms_enrollment import update_dashboard_stats
import logging

router = APIRouter(prefix="/api/enrollment", tags=["enrollment"])
logger = logging.getLogger(__name__)

@router.post("/refresh")
async def refresh_enrollment_stats():
    """Manually trigger CMS data refresh"""
    try:
        # You'll need to inject your DB engine here
        from database import engine
        update_dashboard_stats(engine)
        return {"status": "success", "message": "Enrollment stats updated"}
    except Exception as e:
        logger.error(f"Failed to update enrollment stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest")
async def get_latest_enrollment():
    """Get the most recent enrollment stats"""
    from database import SessionLocal
    db = SessionLocal()
    result = db.execute(
        "SELECT month, total_enrollment, ny_enrollment FROM enrollment_stats ORDER BY month DESC LIMIT 1"
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="No enrollment data found")
    return {
        "month": result[0],
        "total_enrollment": result[1],
        "ny_enrollment": result[2]
    }