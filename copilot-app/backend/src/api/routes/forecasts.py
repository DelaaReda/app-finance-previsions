"""
Forecasts API Routes
Implements the /api/forecasts endpoint according to the never-empty pattern with real data
"""
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime
import logging

from src.core.response import ok, err
from src.storage.io import load_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forecasts")

@router.get("")
async def get_forecasts(
    asset_type: str = Query("all", description="Asset type: equity, commodity, all"),
    horizon: str = Query("all", description="Horizon: 1w, 1m, 3m, all"),
    search: Optional[str] = Query(None, description="Search term"),
    sort_by: str = Query("score", description="Sort by: score, confidence, return"),
    limit: int = Query(50, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get forecasts list - serves real data from forecasts.json with never-empty guarantees.
    
    Returns structured response with {ok: true, data: {...}} pattern.
    Even if no forecasts match filters, returns empty array instead of error.
    """
    try:
        # Load forecasts data from storage
        forecasts_data = load_json("forecasts") or load_json("forecasts.json") or {}
        
        # Extract rows with fallback handling
        rows = forecasts_data.get("rows", []) or forecasts_data.get("data", {}).get("rows", []) or []
        
        # Apply filters
        filtered_rows = rows
        
        if asset_type != "all":
            filtered_rows = [r for r in filtered_rows if r.get("asset_type", "").lower() == asset_type.lower()]
        
        if horizon != "all":
            # Only filter if rows carry a horizon field; otherwise keep data (never-empty)
            if any(isinstance(r, dict) and "horizon" in r for r in filtered_rows):
                alias = {
                    "short": {"1d", "1w", "short"},
                    "medium": {"1m", "3m", "medium"},
                    "long": {"6m", "1y", "long"},
                }
                allowed = alias.get(horizon.lower(), {horizon.lower()})
                def _hz(v):
                    if v is None:
                        return ""
                    return str(v).lower()
                filtered_rows = [r for r in filtered_rows if _hz(r.get("horizon")) in allowed]
        
        if search:
            search_lower = search.lower()
            filtered_rows = [
                r for r in filtered_rows
                if search_lower in (r.get("ticker", "") or "").lower()
                or search_lower in (r.get("name", "") or "").lower()
                or search_lower in (r.get("model", "") or "").lower()
            ]
        
        # Sort results
        if sort_by == "confidence":
            filtered_rows.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        elif sort_by == "return":
            filtered_rows.sort(key=lambda x: x.get("expected_return", 0), reverse=True)
        elif sort_by == "score":
            filtered_rows.sort(key=lambda x: x.get("score", 0), reverse=True)
        else:  # Default sorting
            filtered_rows.sort(key=lambda x: x.get("confidence", 0) * x.get("expected_return", 0), reverse=True)
        
        # Apply pagination
        total_count = len(filtered_rows)
        paginated_rows = filtered_rows[offset:offset + limit]
        
        # Create response with freshness metadata
        response_data = {
            "rows": paginated_rows,
            "count": len(paginated_rows),
            "total": total_count,
            "offset": offset,
            "limit": limit,
            "filters": {
                "asset_type": asset_type,
                "horizon": horizon, 
                "search": search,
                "sort_by": sort_by
            },
            "freshness": forecasts_data.get("generated_at") or forecasts_data.get("timestamp") or datetime.utcnow().isoformat(),
            "source": forecasts_data.get("source") or ["forecasts_storage"],
            "last_update": forecasts_data.get("last_update") or forecasts_data.get("generated_at") or datetime.utcnow().isoformat()
        }
        
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"Error in get_forecasts: {e}", exc_info=True)
        # Never return empty - always return structure with empty data
        return ok({
            "rows": [],
            "count": 0,
            "total": 0,
            "offset": 0,
            "limit": limit,
            "filters": {
                "asset_type": asset_type,
                "horizon": horizon,
                "search": search,
                "sort_by": sort_by
            },
            "freshness": datetime.utcnow().isoformat(),
            "source": ["fallback"],
            "last_update": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Forecasts temporarily unavailable, returning empty response per never-empty pattern"
        })


@router.get("/{forecast_id}")
async def get_forecast(forecast_id: str):
    """
    Get specific forecast by ID with detailed information.
    """
    try:
        forecasts_data = load_json("forecasts") or load_json("forecasts.json") or {}
        rows = forecasts_data.get("rows", []) or forecasts_data.get("data", {}).get("rows", []) or []
        
        # Find forecast by ID (could be ticker or forecast id)
        forecast = None
        for row in rows:
            if row.get("id") == forecast_id or row.get("ticker") == forecast_id:
                forecast = row
                break
        
        if forecast is None:
            return ok({
                "forecast": {},
                "found": False,
                "freshness": datetime.utcnow().isoformat(),
                "source": ["forecasts_storage"],
                "last_update": datetime.utcnow().isoformat(),
                "message": f"Forecast {forecast_id} not found"
            })
        
        return ok({
            "forecast": forecast,
            "found": True,
            "freshness": forecasts_data.get("generated_at") or datetime.utcnow().isoformat(),
            "source": forecasts_data.get("source") or ["forecasts_storage"],
            "last_update": forecasts_data.get("last_update") or datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in get_forecast: {e}", exc_info=True)
        return ok({
            "forecast": {},
            "found": False,
            "freshness": datetime.utcnow().isoformat(),
            "source": ["fallback"],
            "last_update": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Forecast temporarily unavailable, returning empty response per never-empty pattern"
        })


# Make router available for import
forecasts_router = router
