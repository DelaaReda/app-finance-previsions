"""
Scheduler for news ingestion jobs - refreshes news feed every 15 minutes as required
Task: FC-P1-011 (News Ingest v1) + periodic refresh requirement
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import time
import logging
from datetime import datetime
import threading
from backend.src.ingestion.financial_news_ingest import run_news_ingest_job

logger = logging.getLogger(__name__)

def run_news_scheduler():
    """
    Run news ingestion jobs on a schedule (every 15 minutes)
    According to requirements: refresh every 15 minutes for timely news
    """
    print("Setting up news ingestion scheduler...")
    print("- News ingestion job scheduled every 15 minutes")
    print("- Aligns with FC-P1-011 requirements for timely news feed")
    print("- Maintains never-empty guarantee through persistent caching")
    print()
    
    # Run once at startup to populate initial data
    print("Running initial news ingestion job...")
    run_news_ingest_job()
    print("Initial job completed.")
    
    # Run the jobs every 15 minutes
    while True:
        time.sleep(15 * 60)  # Sleep for 15 minutes
        try:
            print(f"[{datetime.now().isoformat()}] Running scheduled news ingestion job...")
            run_news_ingest_job()
            print(f"[{datetime.now().isoformat()}] Scheduled news ingestion job completed.")
        except Exception as e:
            logger.error(f"Error in scheduled news job: {e}")


def start_news_scheduler():
    """
    Start the news scheduler in a background thread
    """
    scheduler_thread = threading.Thread(target=run_news_scheduler, daemon=True)
    scheduler_thread.start()
    print("News ingestion scheduler started in background thread.")
    return scheduler_thread


if __name__ == "__main__":
    print("Starting News Ingestion Scheduler...")
    print("Task: FC-P1-011 - News Ingest v1 (RSS multi-sources) + periodic refresh")
    print(f"Started: {datetime.now().isoformat()}")
    print("-" * 60)
    
    # Start the scheduler
    try:
        run_news_scheduler()
    except KeyboardInterrupt:
        print("\nScheduler stopped by user.")
        print("News ingestion scheduler shutdown completed.")
    except Exception as e:
        print(f"Error in scheduler: {e}")
        logger.error(f"News ingestion scheduler error: {e}")