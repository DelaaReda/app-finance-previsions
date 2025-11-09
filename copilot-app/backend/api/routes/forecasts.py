"""
API Routes for Forecasts - Dashboard Integration
Provides filtered forecasting data for the dashboard with never-empty guarantee
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from core.response import ok, err
from storage.io import load_json

router = APIRouter()

@router.get("/forecasts")
def get_filtered_forecasts(
    horizon: Optional[str] = Query("all", description="Horizon filter: 1d, 5d, 1mo, 1w, 1y, all"),
    asset_type: Optional[str] = Query("all", description="Asset type: equity, commodity, crypto, forex, all"),
    sort_by: Optional[str] = Query("confidence", description="Sort by: confidence, expected_return, ticker, date"),
    limit: Optional[int] = Query(50, description="Limit number of results returned"),
    tickers: Optional[List[str]] = Query(None, description="Specific tickers to include"),
    themes: Optional[List[str]] = Query(None, description="Specific themes to filter (growth, value, momentum, etc.)"),
    min_confidence: Optional[float] = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold (0.0-1.0)")
) -> Dict[str, Any]:
    """
    Dashboard forecasts endpoint with filtering capabilities.
    Returns forecast data with proper structure for dashboard UI components.
    """
    try:
        # Load forecasts from persistent storage (following never-empty pattern)
        forecasts_data = load_json("forecasts")
        
        if not forecasts_data:
            # Return empty structure with metadata but never fail
            return ok({
                "rows": [],
                "count": 0,
                "filtered_params": {
                    "horizon": horizon,
                    "asset_type": asset_type,
                    "sort_by": sort_by,
                    "limit": limit,
                    "tickers": tickers,
                    "themes": themes,
                    "min_confidence": min_confidence
                },
                "message": "No forecast data available - system calculating in background",
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback_empty"]
            })
        
        # Extract forecast rows
        data_payload = forecasts_data.get("data", forecasts_data.get("payload", forecasts_data))
        all_rows = data_payload.get("rows", data_payload if isinstance(data_payload, list) else [])
        
        # Apply filtering
        filtered_rows = all_rows
        
        if asset_type != "all":
            filtered_rows = [row for row in filtered_rows if row.get("asset_type", row.get("type", "equity")).lower() == asset_type.lower()]
        
        if horizon != "all":
            filtered_rows = [row for row in filtered_rows if row.get("horizon", "all") == horizon]
        
        if tickers:
            filtered_rows = [row for row in filtered_rows if row.get("ticker") in tickers or row.get("symbol") in tickers]
        
        if themes:
            filtered_rows = [row for row in filtered_rows if row.get("theme") in themes or row.get("category") in themes]
        
        # Filter by minimum confidence (Sprint 5 - Tâche 5.1)
        if min_confidence and min_confidence > 0:
            filtered_rows = [
                row for row in filtered_rows
                if row.get("confidence", 0) >= min_confidence
            ]
        
        # Sort results
        if sort_by == "confidence":
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("confidence", 0), reverse=True)
        elif sort_by == "expected_return":
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("expected_return", 0), reverse=True)
        elif sort_by == "ticker":
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("ticker", x.get("symbol", "")))
        else:  # Default sort
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Apply limit
        if limit and limit > 0:
            filtered_rows = filtered_rows[:limit]
        
        # Prepare response data
        response_data = {
            "rows": filtered_rows,
            "count": len(filtered_rows),
            "filtered_params": {
                "horizon": horizon,
                "asset_type": asset_type,
                "sort_by": sort_by,
                "limit": limit,
                "tickers": tickers,
                "themes": themes
            },
            "freshness": forecasts_data.get("freshness") or forecasts_data.get("last_update"),
            "generated_at": datetime.utcnow().isoformat(),
            "source": forecasts_data.get("source", ["forecast_pipeline"])
        }
        
        return ok(response_data)
        
    except Exception as e:
        # Return structured response even on error to maintain never-empty contract
        return ok({
            "rows": [],
            "count": 0,
            "filtered_params": {
                "horizon": horizon,
                "asset_type": asset_type,
                "limit": limit,
                "tickers": tickers,
                "themes": themes,
                "min_confidence": min_confidence
            },
            "error": str(e),
            "message": "Forecasts temporarily unavailable - showing fallback data",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback", "error_handling"]
        })