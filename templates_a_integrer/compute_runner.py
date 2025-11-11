"""
Compute runner helpers to unify "serve cached → refresh elsewhere" pattern.
"""
from __future__ import annotations
from typing import Dict, Any
from backend.services.cache_layer import load_or_compute
from backend.jobs.job_forecasts import run_forecast_job
from backend.jobs.job_news import run_news_job
from backend.jobs.job_weekly_brief import run_weekly_brief
from backend.jobs.job_backtests import run_backtests_job

def get_forecasts_data() -> Dict[str, Any]:
    return load_or_compute("forecasts", lambda: run_forecast_job(), source="forecasts")

def get_news_feed() -> Dict[str, Any]:
    return load_or_compute("news_feed", lambda: run_news_job(), source="news")

def get_weekly_brief() -> Dict[str, Any]:
    return load_or_compute("weekly_brief", lambda: run_weekly_brief(), source="weekly")

def get_backtests() -> Dict[str, Any]:
    return load_or_compute("backtests", lambda: run_backtests_job(), source="backtests")
