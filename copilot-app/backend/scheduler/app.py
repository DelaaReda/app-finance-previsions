"""
Scheduler for Finance Copilot - FC-OPS-001
Handles ALL scheduled jobs: news, forecasts, briefs, backtests, alerts
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
Task: FC-OPS-001 (+90 pts)
"""
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import logging
from pathlib import Path
import sys
import os

# Add the backend directory to path to access modules
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

# Import job functions with correct paths based on actual function names found
from jobs.news_ingest import run_news_ingest
from jobs.forecasts import run_forecasts_job
from jobs.weekly_brief import run_and_persist_weekly_brief
from jobs.backtests import ensure_backtests_up_to_date
from jobs.alerts import run_alerts_job

logger = logging.getLogger(__name__)

# Create the scheduler
scheduler = BackgroundScheduler()

# Job 1: News ingestion (every 15 minutes)
scheduler.add_job(
    run_news_ingest,
    'interval',
    minutes=15,
    id='news_ingest_job',
    name='News RSS Ingestion'
)

# Job 2: Forecasts generation (daily at 4 AM)
scheduler.add_job(
    run_forecasts_job,
    'cron',
    hour=4,
    minute=0,
    id='forecasts_generation_job',
    name='Daily Forecasts Generation'
)

# Job 3: Weekly brief (Sunday at 6 PM)
scheduler.add_job(
    run_and_persist_weekly_brief,
    'cron',
    day_of_week='sun',
    hour=18,
    minute=0,
    id='weekly_brief_job',
    name='Weekly Market Brief'
)

# Job 4: Backtests (daily at 3 AM, before forecasts)
scheduler.add_job(
    ensure_backtests_up_to_date,
    'cron',
    hour=3,
    minute=0,
    id='backtests_job',
    name='Daily Backtests Update'
)

# Job 5: Alerts detection (every 30 minutes)
scheduler.add_job(
    run_alerts_job,
    'interval',
    minutes=30,
    id='alerts_detection_job',
    name='Market Alerts Detection'
)

def start_scheduler():
    """Start the background scheduler with all jobs"""
    if not scheduler.running:
        scheduler.start()
        logger.info("="*70)
        logger.info("🚀 Finance Copilot Scheduler Started Successfully")
        logger.info("="*70)
        logger.info("Active Jobs:")

        for job in scheduler.get_jobs():
            logger.info(f"  ✓ {job.name}")
            logger.info(f"    ID: {job.id}")
            logger.info(f"    Next run: {job.next_run_time}")
            logger.info("")

        logger.info("="*70)
        logger.info(f"Total: {len(scheduler.get_jobs())} jobs scheduled")
        logger.info("="*70)

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped")

# For standalone execution
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    start_scheduler()
    logger.info("Scheduler running in standalone mode... Press Ctrl+C to exit")

    try:
        import time
        while True:
            time.sleep(60)  # Keep the main thread alive
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        stop_scheduler()
        logger.info("Scheduler stopped successfully")