"""
APScheduler background jobs. Call start_scheduler() from FastAPI startup event (guarded by env).
"""
from __future__ import annotations
from apscheduler.schedulers.background import BackgroundScheduler
from backend.jobs.job_forecasts import run_forecast_job
from backend.jobs.job_news import run_news_job
from backend.jobs.job_weekly_brief import run_weekly_brief
from backend.jobs.job_backtests import run_backtests_job

_scheduler: BackgroundScheduler | None = None

def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler:
        return _scheduler
    s = BackgroundScheduler(timezone="UTC")
    s.add_job(run_news_job, "interval", minutes=15, id="news_ingest")
    s.add_job(run_forecast_job, "cron", hour=4, minute=0, id="forecasts_daily")
    s.add_job(run_weekly_brief, "cron", day_of_week="sun", hour=18, id="weekly_brief")
    s.add_job(run_backtests_job, "cron", hour=3, minute=30, id="backtests")
    s.start()
    _scheduler = s
    return s
