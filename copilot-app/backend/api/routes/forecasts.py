"""
API Routes for Forecasts - Dashboard Integration
Provides filtered forecasting data for the dashboard with never-empty guarantee
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, Optional, List
import json
from datetime import datetime
import sys
from pathlib import Path

# Add backend root to sys.path for proper imports
backend_root = Path(__file__).resolve().parents[2]  # Go from backend/api/routes/forecasts.py to backend/
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from core.response import ok, err
from storage.io import load_json
import logging

# Import cache service for performance optimization
try:
    from services.cache_service import cache_service
    from services.cache_service import cache_service as cache_service_obj
except ImportError:  # pragma: no cover
    cache_service = None
    cache_service_obj = None

logger = logging.getLogger(__name__)

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
    Implements memory caching for performance (BE-007).
    """
    # Create cache key based on all parameters to ensure proper caching
    cache_params = {
        "horizon": horizon,
        "asset_type": asset_type,
        "sort_by": sort_by,
        "limit": limit,
        "tickers": tickers,
        "themes": themes,
        "min_confidence": min_confidence
    }
    
    # Check if cache_service exists before using it
    cache_key = None
    if cache_service_obj and hasattr(cache_service_obj, 'get_cache_key'):
        cache_key = cache_service_obj.get_cache_key("/api/forecasts", cache_params)
    else:
        # Simple cache key generation if cache_service not available
        cache_key = f"/api/forecasts_{hash(str(cache_params))}"
    
    logger.info(f"📥 GET /api/forecasts - Request received (cache key: {cache_key})", extra={
        "horizon": horizon,
        "asset_type": asset_type,
        "sort_by": sort_by,
        "limit": limit,
        "tickers": tickers,
        "themes": themes,
        "min_confidence": min_confidence
    })
    
    # First, try to get from cache if service exists
    cached_result = None
    if cache_service_obj:
        try:
            cached_result = cache_service_obj.get("/api/forecasts", cache_params)
        except:
            logger.warning("Cache service unavailable, proceeding without cache")
            cached_result = None
    
    if cached_result is not None:
        logger.info(f"💾 Cache HIT for /api/forecasts with {len(cached_result.get('rows', []))} rows", extra={
            "cache_key": cache_key
        })
        return ok({
            **cached_result,
            "cache_hit": True,
            "freshness": "cached"
        })
    
    # If not in cache, compute fresh results
    try:
        logger.debug(f"📂 Loading forecasts from storage (cache miss)...")
        # Load forecasts from persistent storage (following never-empty pattern)
        forecasts_data = load_json("forecasts")
        
        if not forecasts_data:
            logger.warning(f"⚠️ No forecasts data found in storage", extra={
                "filters": {
                    "horizon": horizon,
                    "asset_type": asset_type,
                    "limit": limit
                }
            })
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
        
        logger.info(f"📊 Loaded {len(all_rows)} forecast rows from storage", extra={
            "total_rows": len(all_rows),
            "data_structure": "data.rows" if "data" in forecasts_data else "direct"
        })
        
        # Apply filtering
        filtered_rows = all_rows
        initial_count = len(filtered_rows)
        
        # Track initial count for logging purposes
        current_count = initial_count
        
        if asset_type and asset_type != "all":
            filtered_rows = [row for row in filtered_rows if row.get("asset_type", row.get("type", "equity")).lower() == asset_type.lower()]
            logger.debug(f"🔍 Filtered by asset_type={asset_type}: {current_count} → {len(filtered_rows)} rows")
            current_count = len(filtered_rows)
        
        if horizon and horizon != "all":
            # Map frontend horizon values to backend values
            # If data doesn't have horizon field, default to "short" for compatibility
            horizon_mapping = {
                "short": ["1d", "5d", "1w", "short"],
                "medium": ["1mo", "3mo", "medium"],
                "long": ["6mo", "1y", "2y", "long"]
            }
            # If horizon filter is specified, match against mapped values or exact match
            if horizon in horizon_mapping:
                allowed_horizons = horizon_mapping[horizon]
                filtered_rows = [
                    row for row in filtered_rows
                    # If row has no horizon, include it for "short" (default)
                    if (row.get("horizon") is None and horizon == "short") or
                       (row.get("horizon") in allowed_horizons) or row.get("horizon") == horizon
                ]
            else:
                # Exact match for other horizon values, or include if no horizon and filtering for "short"
                filtered_rows = [
                    row for row in filtered_rows
                    if (row.get("horizon") is None and horizon == "short") or row.get("horizon", "short") == horizon
                ]
            logger.debug(f"🔍 Filtered by horizon={horizon}: {current_count} → {len(filtered_rows)} rows")
            current_count = len(filtered_rows)
        
        if tickers:
            before_tickers = len(filtered_rows)
            filtered_rows = [row for row in filtered_rows if row.get("ticker") in tickers or row.get("symbol") in tickers]
            logger.debug(f"🔍 Filtered by tickers: {before_tickers} → {len(filtered_rows)} rows")
        
        if themes:
            before_themes = len(filtered_rows)
            filtered_rows = [row for row in filtered_rows if row.get("theme") in themes or row.get("category") in themes]
            logger.debug(f"🔍 Filtered by themes: {before_themes} → {len(filtered_rows)} rows")
        
        # Filter by minimum confidence (Sprint 5 - Task 5.1)
        if min_confidence and min_confidence > 0:
            before_confidence = len(filtered_rows)
            filtered_rows = [
                row for row in filtered_rows
                if row.get("confidence", 0) >= min_confidence
            ]
            logger.debug(f"🔍 Filtered by min_confidence={min_confidence}: {before_confidence} → {len(filtered_rows)} rows")
        
        # Sort results
        logger.debug(f"🔀 Sorting by {sort_by}...")
        if sort_by == "confidence":
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("confidence", 0), reverse=True)
        elif sort_by == "expected_return":
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("expected_return", 0), reverse=True)
        elif sort_by == "ticker":
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("ticker", x.get("symbol", "")), reverse=True)
        else:  # Default sort by confidence
            filtered_rows = sorted(filtered_rows, key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Apply limit
        before_limit = len(filtered_rows)
        if limit and limit > 0:
            limit_val = min(limit, 200)  # Cap limit to 200
            filtered_rows = filtered_rows[:limit_val]
            logger.debug(f"✂️ Applied limit={limit_val}: {before_limit} → {len(filtered_rows)} rows")
        
        logger.info(f"✅ Forecasts filtered successfully", extra={
            "initial_count": initial_count,
            "final_count": len(filtered_rows),
            "filters_applied": {
                "asset_type": asset_type != "all" if asset_type else False,
                "horizon": horizon != "all" if horizon else False,
                "tickers": tickers is not None,
                "themes": themes is not None,
                "min_confidence": min_confidence > 0 if min_confidence else False
            }
        })
        
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
        
        # Cache the response for future requests (BE-007 - Memory caching)
        if cache_service_obj:
            try:
                cache_service_obj.set("/api/forecasts", response_data, cache_params, ttl_seconds=300)  # 5 min cache
            except:
                logger.warning("Cache service unavailable for saving, proceeding without caching")
        
        logger.info(f"✅ Returning {len(filtered_rows)} forecasts to client (cached for 300s)")
        return ok({
            **response_data,
            "cache_hit": False,
            "freshness": "fresh",
            "cache_age": "0s"
        })
        
    except Exception as e:
        logger.error(f"❌ Error in forecasts endpoint: {str(e)}", exc_info=True, extra={
            "error_type": type(e).__name__,
            "filters": {
                "horizon": horizon,
                "asset_type": asset_type,
                "limit": limit
            }
        })
        # Return structured response even on error to maintain never-empty contract
        error_response = {
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
        }
        
        # Even in error cases, we can cache the error response to avoid repeated computations if cache service available
        if cache_service_obj:
            try:
                cache_service_obj.set("/api/forecasts", error_response, cache_params, ttl_seconds=60)  # 1 min cache for errors
            except:
                logger.warning("Cache service unavailable for saving error response")
        
        return ok({
            **error_response,
            "cache_hit": False,
            "freshness": "error_fallback"
        })

# Export router with expected name for main.py
forecasts_router = router