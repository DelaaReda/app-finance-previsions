"""
API Routes for Macro Data - Dashboard Integration
Provides filtered macroeconomic data for the dashboard with never-empty guarantee
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Sprint 2 - Tâche 2.2 - Caching données macro
"""
from fastapi import APIRouter, Query, Response
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime, timedelta

from core.response import ok, err
from storage.io import load_json

logger = logging.getLogger(__name__)

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
        # 0. Try to load from cache first (Sprint 2 - Tâche 2.2 - Cache)
        try:
            cached_macro = load_json("macro_series")
            if cached_macro:
                # Extract data if wrapped
                cached_data = cached_macro.get("data") or cached_macro.get("payload") or cached_macro
                # Check freshness (1h max age for macro data - Tâche 2.2)
                cached_at = cached_data.get("freshness") or cached_macro.get("last_update") or cached_macro.get("generated_at")
                if cached_at:
                    try:
                        cached_time = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
                        age = (datetime.utcnow() - cached_time.replace(tzinfo=None)).total_seconds()
                        if age < 3600:  # 1 hour (3600 seconds)
                            logger.info(f"✅ Serving cached macro series (age: {age:.0f}s)")
                            # Apply filters to cached data
                            filtered_response = _apply_macro_filters(cached_data, ids, limit, window, format_resp)
                            # Return with cache headers
                            return Response(
                                content=json.dumps(ok(filtered_response)),
                                media_type="application/json",
                                headers={
                                    "Cache-Control": "public, max-age=3600",  # 1h browser cache
                                    "ETag": f'"{hash(str(filtered_response))}"',  # Simple ETag
                                }
                            )
                    except Exception:
                        pass  # Continue to load if cache invalid
        except Exception as e:
            logger.debug(f"Cache check failed: {e}")
        
        # 1. Load macro data from persistent storage (following never-empty pattern)
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
        
        # Apply filtering (extracted to helper function for cache reuse)
        filtered_response = _apply_macro_filters(data_payload, ids, limit, window, format_resp, all_series)
        
        # Add freshness and metadata
        filtered_response["freshness"] = macro_data.get("freshness") or macro_data.get("last_update")
        filtered_response["generated_at"] = datetime.utcnow().isoformat()
        filtered_response["source"] = macro_data.get("source", ["macro_pipeline", "fred"])
        
        # Return with cache headers (Tâche 2.2 - HTTP Cache)
        return Response(
            content=json.dumps(ok(filtered_response)),
            media_type="application/json",
            headers={
                "Cache-Control": "public, max-age=3600",  # 1h browser cache
                "ETag": f'"{hash(str(filtered_response))}"',  # Simple ETag
            }
        )
        
    except Exception as e:
        # Return structured response even on error to maintain never-empty contract
        error_response = {
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
        }
        return ok(error_response)


def _apply_macro_filters(
    data_payload: Dict[str, Any],
    ids: Optional[List[str]],
    limit: Optional[int],
    window: Optional[str],
    format_resp: Optional[str],
    all_series: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Helper function to apply filters to macro series data.
    Used both for cached and fresh data.
    """
    if all_series is None:
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
        }
    }
    
    # If format is 'map', transform to a mapping indexed by series ID
    if format_resp == "map":
        series_map = {}
        for series in filtered_series:
            series_id = series.get("id") or series.get("series_id") or series.get("name", f"series_{len(series_map)}")
            series_map[series_id] = series
        response_data["series_map"] = series_map
        response_data["format"] = "map"
    
    # Enhance data format for Tremor charts - ensure data points have proper structure
    for series in response_data["series"]:
        if "data" in series and isinstance(series["data"], list):
            # Ensure data points are in the format expected by Tremor (with proper date/value fields)
            formatted_data = []
            for point in series["data"]:
                if isinstance(point, dict):
                    # Ensure the data point has both date and value fields for Tremor charts
                    formatted_point = {
                        "date": point.get("date") or point.get("timestamp") or point.get("time") or "",
                        "value": point.get("value") or point.get("level") or point.get("close") or point.get("price") or 0.0,
                        **{k: v for k, v in point.items() if k not in ["date", "timestamp", "time", "value", "level", "close", "price"]}
                    }
                    formatted_data.append(formatted_point)
                elif isinstance(point, (list, tuple)) and len(point) >= 2:
                    # Handle list format [date, value]
                    formatted_data.append({
                        "date": point[0],
                        "value": point[1]
                    })
            
            series["data"] = formatted_data
    
    return response_data


@router.get("/macro/latest")
def get_macro_latest(
    ids: Optional[List[str]] = Query(None, description="FRED series IDs: CPIAUCSL, VIXCLS, DGS10, etc.")
) -> Dict[str, Any]:
    """
    Get the latest values for specified macro series - useful for live dashboards.
    """
    try:
        # Try to load from cache first
        cached_macro = load_json("macro_series")
        if cached_macro:
            data_payload = cached_macro.get("data") or cached_macro.get("payload") or cached_macro
            all_series = data_payload.get("series", data_payload if isinstance(data_payload, list) else [])
            
            # Filter series by IDs if specified
            if ids:
                filtered_series = [
                    series for series in all_series
                    if series.get("id") in ids or series.get("series_id") in ids or series.get("name") in ids
                ]
            else:
                filtered_series = all_series
            
            # Get the latest data point for each series
            latest_values = []
            for series in filtered_series:
                series_id = series.get("id") or series.get("series_id") or series.get("name", "unnamed")
                series_name = series.get("name") or series.get("title") or series_id
                
                # Get latest data point
                data_points = series.get("data", [])
                if data_points:
                    latest_point = data_points[-1]  # Last point is typically most recent
                    latest_value = {
                        "id": series_id,
                        "name": series_name,
                        "date": latest_point.get("date") or latest_point.get("timestamp") or "",
                        "value": latest_point.get("value") or latest_point.get("level") or latest_point.get("close") or 0.0,
                        "change": latest_point.get("change_pct") or latest_point.get("change") or 0.0,
                        "last_update": data_payload.get("last_update") or datetime.utcnow().isoformat()
                    }
                    latest_values.append(latest_value)
            
            return ok({
                "latest": latest_values,
                "count": len(latest_values),
                "requested_ids": ids,
                "freshness": data_payload.get("freshness") or data_payload.get("last_update"),
                "generated_at": datetime.utcnow().isoformat(),
                "source": data_payload.get("source", ["macro_service"])
            })
        
        # Fallback if no cache data
        return ok({
            "latest": [],
            "count": 0,
            "requested_ids": ids,
            "message": "No macro data available - system fetching from FRED in background",
            "freshness": "unknown",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback_empty"]
        })
        
    except Exception as e:
        return ok({
            "latest": [],
            "count": 0,
            "requested_ids": ids,
            "error": str(e),
            "message": "Error retrieving latest macro values",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["error_fallback"]
        })


# Export router with expected name for main.py registration
macro_router = router