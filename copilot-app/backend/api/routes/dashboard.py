"""
Dashboard Routes
Routes pour le tableau de bord avec KPIs, top signaux et risques
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Tâche 1.1 - Corriger et Optimiser l'API Dashboard
"""
from fastapi import APIRouter, Query, HTTPException, Response
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import json

from core.response import ok, err
from storage.base import load_forecasts, load_weekly_brief, load_json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard/kpis")
def get_dashboard_kpis(
    sectors: Optional[str] = Query(None, description="Filter by sectors (comma-separated)"),
    horizons: Optional[str] = Query(None, description="Filter by horizons (comma-separated)"),
    themes: Optional[str] = Query(None, description="Filter by themes (comma-separated)"),
    tickers: Optional[str] = Query(None, description="Filter by tickers (comma-separated)"),
):
    """
    Get dashboard KPIs with top signals and risks.
    
    Returns:
        - KPIs (last_forecast_dt, total_forecasts, tickers_tracked, available_horizons)
        - top_signals: Top 3 opportunities
        - top_risks: Top 3 risks
    """
    try:
        # 0. Try to load from cache first (Tâche 1.2 - Cache)
        try:
            from storage.io import load_json as load_json_io
            cached_kpis = load_json_io("dashboard/kpis")
            if cached_kpis:
                # Extract data if wrapped
                cached_data = cached_kpis.get("data") or cached_kpis.get("payload") or cached_kpis
                # Check freshness (15 min max age)
                cached_at = cached_data.get("generated_at") or cached_kpis.get("freshness")
                if cached_at:
                    from datetime import datetime, timedelta
                    try:
                        cached_time = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
                        age = (datetime.utcnow() - cached_time.replace(tzinfo=None)).total_seconds()
                        if age < 900:  # 15 minutes
                            logger.info(f"✅ Serving cached dashboard KPIs (age: {age:.0f}s)")
                            # Return with cache headers
                            response_data = ok(cached_data)
                            # Add cache headers (Tâche 1.2 - HTTP Cache)
                            return Response(
                                content=json.dumps(response_data),
                                media_type="application/json",
                                headers={
                                    "Cache-Control": "public, max-age=300",  # 5 min browser cache
                                    "ETag": f'"{hash(str(cached_data))}"',  # Simple ETag
                                }
                            )
                    except Exception:
                        pass  # Continue to compute if cache invalid
        except Exception as e:
            logger.debug(f"Cache check failed: {e}")
        
        # 1. Load forecasts data for KPIs
        forecasts_data = load_forecasts()
        
        # Extract KPIs from forecasts
        if forecasts_data and "data" in forecasts_data:
            forecasts_rows = forecasts_data["data"].get("rows", [])
            last_forecast_dt = forecasts_data.get("last_update")
            
            # Count unique tickers
            tickers_set = set()
            horizons_set = set()
            for f in forecasts_rows:
                if f.get("ticker"):
                    tickers_set.add(f["ticker"])
                if f.get("horizon"):
                    horizons_set.add(f["horizon"])
            
            total_forecasts = len(forecasts_rows)
            tickers_tracked = len(tickers_set)
            available_horizons = sorted(list(horizons_set))
        else:
            last_forecast_dt = None
            total_forecasts = 0
            tickers_tracked = 0
            available_horizons = []
        
        # 2. Load weekly brief for top signals and risks
        brief_data = load_weekly_brief()
        
        top_signals = []
        top_risks = []
        
        if brief_data and "data" in brief_data:
            brief_weekly = brief_data["data"].get("weekly", {})
            
            # Extract top signals
            signals = brief_weekly.get("top_signals", [])
            if signals:
                top_signals = signals[:3]  # Top 3
            else:
                # Fallback: try to get from brief root level
                top_signals = brief_data["data"].get("top_signals", [])[:3]
            
            # Extract top risks
            risks = brief_weekly.get("top_risks", [])
            if risks:
                top_risks = risks[:3]  # Top 3
            else:
                # Fallback: try to get from brief root level
                top_risks = brief_data["data"].get("top_risks", [])[:3]
        
        # 3. If brief is empty, try to get from forecasts as fallback
        if not top_signals and not top_risks and forecasts_data:
            forecasts_rows = forecasts_data["data"].get("rows", [])
            
            # Sort by confidence * expected_return for signals
            bullish_forecasts = [
                f for f in forecasts_rows 
                if f.get("direction") == "up" and f.get("confidence", 0) > 0.5
            ]
            bullish_forecasts.sort(
                key=lambda x: x.get("confidence", 0) * abs(x.get("expected_return", 0)),
                reverse=True
            )
            
            for f in bullish_forecasts[:3]:
                top_signals.append({
                    "ticker": f.get("ticker"),
                    "direction": "up",
                    "confidence": f.get("confidence", 0),
                    "expected_return": f.get("expected_return", 0),
                    "horizon": f.get("horizon", "1m"),
                    "reason": f.get("explanation", "Bullish forecast"),
                })
            
            # Sort by risk (low confidence or bearish)
            bearish_forecasts = [
                f for f in forecasts_rows 
                if f.get("direction") == "down" or f.get("confidence", 0) < 0.3
            ]
            bearish_forecasts.sort(
                key=lambda x: (1 - x.get("confidence", 0)) * abs(x.get("expected_return", 0)),
                reverse=True
            )
            
            for f in bearish_forecasts[:3]:
                top_risks.append({
                    "ticker": f.get("ticker"),
                    "direction": "down",
                    "confidence": f.get("confidence", 0),
                    "expected_return": f.get("expected_return", 0),
                    "horizon": f.get("horizon", "1m"),
                    "reason": f.get("explanation", "Bearish forecast"),
                })
        
        # 4. Build response
        response = {
            "last_forecast_dt": last_forecast_dt,
            "total_forecasts": total_forecasts,
            "tickers_tracked": tickers_tracked,
            "available_horizons": available_horizons,
            "top_signals": top_signals,
            "top_risks": top_risks,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        # 5. Apply filters if provided (future enhancement)
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",")]
            # Filter signals and risks by tickers
            response["top_signals"] = [
                s for s in response["top_signals"]
                if s.get("ticker") in ticker_list
            ]
            response["top_risks"] = [
                r for r in response["top_risks"]
                if r.get("ticker") in ticker_list
            ]
        
        # Return with cache headers
        response_data = ok(response)
        return Response(
            content=json.dumps(response_data),
            media_type="application/json",
            headers={
                "Cache-Control": "public, max-age=300",  # 5 min browser cache
            }
        )
        
    except Exception as e:
        logger.error(f"Error in get_dashboard_kpis: {str(e)}", exc_info=True)
        # Return empty but valid structure
        return ok({
            "last_forecast_dt": None,
            "total_forecasts": 0,
            "tickers_tracked": 0,
            "available_horizons": [],
            "top_signals": [],
            "top_risks": [],
            "generated_at": datetime.utcnow().isoformat(),
            "error": str(e),
        })

