"""
API Routes for Macro Data - Dashboard Integration
Provides filtered macroeconomic data for the dashboard with never-empty guarantee
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timedelta

from core.response import ok, err
from storage.io import load_json

router = APIRouter()

@router.get("/macro/series")
def get_filtered_macro_series(
    ids: Optional[List[str]] = Query(None, description="FRED series IDs: CPIAUCSL, VIXCLS, DGS10, etc."),
    limit: Optional[int] = Query(200, description="Limit number of data points returned"),
    window: Optional[str] = Query("1y", description="Time window: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
    format_resp: Optional[str] = Query("array", description="Response format: array, map")
) -> Dict[str, Any]:
    """
    Dashboard macro series endpoint with filtering capabilities.
    Returns macro data with proper structure for dashboard UI components.
    """
    try:
        # Load macro data from persistent storage (following never-empty pattern)
        macro_data = load_json("macro_series")
        
        if not macro_data:
            # Return empty structure with metadata but never fail
            return ok({
                "series": [],
                "count": 0,
                "filtered_params": {
                    "ids": ids,
                    "limit": limit,
                    "window": window,
                    "format": format_resp
                },
                "message": "No macro data available - system fetching from FRED in background",
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback_empty"]
            })
        
        # Extract macro series data
        data_payload = macro_data.get("data", macro_data.get("payload", macro_data))
        all_series = data_payload.get("series", data_payload if isinstance(data_payload, list) else [])
        
        # Apply filtering
        filtered_series = all_series
        
        # Filter by specific IDs if specified
        if ids:
            filtered_series = [
                series for series in filtered_series
                if series.get("id") in ids or series.get("series_id") in ids or series.get("name") in ids
            ]
        
        # Apply time window filter
        if window:
            # Parse the time window
            time_multiplier = {"d": 1, "mo": 30, "y": 365}  # days in each period
            if len(window) > 1 and window[-1:] in ["d", "y"] or (len(window) > 2 and window[-2:] == "mo"):
                try:
                    if window.endswith("mo"):
                        num = int(window[:-2])
                        days_back = num * 30
                    else:
                        suffix = window[-1:]
                        num = int(window[:-1])
                        days_back = num * time_multiplier[suffix]
                    
                    cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat().split("T")[0]  # Date only
                    
                    for series in filtered_series:
                        if "data" in series and isinstance(series["data"], list):
                            series["data"] = [
                                point for point in series["data"]
                                if point.get("date", "")[:10] >= cutoff_date  # Compare date part only
                            ]
                            
                            # Apply point limit within each series
                            if limit and limit > 0:
                                series["data"] = series["data"][-limit:]  # Take last N points
                                
                except (ValueError, IndexError):
                    # If parsing fails, skip time window filtering
                    pass
        
        # Apply limit to number of series if specified (not per series)
        if limit and limit > 0 and len(filtered_series) > limit:
            filtered_series = filtered_series[:limit]
        
        # Format response based on format_resp parameter
        response_data = {
            "series": filtered_series,
            "count": len(filtered_series),
            "filtered_params": {
                "ids": ids,
                "limit": limit,
                "window": window,
                "format": format_resp
            },
            "freshness": macro_data.get("freshness") or macro_data.get("last_update"),
            "generated_at": datetime.utcnow().isoformat(),
            "source": macro_data.get("source", ["macro_pipeline", "fred"])
        }
        
        # If format is 'map', transform to a mapping indexed by series ID
        if format_resp == "map":
            series_map = {}
            for series in filtered_series:
                series_id = series.get("id") or series.get("series_id") or series.get("name", f"series_{len(series_map)}")
                series_map[series_id] = series
            response_data["series_map"] = series_map
            response_data["format"] = "map"
        
        return ok(response_data)
        
    except Exception as e:
        # Return structured response even on error to maintain never-empty contract
        return ok({
            "series": [],
            "count": 0,
            "filtered_params": {
                "ids": ids,
                "limit": limit,
                "window": window,
                "format": format_resp
            },
            "error": str(e),
            "message": "Macro data temporarily unavailable - showing fallback data",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback", "error_handling"]
        })