"""
Scheduler for Finance Copilot - FC-P1-011
Handles scheduled jobs like news ingestion, forecast updates, etc.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from jobs.news_ingest import run_news_ingest
import atexit

# Create the scheduler
scheduler = BackgroundScheduler()

# Add jobs
# News ingestion job - run every 15 minutes
scheduler.add_job(run_news_ingest, 'interval', minutes=15, id='news_ingest_job')

def start_scheduler():
    """Start the background scheduler"""
    if not scheduler.running:
        scheduler.start()
        print("Scheduler started. Jobs: news_ingest (every 15 min)")
        
        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped")

# For standalone execution
if __name__ == "__main__":
    start_scheduler()
    print("Scheduler running... Press Ctrl+C to exit")
    try:
        import time
        while True:
            time.sleep(60)  # Keep the main thread alive
    except KeyboardInterrupt:
        print("Shutting down...")
        stop_scheduler()