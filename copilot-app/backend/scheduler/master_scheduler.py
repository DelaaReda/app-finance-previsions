"""
Master Scheduler - Centralized Agent Orchestration System
Part of Finance Copilot Architecture Enhancement Initiative

Implements centralized scheduling for all agents following the architecture recommendations from analysis:
- Centralizes the scheduling of agents (ingestion, forecasting, aggregation, quality monitoring)
- Provides unified logging and monitoring
- Enables coordinated execution of dependent tasks
- Implements fallback mechanisms for resilient operations

File: /scheduler/master_scheduler.py
Task: FC-SCHEDULER-001 - Implement centralized agent orchestration
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import json
from pathlib import Path
import os

from jobs.forecasts import run_forecasts_job
from jobs.leads import run_leads_job  
from jobs.news_sentiment import run_news_sentiment_analysis
from jobs.market_brief import run_market_brief_job
from jobs.update_monitor import run_update_monitor_job
from storage.io import save_json, load_json

class MasterScheduler:
    """
    Centralized scheduler system for coordinating all agents in the Finance Copilot ecosystem.
    Implements the architecture recommendation for unified agent orchestration.
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger(__name__)
        self.job_results = {}  # Store results for monitoring
        self.failed_jobs = {}  # Track failed executions
        
        # Setup logging
        self.setup_logging()
        
        # Register event listeners
        self.scheduler.add_listener(self.job_execution_listener)
        
    def setup_logging(self):
        """Setup logging for scheduler events"""
        # Configure logging to save to a file
        log_dir = Path("logs") / "scheduler"
        log_dir.mkdir(exist_ok=True, parents=True)
        log_file = log_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def job_execution_listener(self, event):
        """Listen for job execution events and log results"""
        if event.exception:
            self.logger.error(f"Job {event.job_id} failed: {event.exception}")
            self.failed_jobs[event.job_id] = {
                "timestamp": datetime.now().isoformat(),
                "error": str(event.exception),
                "job_id": event.job_id
            }
        else:
            self.logger.info(f"Job {event.job_id} completed successfully")
    
    def register_forecast_job(self):
        """Register the forecast generation job with the scheduler"""
        self.scheduler.add_job(
            func=self._run_forecasts_wrapper,
            trigger=CronTrigger(hour=2, minute=0),  # Daily at 2 AM
            id='forecast_job',
            name='Generate Daily Forecasts',
            replace_existing=True
        )
        self.logger.info("Registered forecast job: Daily at 2:00 AM UTC")
    
    def register_leads_job(self):
        """Register the leads generation job with the scheduler"""
        self.scheduler.add_job(
            func=self._run_leads_wrapper,
            trigger=CronTrigger(hour=4, minute=30),  # Daily at 4:30 AM
            id='leads_job',
            name='Generate Investment Leads',
            replace_existing=True
        )
        self.logger.info("Registered leads job: Daily at 4:30 AM UTC")
    
    def register_news_sentiment_job(self):
        """Register the news sentiment analysis job with the scheduler"""
        self.scheduler.add_job(
            func=self._run_news_sentiment_wrapper,
            trigger="interval",
            minutes=30,  # Every 30 minutes
            id='news_sentiment_job',
            name='Analyze News Sentiment',
            replace_existing=True
        )
        self.logger.info("Registered news sentiment job: Every 30 minutes")
    
    def register_market_brief_job(self):
        """Register the market brief generation job with the scheduler"""
        self.scheduler.add_job(
            func=self._run_market_brief_wrapper,
            trigger=CronTrigger(hour=6, minute=0),  # Daily at 6 AM (before markets open)
            id='market_brief_job',
            name='Generate Market Brief',
            replace_existing=True
        )
        self.logger.info("Registered market brief job: Daily at 6:00 AM UTC")
    
    def register_update_monitor_job(self):
        """Register the data update monitoring job with the scheduler"""
        self.scheduler.add_job(
            func=self._run_update_monitor_wrapper,
            trigger="interval",
            hours=1,  # Hourly check
            id='update_monitor_job',
            name='Monitor Data Freshness',
            replace_existing=True
        )
        self.logger.info("Registered update monitor job: Hourly")
    
    def register_data_quality_job(self):
        """Register the data quality monitoring job with the scheduler"""
        self.scheduler.add_job(
            func=self._run_data_quality_wrapper,
            trigger=CronTrigger(hour=1, minute=0),  # Daily at 1 AM
            id='data_quality_job',
            name='Run Data Quality Checks',
            replace_existing=True
        )
        self.logger.info("Registered data quality job: Daily at 1:00 AM UTC")
    
    def register_weekly_summary_job(self):
        """Register the weekly summary generation job"""
        self.scheduler.add_job(
            func=self._run_weekly_summary_wrapper,
            trigger=CronTrigger(day_of_week='mon', hour=5, minute=0),  # Monday at 5 AM
            id='weekly_summary_job',
            name='Generate Weekly Summary',
            replace_existing=True
        )
        self.logger.info("Registered weekly summary job: Mondays at 5:00 AM UTC")
    
    # Wrappers for job execution with error handling and logging
    async def _run_forecasts_wrapper(self):
        """Wrapper for forecast job with error handling"""
        try:
            self.logger.info("Starting forecast job execution")
            result = await asyncio.get_event_loop().run_in_executor(None, run_forecasts_job)
            self.job_results['forecast_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "result": result
            }
            self.logger.info(f"Forecast job completed: {result}")
            
            # Save results for monitoring
            await self.save_job_results('forecast', result)
            
        except Exception as e:
            self.logger.error(f"Forecast job failed: {e}", exc_info=True)
            self.job_results['forecast_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def _run_leads_wrapper(self):
        """Wrapper for leads job with error handling"""
        try:
            self.logger.info("Starting leads job execution")
            result = await asyncio.get_event_loop().run_in_executor(None, run_leads_job)
            self.job_results['leads_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "success", 
                "result": result
            }
            self.logger.info(f"Leads job completed: {len(result.get('leads', [])) if isinstance(result, dict) else 'unknown'} leads generated")
            
            # Save results for monitoring
            await self.save_job_results('leads', result)
            
        except Exception as e:
            self.logger.error(f"Leads job failed: {e}", exc_info=True)
            self.job_results['leads_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def _run_news_sentiment_wrapper(self):
        """Wrapper for news sentiment job with error handling"""
        try:
            self.logger.info("Starting news sentiment job execution")
            result = await asyncio.get_event_loop().run_in_executor(None, run_news_sentiment_analysis)
            self.job_results['news_sentiment_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "result": result
            }
            self.logger.info(f"News sentiment job completed")
            
            # Save results for monitoring
            await self.save_job_results('news_sentiment', result)
            
        except Exception as e:
            self.logger.error(f"News sentiment job failed: {e}", exc_info=True)
            self.job_results['news_sentiment_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def _run_market_brief_wrapper(self):
        """Wrapper for market brief job with error handling"""
        try:
            self.logger.info("Starting market brief job execution")
            result = await asyncio.get_event_loop().run_in_executor(None, run_market_brief_job)
            self.job_results['market_brief_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "result": result
            }
            self.logger.info(f"Market brief job completed")
            
            # Save results for monitoring
            await self.save_job_results('market_brief', result)
            
        except Exception as e:
            self.logger.error(f"Market brief job failed: {e}", exc_info=True)
            self.job_results['market_brief_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def _run_update_monitor_wrapper(self):
        """Wrapper for update monitor job with error handling"""
        try:
            self.logger.info("Starting update monitor job execution")
            result = await asyncio.get_event_loop().run_in_executor(None, run_update_monitor_job)
            self.job_results['update_monitor_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "result": result
            }
            self.logger.info(f"Update monitor job completed")
            
            # Save results for monitoring
            await self.save_job_results('update_monitor', result)
            
        except Exception as e:
            self.logger.error(f"Update monitor job failed: {e}", exc_info=True)
            self.job_results['update_monitor_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def _run_data_quality_wrapper(self):
        """Wrapper for data quality job with error handling"""
        try:
            self.logger.info("Starting data quality job execution")
            # Placeholder - implement actual data quality job
            result = {"status": "completed", "checked_at": datetime.now().isoformat()}
            self.job_results['data_quality_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "result": result
            }
            self.logger.info("Data quality job completed")
            
            # Save results for monitoring
            await self.save_job_results('data_quality', result)
            
        except Exception as e:
            self.logger.error(f"Data quality job failed: {e}", exc_info=True)
            self.job_results['data_quality_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def _run_weekly_summary_wrapper(self):
        """Wrapper for weekly summary job with error handling"""
        try:
            self.logger.info("Starting weekly summary job execution")
            # Placeholder - implement actual weekly summary job
            result = {"status": "completed", "summary_period": "weekly", "created_at": datetime.now().isoformat()}
            self.job_results['weekly_summary_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "result": result
            }
            self.logger.info("Weekly summary job completed")
            
            # Save results for monitoring
            await self.save_job_results('weekly_summary', result)
            
        except Exception as e:
            self.logger.error(f"Weekly summary job failed: {e}", exc_info=True)
            self.job_results['weekly_summary_last_run'] = {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def save_job_results(self, job_name: str, result: Any):
        """Save job results to persistent storage"""
        try:
            data_dir = Path("data") / "scheduler"
            data_dir.mkdir(exist_ok=True, parents=True)
            
            filepath = data_dir / f"{job_name}_results.json"
            save_json(result, str(filepath), source=["scheduler", f"{job_name}_job"])
            
        except Exception as e:
            self.logger.error(f"Failed to save {job_name} results: {e}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current status of the scheduler"""
        jobs = self.scheduler.get_jobs()
        return {
            "running": self.scheduler.running,
            "job_count": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in jobs
            ],
            "last_results": self.job_results,
            "failed_jobs": self.failed_jobs
        }
    
    def start(self):
        """Start the centralized scheduler"""
        self.logger.info("Starting Master Scheduler...")
        
        # Register all jobs
        self.register_forecast_job()
        self.register_leads_job()
        self.register_news_sentiment_job()
        self.register_market_brief_job()
        self.register_update_monitor_job()
        self.register_data_quality_job()
        self.register_weekly_summary_job()
        
        # Start the scheduler
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("Master Scheduler started successfully with all agents registered")
    
    def stop(self):
        """Stop the centralized scheduler"""
        self.logger.info("Stopping Master Scheduler...")
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.logger.info("Master Scheduler stopped successfully")

# Global instance for easy access
master_scheduler = MasterScheduler()

def get_scheduler():
    """Get the global scheduler instance"""
    return master_scheduler

if __name__ == "__main__":
    # Test the scheduler setup
    import time
    scheduler = MasterScheduler()
    
    # Add a test job that runs immediately for testing
    scheduler.scheduler.add_job(
        func=lambda: print(f"Test job executed at {datetime.now()}"),
        trigger="date",
        run_date=datetime.now() + timedelta(seconds=2),
        id='test_job'
    )
    
    print("Starting scheduler for testing...")
    scheduler.start()
    
    # Let it run briefly then stop
    try:
        time.sleep(5)
    finally:
        scheduler.stop()
        print("Scheduler test completed.")