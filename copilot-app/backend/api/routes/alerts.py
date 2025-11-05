"""
Alerts API Route - Provides market alerts based on technical signals, news, and forecasts
"""
from fastapi import APIRouter
from typing import Dict, Any

from backend.core.response import ok
from backend.services.cache_layer import load_or_compute
from backend.jobs.alerts import get_latest_alerts

router = APIRouter()


@router.get("/alerts")
def alerts():
    """
    Get market alerts with technical signals, news sentiment, and forecast correlation.
    
    Returns alerts ordered by confidence (highest first).
    
    Example response structure:
    {
        "ok": true,
        "data": {
            "alerts": [
                {
                    "id": "oversold-bearish-SPY-20251104123456",
                    "type": "oversold-bearish",
                    "ticker": "SPY",
                    "description": "SPY oversold (RSI: 28.5) with negative sentiment and bearish forecast",
                    "severity": "medium",
                    "confidence": 0.85,
                    "timestamp": "2025-11-04T12:34:56.789Z",
                    "signals": {
                        "rsi": 28.5,
                        "sentiment_negative": true,
                        "forecast_direction": "down"
                    }
                }
            ],
            "count": 1,
            "generated_at": "2025-11-04T12:34:56.789Z",
            "source": ["technical_signals", "news_sentiment", "forecast_correlation"],
            "pipeline": {
                "algorithm": "multi_signal_confluence_v1",
                "processed_at": "2025-11-04T12:34:56.789Z"
            }
        }
    }
    """
    # Use the cache layer to get alerts data
    # If cached data exists and is fresh, return it
    # Otherwise, compute fresh alerts and cache them
    alerts_data = get_latest_alerts()
    
    # Add freshness information to response
    if 'generated_at' in alerts_data:
        # Calculate if data is stale (older than 1 hour)
        import datetime
        try:
            gen_time = datetime.datetime.fromisoformat(alerts_data['generated_at'].replace('Z', '+00:00'))
            current_time = datetime.datetime.now(datetime.timezone.utc)
            time_diff = (current_time - gen_time).total_seconds()
            
            alerts_data["freshness"] = "stale" if time_diff > 3600 else "fresh"
        except:
            alerts_data["freshness"] = "unknown"
    else:
        alerts_data["freshness"] = "fresh"
    
    return ok(alerts_data)


# Run the alert job to generate initial alerts
# This ensures that when the endpoint is first called, there's already data
if __name__ != "__main__":
    # Import and run the job to ensure we have initial data
    from backend.jobs.alerts import run_alerts_job
    import sys
    import os
    # Only run on import if we're not in a test environment
    if not os.environ.get('TEST_ENV'):
        try:
            run_alerts_job()
        except:
            # If job fails to run, that's okay - the endpoint will handle it gracefully
            pass