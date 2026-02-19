"""
API endpoints for Railway data loading with progress monitoring.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
import logging
from pathlib import Path

from core.security import get_current_user
from models import User

logger = logging.getLogger(__name__)

router = APIRouter()


class DataLoadRequest(BaseModel):
    """Request to start data loading."""
    zip_path: str = Field(..., description="Path to ZIP file on Railway volume")
    state_filter: str = Field("NY", description="Filter to specific state")
    resume: bool = Field(True, description="Resume from last checkpoint")
    max_rows: Optional[int] = Field(None, description="Limit rows (for testing)")


class DataLoadResponse(BaseModel):
    """Response from data load initiation."""
    task_id: str
    status: str
    message: str
    estimated_hours: Optional[float] = None


class DataLoadProgress(BaseModel):
    """Data loading progress information."""
    task_id: Optional[str] = None
    status: str
    rows_loaded: int
    last_checkpoint: int
    updated_at: Optional[str] = None
    file_size_gb: Optional[float] = None
    estimated_completion: Optional[str] = None


@router.post("/start", response_model=DataLoadResponse)
async def start_data_load(
    request: DataLoadRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Start loading 77M Medicaid claims data in background.
    
    This endpoint triggers a Celery task that:
    - Streams from ZIP without full extraction
    - Processes in 10k row chunks
    - Saves checkpoints every 50k rows
    - Can resume from last checkpoint on crash
    
    **Railway Setup Required:**
    1. Upload ZIP to Railway volume: `/data/medicaid_claims.zip`
    2. Ensure Celery worker is running
    3. Monitor progress via `/data-loading/progress` endpoint
    
    **Estimated Time:** 2-4 hours for 77M rows on Railway
    """
    # Only Partners can trigger data loads
    if current_user.role not in ["Partner", "Admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only Partners can initiate data loading"
        )
    
    # Verify file exists
    if not Path(request.zip_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"ZIP file not found: {request.zip_path}. "
                   f"Upload to Railway volume first."
        )
    
    # Check file size
    file_size_gb = Path(request.zip_path).stat().st_size / (1024**3)
    logger.info(f"Starting data load for {file_size_gb:.2f} GB file")
    
    # Trigger Celery task
    try:
        from tasks import load_railway_data
        
        task = load_railway_data.apply_async(
            kwargs={
                "zip_path": request.zip_path,
                "state_filter": request.state_filter,
                "resume": request.resume,
                "max_rows": request.max_rows
            }
        )
        
        # Estimate completion time
        from services.railway_data_loader import estimate_load_time
        estimate = estimate_load_time(file_size_gb * 3)  # Uncompressed is ~3x
        
        return DataLoadResponse(
            task_id=task.id,
            status="started",
            message=f"Data loading started. Task ID: {task.id}",
            estimated_hours=estimate.get("estimated_hours")
        )
        
    except Exception as e:
        logger.error(f"Failed to start data load: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start data load: {str(e)}"
        )


@router.get("/progress", response_model=DataLoadProgress)
async def get_data_load_progress(
    task_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get current data loading progress.
    
    If task_id is provided, gets progress for that specific task.
    Otherwise, returns the most recent loading progress.
    """
    try:
        import redis
        from config import settings
        
        redis_client = redis.from_url(settings.REDIS_URL)
        
        # Get progress from Redis
        if task_id:
            progress_key = f"data_load_progress:{task_id}"
        else:
            # Find most recent progress key
            keys = redis_client.keys("data_load_progress:*")
            if not keys:
                return DataLoadProgress(
                    status="not_started",
                    rows_loaded=0,
                    last_checkpoint=0
                )
            progress_key = keys[0].decode() if isinstance(keys[0], bytes) else keys[0]
        
        progress_json = redis_client.get(progress_key)
        
        if not progress_json:
            return DataLoadProgress(
                task_id=task_id,
                status="not_found",
                rows_loaded=0,
                last_checkpoint=0
            )
        
        import json
        progress = json.loads(progress_json)
        
        return DataLoadProgress(
            task_id=task_id,
            status=progress.get("status", "unknown"),
            rows_loaded=progress.get("rows_loaded", 0),
            last_checkpoint=progress.get("last_checkpoint", 0),
            updated_at=progress.get("updated_at"),
            file_size_gb=progress.get("file_size_gb")
        )
        
    except redis.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Redis not available. Cannot retrieve progress."
        )
    except Exception as e:
        logger.error(f"Failed to get progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get progress: {str(e)}"
        )


@router.post("/resume")
async def resume_data_load(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Resume a failed or interrupted data load from last checkpoint.
    """
    if current_user.role not in ["Partner", "Admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only Partners can resume data loading"
        )
    
    try:
        import redis
        from config import settings
        from tasks import load_railway_data
        
        redis_client = redis.from_url(settings.REDIS_URL)
        
        # Get previous progress
        progress_key = f"data_load_progress:{task_id}"
        progress_json = redis_client.get(progress_key)
        
        if not progress_json:
            raise HTTPException(
                status_code=404,
                detail=f"No progress found for task {task_id}"
            )
        
        import json
        progress = json.loads(progress_json)
        
        # Start new task with resume
        new_task = load_railway_data.apply_async(
            kwargs={
                "zip_path": os.getenv("MEDICAID_DATASET_PATH", "/data/medicaid_claims.zip"),
                "state_filter": "NY",
                "resume": True,
                "max_rows": None
            }
        )
        
        return {
            "task_id": new_task.id,
            "status": "resumed",
            "message": f"Resuming from row {progress.get('last_checkpoint', 0):,}",
            "previous_task_id": task_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume data load: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume: {str(e)}"
        )


@router.get("/stats")
async def get_data_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get current database statistics.
    
    Returns counts of providers, claims, and data quality metrics.
    """
    try:
        from database import SessionLocal
        from models import Provider, Claim
        from sqlalchemy import func, text
        
        db = SessionLocal()
        
        try:
            # Get counts
            provider_count = db.query(Provider).count()
            claim_count = db.query(Claim).count()
            
            # Get state distribution
            state_dist = db.query(
                Provider.state,
                func.count(Provider.id).label('count')
            ).group_by(Provider.state).order_by(func.count(Provider.id).desc()).limit(10).all()
            
            # Get NYC-specific stats
            nyc_providers = db.query(Provider).filter(
                Provider.state == 'NY',
                Provider.city.in_(['NEW YORK', 'BROOKLYN', 'QUEENS', 'BRONX', 'STATEN ISLAND'])
            ).count()
            
            # Get date range
            date_range = db.query(
                func.min(Claim.claim_date).label('earliest'),
                func.max(Claim.claim_date).label('latest')
            ).first()
            
            return {
                "providers": {
                    "total": provider_count,
                    "nyc": nyc_providers,
                    "by_state": [{"state": s, "count": c} for s, c in state_dist]
                },
                "claims": {
                    "total": claim_count,
                    "earliest_date": str(date_range.earliest) if date_range.earliest else None,
                    "latest_date": str(date_range.latest) if date_range.latest else None
                },
                "data_quality": {
                    "providers_with_claims": db.query(Provider).join(Claim).distinct().count(),
                    "avg_claims_per_provider": round(claim_count / provider_count, 2) if provider_count > 0 else 0
                }
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.delete("/clear")
async def clear_data(
    confirm: str,
    current_user: User = Depends(get_current_user)
):
    """
    Clear all claims and providers data.
    
    **WARNING:** This is destructive and cannot be undone.
    
    Requires confirmation string: "DELETE_ALL_DATA"
    """
    if current_user.role not in ["Partner", "Admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only Partners can clear data"
        )
    
    if confirm != "DELETE_ALL_DATA":
        raise HTTPException(
            status_code=400,
            detail="Invalid confirmation. Must be 'DELETE_ALL_DATA'"
        )
    
    try:
        from database import SessionLocal, Base, engine
        from models import Claim, Provider
        
        db = SessionLocal()
        
        try:
            # Get counts before deletion
            claim_count = db.query(Claim).count()
            provider_count = db.query(Provider).count()
            
            # Delete all data
            db.query(Claim).delete()
            db.query(Provider).delete()
            db.commit()
            
            logger.warning(f"Data cleared by {current_user.email}: {claim_count} claims, {provider_count} providers")
            
            return {
                "status": "cleared",
                "claims_deleted": claim_count,
                "providers_deleted": provider_count,
                "message": "All data has been cleared"
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to clear data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear data: {str(e)}"
        )
