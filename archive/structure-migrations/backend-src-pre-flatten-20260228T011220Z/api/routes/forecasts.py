"""Forecasts API routes (orchestrator-only).

Business logic lives in `services/forecasts_service.py`.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

try:
    from src.core.response import ok
except Exception:  # pragma: no cover
    def ok(data):
        return {"ok": True, "data": data}

from storage.io import load_json

try:
    from schemas.forecasts import (  # type: ignore
        ForecastDetailResponse,
        ForecastSortBy,
        ForecastSortOrder,
        ForecastsResponse,
    )
except Exception:  # pragma: no cover
    ForecastsResponse = None  # type: ignore
    ForecastDetailResponse = None  # type: ignore
    ForecastSortBy = str  # type: ignore
    ForecastSortOrder = str  # type: ignore

try:
    from services import forecasts_service
except Exception:  # pragma: no cover
    from src.services import forecasts_service  # type: ignore


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forecasts")

# Expose service state for test/backward-compat contract checks.
_FORECASTS_RESPONSE_CACHE = forecasts_service._FORECASTS_RESPONSE_CACHE
_FORECASTS_INFLIGHT = forecasts_service._FORECASTS_INFLIGHT
_FORECASTS_INFLIGHT_LOCK = forecasts_service._FORECASTS_INFLIGHT_LOCK


@router.get(
    "",
    response_model=ForecastsResponse if ForecastsResponse is not None else None,
    response_model_exclude_none=True,
)
async def get_forecasts(
    asset_type: str = Query("all", description="Asset type: equity, commodity, crypto, all"),
    horizon: str = Query("all", description="Horizon: 1w, 1m, 3m, all"),
    ticker: Optional[List[str]] = Query(None, description="Filter by ticker symbols"),
    search: Optional[str] = Query(None, description="Search term"),
    sort_by: ForecastSortBy = Query(  # type: ignore[valid-type]
        "score",
        description="Sort by: score, confidence, expected_return, timestamp, risk_level",
    ),
    sort_order: ForecastSortOrder = Query("desc", description="Sort order (asc/desc)"),  # type: ignore[valid-type]
    limit: int = Query(50, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    debug: bool = Query(False, description="Bypass cache and include debug_pipeline traces."),
):
    try:
        payload = await forecasts_service.get_forecasts_payload(
            asset_type=asset_type,
            horizon=horizon,
            ticker=ticker,
            search=search,
            sort_by=str(sort_by),
            sort_order=str(sort_order),
            limit=limit,
            offset=offset,
            debug=debug,
            load_json_fn=load_json,
        )
        return ok(payload)
    except Exception as route_exc:
        logger.error("Error in get_forecasts route orchestration: %s", route_exc, exc_info=True)
        # Never-empty route-level fallback.
        return ok(
            {
                "rows": [],
                "count": 0,
                "total": 0,
                "offset": int(offset),
                "limit": int(limit),
                "generated_at": "",
                "freshness": "",
                "last_update": "",
                "source": ["forecasts_route", "critical_route_error_fallback"],
                "filters_applied": {
                    "asset_type": asset_type,
                    "horizon": horizon,
                    "search": search,
                    "sort_by": str(sort_by),
                    "sort_order": str(sort_order),
                    "tickers": sorted(
                        {
                            str(item).strip().upper()
                            for item in (ticker or [])
                            if str(item).strip()
                        }
                    ),
                    "limit": int(limit),
                    "offset": int(offset),
                },
                "stats": {
                    "total_loaded": 0,
                    "filtered_count": 0,
                    "returned_count": 0,
                    "high_confidence_count": 0,
                    "high_confidence_percentage": 0.0,
                    "avg_confidence": 0.0,
                },
                "warnings": [],
                "cache": {"hit": False, "age_seconds": 0.0, "ttl_seconds": 0},
                "error": str(route_exc),
                "message": "Forecasts route failed critically but returned never-empty fallback.",
            }
        )


@router.get(
    "/{forecast_id}",
    response_model=ForecastDetailResponse if ForecastDetailResponse is not None else None,
    response_model_exclude_none=True,
)
async def get_forecast(forecast_id: str):
    try:
        payload = forecasts_service.get_forecast_detail_payload(
            forecast_id=forecast_id,
            load_json_fn=load_json,
        )
        return ok(payload)
    except Exception as exc:
        logger.error("Error in get_forecast route orchestration: %s", exc, exc_info=True)
        return ok(
            {
                "forecast": {},
                "found": False,
                "generated_at": "",
                "freshness": "",
                "last_update": "",
                "source": ["forecasts_route", "critical_route_error_fallback"],
                "warnings": [],
                "error": str(exc),
                "message": "Forecast temporarily unavailable, returning empty response per never-empty pattern.",
            }
        )


forecasts_router = router
