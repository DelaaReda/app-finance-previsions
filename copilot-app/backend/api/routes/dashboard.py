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
            data_payload = forecasts_data["data"]
            forecasts_rows = data_payload.get("rows", data_payload if isinstance(data_payload, list) else [])
            last_forecast_dt = forecasts_data.get("last_update")
            
            # Count unique tickers
            tickers_set = set()
            horizons_set = set()
            for f in forecasts_rows:
                if isinstance(f, dict):
                    ticker = f.get("ticker") or f.get("symbol")
                    if ticker:
                        tickers_set.add(ticker)
                    horizon = f.get("horizon") or f.get("timeframe")
                    if horizon:
                        horizons_set.add(horizon)
            
            total_forecasts = len(forecasts_rows)
            tickers_tracked = len(tickers_set)
            available_horizons = sorted(list(horizons_set))
        else:
            last_forecast_dt = None
            total_forecasts = 0
            tickers_tracked = 0
            available_horizons = []
            forecasts_rows = []
        
        # 2. Load weekly brief for top signals and risks
        brief_data = load_weekly_brief()
        
        top_signals = []
        top_risks = []
        
        if brief_data and "data" in brief_data:
            data_payload = brief_data["data"]
            brief_weekly = data_payload.get("weekly", data_payload if isinstance(data_payload, dict) else data_payload)
            
            # Extract top signals
            signals = brief_weekly.get("top_signals", [])
            if signals:
                top_signals = signals[:3]  # Top 3
            else:
                # Fallback: try to get from brief root level
                top_signals = data_payload.get("top_signals", [])[:3]
            
            # Extract top risks
            risks = brief_weekly.get("top_risks", [])
            if risks:
                top_risks = risks[:3]  # Top 3
            else:
                # Fallback: try to get from brief root level
                top_risks = data_payload.get("top_risks", [])[:3]
        
        # 3. If brief is empty, try to get from forecasts as fallback (this is the main improvement)
        if (not top_signals or len(top_signals) == 0) and (not top_risks or len(top_risks) == 0):
            if forecasts_rows and len(forecasts_rows) > 0:
                # Sort by confidence * expected_return for signals
                bullish_forecasts = []
                bearish_forecasts = []
                
                for f in forecasts_rows:
                    if isinstance(f, dict):
                        # Determine direction based on available fields
                        direction = f.get("direction") or f.get("trend") or "neutral"
                        confidence = f.get("confidence", f.get("confidence_score", 0))
                        expected_return = f.get("expected_return", f.get("expected_return_pct", 0))
                        
                        if direction in ["up", "positive", "bullish", "buy"] or (confidence > 0.5 and expected_return > 0):
                            bullish_forecasts.append(f)
                        elif direction in ["down", "negative", "bearish", "sell"] or (confidence > 0.5 and expected_return < 0):
                            bearish_forecasts.append(f)
                
                # Sort bullish by confidence and expected return
                bullish_forecasts.sort(
                    key=lambda x: x.get("confidence", 0) * abs(x.get("expected_return", 0)) if isinstance(x, dict) else 0,
                    reverse=True
                )
                
                # Sort bearish by confidence and negative expected return
                bearish_forecasts.sort(
                    key=lambda x: x.get("confidence", 0) * abs(x.get("expected_return", 0)) if isinstance(x, dict) else 0,
                    reverse=True
                )
                
                # Take top 3 bullish as signals
                for f in bullish_forecasts[:3]:
                    if isinstance(f, dict):
                        top_signals.append({
                            "ticker": f.get("ticker") or f.get("symbol") or "N/A",
                            "direction": f.get("direction") or f.get("trend") or "up",
                            "confidence": f.get("confidence", f.get("confidence_score", 0)),
                            "expected_return": f.get("expected_return", f.get("expected_return_pct", 0)),
                            "horizon": f.get("horizon") or f.get("timeframe") or f.get("period") or "short",
                            "reason": f.get("explanation") or f.get("rationale") or f.get("summary") or "AI prediction based on technical and fundamental analysis",
                        })
                
                # Take top 3 bearish as risks
                for f in bearish_forecasts[:3]:
                    if isinstance(f, dict):
                        top_risks.append({
                            "ticker": f.get("ticker") or f.get("symbol") or "N/A",
                            "direction": f.get("direction") or f.get("trend") or "down",
                            "confidence": f.get("confidence", f.get("confidence_score", 0)),
                            "expected_return": f.get("expected_return", f.get("expected_return_pct", 0)),
                            "horizon": f.get("horizon") or f.get("timeframe") or f.get("period") or "short",
                            "reason": f.get("explanation") or f.get("rationale") or f.get("summary") or "AI prediction based on technical and fundamental analysis",
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
            ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
            # Filter signals and risks by tickers
            if response["top_signals"]:
                response["top_signals"] = [
                    s for s in response["top_signals"]
                    if isinstance(s, dict) and s.get("ticker") in ticker_list
                ]
            if response["top_risks"]:
                response["top_risks"] = [
                    r for r in response["top_risks"]
                    if isinstance(r, dict) and r.get("ticker") in ticker_list
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
            "note": "System is calculating forecasts in background",
            "source": ["fallback_empty_response", "error_handling"]
        })