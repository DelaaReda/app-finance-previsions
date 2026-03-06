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

try:
    from platform.edge.contracts import edge_degraded, edge_enabled, edge_ok
    from platform.edge.critical_endpoints import (
        forecasts_degraded as edge_forecasts_degraded,
        forecasts_ok as edge_forecasts_ok,
    )
except Exception:  # pragma: no cover
    edge_ok = lambda data, **_: {"ok": True, "data": data}  # type: ignore
    edge_degraded = (  # type: ignore
        lambda data, code, message, detail=None, **_: {
            "ok": True,
            "status": "degraded",
            "data": data,
            "error": {"code": code, "message": message, "detail": detail},
            "meta": {"source": ["legacy_fallback"], "fallback": True},
        }
    )
    edge_enabled = lambda *_args, **_kwargs: False  # type: ignore
    edge_forecasts_ok = lambda data, **_: {"ok": True, "data": data}  # type: ignore
    edge_forecasts_degraded = lambda data, detail=None, **_: {"ok": True, "data": data}  # type: ignore

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
EDGE_FORECASTS_FLAG = "FC_API_EDGE_FORECASTS"

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
        if edge_enabled(EDGE_FORECASTS_FLAG, default=True):
            return edge_forecasts_ok(payload)
        return ok(payload)
    except Exception as route_exc:
        logger.error("Error in get_forecasts route orchestration: %s", route_exc, exc_info=True)
        # Never-empty route-level fallback.
        fallback_payload = {
            "rows": [],
            "count": 0,
            "total": 0,
            "offset": int(offset),
            "limit": int(limit),
            "generated_at": "",
            "freshness": "",
            "freshness_status": "unknown",
            "freshness_age": -1.0,
            "last_update": "",
            "source": ["forecasts_route", "critical_route_error_fallback"],
            "provider_chain": ["route_exception_fallback"],
            "fallback_used": True,
            "latency_ms": 0.0,
            "observability": {
                "provider_chain": ["route_exception_fallback"],
                "fallback_used": True,
                "latency_ms": 0.0,
                "freshness_age": -1.0,
            },
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
        if edge_enabled(EDGE_FORECASTS_FLAG, default=True):
            return edge_forecasts_degraded(fallback_payload, detail=str(route_exc))
        return ok(fallback_payload)


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
        if edge_enabled(EDGE_FORECASTS_FLAG, default=True):
            return edge_ok(
                payload,
                source=["forecasts_route", "forecast_detail"],
                fallback=not bool(payload.get("found")) if isinstance(payload, dict) else False,
            )
        return ok(payload)
    except Exception as exc:
        logger.error("Error in get_forecast route orchestration: %s", exc, exc_info=True)
        fallback_payload = {
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
        if edge_enabled(EDGE_FORECASTS_FLAG, default=True):
            return edge_degraded(
                fallback_payload,
                code="forecast_detail_unavailable",
                message="Forecast detail unavailable, degraded fallback payload returned.",
                detail=str(exc),
                source=["forecasts_route", "critical_route_error_fallback"],
                fallback=True,
            )
        return ok(fallback_payload)


forecasts_router = router
