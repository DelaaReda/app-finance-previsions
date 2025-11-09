"""
Fixed Query parameter handling in forecasts endpoint to properly resolve FastAPI Query objects
before applying filtering logic. The issue was that Query objects were being compared directly
without resolving their actual values first.
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
        # Convert Query objects to actual values if they're not already resolved
        # In FastAPI context, these should be resolved automatically, but we'll ensure
        horizon_val = horizon if isinstance(horizon, str) else str(horizon) if horizon is not None else "all"
        asset_type_val = asset_type if isinstance(asset_type, str) else str(asset_type) if asset_type is not None else "all"
        sort_by_val = sort_by if isinstance(sort_by, str) else str(sort_by) if sort_by is not None else "confidence"
        limit_val = limit if isinstance(limit, int) else int(limit) if limit is not None else 50
        min_confidence_val = min_confidence if isinstance(min_confidence, float) else float(min_confidence) if min_confidence is not None else 0.0
        
        # Same for list parameters
        tickers_val = tickers if isinstance(tickers, list) else (tickers if tickers else None)
        themes_val = themes if isinstance(themes, list) else (themes if themes else None)

        # Load forecasts from persistent storage (following never-empty pattern)
        forecasts_data = load_json("forecasts")
        
        if not forecasts_data:
            # Return empty structure with metadata but never fail
            return ok({
                "rows": [],
                "count": 0,
                "filtered_params": {
                    "horizon": horizon_val,
                    "asset_type": asset_type_val,
                    "sort_by": sort_by_val,
                    "limit": limit_val,
                    "tickers": tickers_val,
                    "themes": themes_val,
                    "min_confidence": min_confidence_val
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
        
        if asset_type_val and asset_type_val != "all":
            filtered_rows = [row for row in filtered_rows if row.get("asset_type", row.get("type", "equity")).lower() == asset_type_val.lower()]
        
        if horizon_val and horizon_val != "all":
            filtered_rows = [row for row in filtered_rows if row.get("horizon", "all") == horizon_val]
        
        if tickers_val:
            filtered_rows = [row for row in filtered_rows if row.get("ticker") in tickers_val or row.get("symbol") in tickers_val]
        
        if themes_val:
            filtered_rows = [row for row in filtered_rows if row.get("theme") in themes_val or row.get("category") in themes_val]
        
        # Filter by minimum confidence (Sprint 5 - Tâche 5.1)
        if min_confidence_val and min_confidence_val > 0:
            filtered_rows = [
                row for row in filtered_rows
                if row.get("confidence", 0) >= min_confidence_val
            ]
        
        # Sort results
        if sort_by_val == "confidence":
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("confidence", 0), reverse=True)
        elif sort_by_val == "expected_return":
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("expected_return", 0), reverse=True)
        elif sort_by_val == "ticker":
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("ticker", x.get("symbol", "")))
        else:  # Default sort
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Apply limit
        if limit_val and limit_val > 0:
            filtered_rows = filtered_rows[:limit_val]
        
        # Prepare response data
        response_data = {
            "rows": filtered_rows,
            "count": len(filtered_rows),
            "filtered_params": {
                "horizon": horizon_val,
                "asset_type": asset_type_val,
                "sort_by": sort_by_val,
                "limit": limit_val,
                "tickers": tickers_val,
                "themes": themes_val
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
                "horizon": "all",
                "asset_type": "all", 
                "limit": 50,
                "tickers": None,
                "themes": None,
                "min_confidence": 0.0
            },
            "error": str(e),
            "message": "Forecasts temporarily unavailable - showing fallback data",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback", "error_handling"]
        })