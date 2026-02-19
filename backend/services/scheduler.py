from apscheduler.schedulers.background import BackgroundScheduler
from services.cms_enrollment import update_dashboard_stats
from database import engine
import logging

logger = logging.getLogger(__name__)

def scheduled_enrollment_update():
    """Run every 30 days to keep enrollment data fresh"""
    logger.info("Running scheduled enrollment data update...")
    try:
        update_dashboard_stats(engine)
        logger.info("Scheduled update completed successfully")
    except Exception as e:
        logger.error(f"Scheduled update failed: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(
    scheduled_enrollment_update,
    'interval',
    days=30,
    id='enrollment_updater',
    replace_existing=True
)

def start_scheduler():
    scheduler.start()
    logger.info("Scheduler started - will update enrollment data every 30 days")