"""
Celery tasks for background job processing.
"""

from celery import Celery
from celery.schedules import crontab
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    "medifraudy",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/New_York",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minute hard limit
    task_soft_time_limit=540,  # 9 minute soft limit
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_prefetch_multiplier=4,
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True
)


@celery_app.task(name="tasks.generate_evidence_package_async", bind=True, max_retries=3)
def generate_evidence_package_async(self, provider_id: str, user_id: int):
    """
    Generate evidence package in background.
    
    Args:
        provider_id: Provider to generate evidence for
        user_id: User requesting the evidence
    
    Returns:
        dict: Generated evidence package
    """
    from database import SessionLocal
    from services.evidence_builder import generate_case_package
    from services.evidence_integrity import evidence_integrity
    from datetime import datetime
    
    db = SessionLocal()
    try:
        logger.info(f"Starting evidence generation for provider {provider_id}")
        
        # Generate package ID
        package_id = f"EVD-{provider_id}-{int(datetime.utcnow().timestamp())}"
        
        # Build package
        package = generate_case_package(db, int(provider_id))
        
        # Sign package
        signed_package = evidence_integrity.sign_package(
            package_id=package_id,
            package_data=package,
            user_id=user_id,
            db=db
        )
        
        logger.info(f"Evidence package generated: {package_id}")
        
        return signed_package
        
    except Exception as e:
        logger.error(f"Evidence generation failed: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


@celery_app.task(name="tasks.batch_risk_score_update")
def batch_risk_score_update():
    """
    Update risk scores for all active providers.
    Runs nightly to keep scores fresh.
    """
    from database import SessionLocal
    from services.risk_scoring import calculate_risk_score
    from models import Provider
    
    db = SessionLocal()
    try:
        logger.info("Starting batch risk score update")
        
        # Get all providers
        providers = db.query(Provider).all()
        
        updated_count = 0
        for provider in providers:
            try:
                score_result = calculate_risk_score(db, provider.id)
                
                # Update provider risk score
                provider.risk_score = score_result.get("risk_score", 0)
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to update risk score for provider {provider.id}: {e}")
                continue
        
        db.commit()
        logger.info(f"Batch risk score update complete: {updated_count} providers updated")
        
        return {"updated": updated_count, "total": len(providers)}
        
    except Exception as e:
        logger.error(f"Batch risk score update failed: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="tasks.cleanup_old_audit_logs")
def cleanup_old_audit_logs(retention_days: int = 2555):  # 7 years for HIPAA
    """
    Archive or delete old audit logs.
    HIPAA requires 6+ years retention.
    """
    from database import SessionLocal
    from datetime import datetime, timedelta
    from models import AuditLog
    
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Delete old logs
        deleted_count = db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} audit logs older than {retention_days} days")
        
        return {"deleted": deleted_count}
        
    except Exception as e:
        logger.error(f"Audit log cleanup failed: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


# Celery Beat Schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    "batch-risk-score-update-nightly": {
        "task": "tasks.batch_risk_score_update",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
    "cleanup-audit-logs-weekly": {
        "task": "tasks.cleanup_old_audit_logs",
        "schedule": crontab(day_of_week=0, hour=3, minute=0),  # Sunday 3 AM
    },
}
