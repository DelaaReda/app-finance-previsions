"""
Dashboard KPIs API Routes - FIXED VERSION
"""
from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from storage.io import load_json

# Create router instance
dashboard_router = APIRouter(tags=["dashboard"])

@dashboard_router.get("/kpis")
async def dashboard_kpis():
    """Get dashboard KPIs with real data"""
    try:
        # Load data
        forecasts_data = load_json("forecasts") or {}
        news_data = load_json("news_feed") or {}
        
        # Extract forecast rows
        forecast_rows = forecasts_data.get("rows", [])
        
        # Extract news articles  
        articles = news_data.get("articles", [])
        
        # Calculate forecast KPIs
        total_forecasts = len(forecast_rows)
        high_conf_count = sum(1 for r in forecast_rows if r.get("confidence", 0) >= 0.6)
        bullish = sum(1 for r in forecast_rows if r.get("direction") == "up")
        bearish = sum(1 for r in forecast_rows if r.get("direction") == "down")
        
        # Calculate news KPIs
        news_count = len(articles)
        positive_news = sum(1 for a in articles if a.get("sentiment_score", 0) >= 0.1)
        
        # Build response
        return {
            "ok": True,
            "data": {
                "kpi_forecasts": {
                    "active_forecasts": total_forecasts,
                    "high_confidence_forecasts": high_conf_count,
                    "bullish_signals": bullish,
                    "bearish_signals": bearish,
                },
                "kpi_news": {
                    "total_news": news_count,
                    "positive_news": positive_news,
                },
                "health": {
                    "forecasts_available": total_forecasts > 0,
                    "news_available": news_count > 0,
                    "overall_health": "healthy" if (total_forecasts > 0 and news_count > 0) else "degraded"
                },
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        }
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "kpi_forecasts": {"active_forecasts": 0, "high_confidence_forecasts": 0, "bullish_signals": 0, "bearish_signals": 0},
                "kpi_news": {"total_news": 0, "positive_news": 0},
                "health": {"overall_health": "error"},
                "error": str(e)
            }
        }

# Export router with expected name
router = dashboard_router
dashboard_router = dashboard_router  # Explicit export for main.py
