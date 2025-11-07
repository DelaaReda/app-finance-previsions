"""
Scheduler module for managing recurring jobs in the Finance Copilot system.
Handles news refresh, forecasts, brief reports, backtests, and model watcher refreshes.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
import atexit
import os
import sys
from pathlib import Path

# Ensure src/ is importable for agents.*
BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = BACKEND_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Configure logging for scheduler
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the actual job modules
from backend.jobs.news_ingest import run_news_ingest
from backend.jobs.forecasts import run_forecasts_job
from backend.jobs.weekly_brief import run_weekly_brief_job
from backend.jobs.backtests import run_backtests_job
from backend.storage.io import save_json
from agents.g4f_model_watcher import refresh as refresh_g4f_models

class JobScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """
        Set up all scheduled jobs with their cron schedules
        """
        # News refresh job - every 15 minutes
        self.scheduler.add_job(
            func=self._run_news_refresh_job,
            trigger="interval",
            minutes=15,  # Every 15 minutes
            id='news_refresh_job',
            name='Refresh news feed data',
            replace_existing=True
        )
        logger.info("Scheduled news refresh job every 15 minutes")
        
        # Forecasts job - daily at 2 AM
        self.scheduler.add_job(
            func=self._run_forecasts_job,
            trigger="cron",
            hour=2,
            minute=0,  # Daily at 2:00 AM
            id='forecasts_job',
            name='Generate daily forecasts',
            replace_existing=True
        )
        logger.info("Scheduled forecasts job daily at 2:00 AM")
        
        # Weekly brief job - Sundays at 11:30 PM
        self.scheduler.add_job(
            func=self._run_weekly_brief_job,
            trigger="cron",
            day_of_week='sun',
            hour=23,
            minute=30,  # Sundays at 23:30
            id='weekly_brief_job',
            name='Generate weekly market brief',
            replace_existing=True
        )
        logger.info("Scheduled weekly brief job Sundays at 23:30")
        
        # Backtests job - weekly on Wednesdays at 3:00 AM
        self.scheduler.add_job(
            func=self._run_backtests_job,
            trigger="cron",
            day_of_week='wed',
            hour=3,
            minute=0,  # Wednesdays at 3:00 AM
            id='backtests_job',
            name='Run backtests validation',
            replace_existing=True
        )
        logger.info("Scheduled backtests job Wednesdays at 3:00 AM")
        
        # G4F model watcher job - interval (default 120 minutes)
        watcher_interval_minutes = int(os.getenv("G4F_WATCHER_INTERVAL_MINUTES", "120") or "0")
        if watcher_interval_minutes > 0:
            self.scheduler.add_job(
                func=self._run_g4f_watcher_job,
                trigger="interval",
                minutes=watcher_interval_minutes,
                id='g4f_watcher_job',
                name='Refresh G4F model working list',
                replace_existing=True
            )
            logger.info("Scheduled G4F watcher job every %s minutes", watcher_interval_minutes)
    
    def _run_news_refresh_job(self):
        """
        Run news refresh job with error handling and logging
        """
        try:
            logger.info("Starting news refresh job...")
            start_time = datetime.utcnow()
            result = run_news_ingest()
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Create job metadata
            job_metadata = {
                "job_id": "news_refresh_job",
                "start_time": start_time.isoformat() + "Z",
                "end_time": datetime.utcnow().isoformat() + "Z",
                "duration_seconds": duration,
                "status": "success",
                "result_summary": result
            }
            
            # Save job metadata to persistent storage
            save_json("job_news_refresh", job_metadata, source=["scheduler", "news_refresh"])
            logger.info(f"News refresh job completed successfully in {duration:.2f}s")
        except Exception as e:
            logger.error(f"News refresh job failed: {str(e)}", exc_info=True)
            job_metadata = {
                "job_id": "news_refresh_job",
                "start_time": datetime.utcnow().isoformat() + "Z",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            save_json("job_news_refresh", job_metadata, source=["scheduler", "news_refresh", "error"])
    
    def _run_forecasts_job(self):
        """
        Run forecasts job with error handling and logging
        """
        try:
            logger.info("Starting forecasts job...")
            start_time = datetime.utcnow()
            result = run_forecasts_job()
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Save job metadata
            job_metadata = {
                "job_id": "forecasts_job",
                "start_time": start_time.isoformat() + "Z",
                "end_time": datetime.utcnow().isoformat() + "Z",
                "duration_seconds": duration,
                "status": "success",
                "result_summary": result
            }
            
            save_json("job_forecasts", job_metadata, source=["scheduler", "forecasts"])
            logger.info(f"Forecasts job completed successfully in {duration:.2f}s")
        except Exception as e:
            logger.error(f"Forecasts job failed: {str(e)}", exc_info=True)
            job_metadata = {
                "job_id": "forecasts_job",
                "start_time": datetime.utcnow().isoformat() + "Z",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            save_json("job_forecasts", job_metadata, source=["scheduler", "forecasts", "error"])
    
    def _run_weekly_brief_job(self):
        """
        Run weekly brief job with error handling and logging
        """
        try:
            logger.info("Starting weekly brief job...")
            start_time = datetime.utcnow()
            result = run_weekly_brief_job()
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Save job metadata
            job_metadata = {
                "job_id": "weekly_brief_job",
                "start_time": start_time.isoformat() + "Z",
                "end_time": datetime.utcnow().isoformat() + "Z",
                "duration_seconds": duration,
                "status": "success",
                "result_summary": result
            }
            
            save_json("job_weekly_brief", job_metadata, source=["scheduler", "weekly_brief"])
            logger.info(f"Weekly brief job completed successfully in {duration:.2f}s")
        except Exception as e:
            logger.error(f"Weekly brief job failed: {str(e)}", exc_info=True)
            job_metadata = {
                "job_id": "weekly_brief_job",
                "start_time": datetime.utcnow().isoformat() + "Z",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            save_json("job_weekly_brief", job_metadata, source=["scheduler", "weekly_brief", "error"])
    
    def _run_backtests_job(self):
        """
        Run backtests job with error handling and logging
        """
        try:
            logger.info("Starting backtests job...")
            start_time = datetime.utcnow()
            result = run_backtests_job()
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Save job metadata
            job_metadata = {
                "job_id": "backtests_job",
                "start_time": start_time.isoformat() + "Z",
                "end_time": datetime.utcnow().isoformat() + "Z",
                "duration_seconds": duration,
                "status": "success",
                "result_summary": result
            }
            
            save_json("job_backtests", job_metadata, source=["scheduler", "backtests"])
            logger.info(f"Backtests job completed successfully in {duration:.2f}s")
        except Exception as e:
            logger.error(f"Backtests job failed: {str(e)}", exc_info=True)
            job_metadata = {
                "job_id": "backtests_job",
                "start_time": datetime.utcnow().isoformat() + "Z",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            save_json("job_backtests", job_metadata, source=["scheduler", "backtests", "error"])
    
    def _run_g4f_watcher_job(self):
        """
        Refresh the G4F working models list to keep judge fast and reliable.
        """
        try:
            limit = int(os.getenv("G4F_WATCHER_LIMIT", "10") or "10")
            refresh_verified = os.getenv("G4F_WATCHER_REFRESH_VERIFIED", "1").strip().lower() not in {"0", "false", "no"}
            logger.info("Starting G4F watcher job (limit=%s, refresh_verified=%s)...", limit, refresh_verified)
            start_time = datetime.utcnow()
            path = refresh_g4f_models(limit=limit, refresh_verified=refresh_verified)
            duration = (datetime.utcnow() - start_time).total_seconds()
            job_metadata = {
                "job_id": "g4f_watcher_job",
                "start_time": start_time.isoformat() + "Z",
                "end_time": datetime.utcnow().isoformat() + "Z",
                "duration_seconds": duration,
                "status": "success",
                "result_summary": {
                    "saved_to": str(path),
                    "limit": limit,
                    "refresh_verified": refresh_verified,
                }
            }
            save_json("job_g4f_watcher", job_metadata, source=["scheduler", "g4f_watcher"])
            logger.info("G4F watcher job completed successfully in %.2fs", duration)
        except Exception as e:
            logger.error("G4F watcher job failed: %s", e, exc_info=True)
            job_metadata = {
                "job_id": "g4f_watcher_job",
                "start_time": datetime.utcnow().isoformat() + "Z",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            save_json("job_g4f_watcher", job_metadata, source=["scheduler", "g4f_watcher", "error"])
    
    def start(self):
        """
        Start the scheduler
        """
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
            
            # Register shutdown function to properly close the scheduler on exit
            atexit.register(lambda: self.shutdown())
    
    def shutdown(self):
        """
        Shutdown the scheduler
        """
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down")


# Global scheduler instance
scheduler = JobScheduler()


def start_scheduler():
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown()
