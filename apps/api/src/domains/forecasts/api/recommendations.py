"""
Recommendations API Routes
Provides daily ML+LLM powered stock recommendations

Task: FC-INT-023
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Integration: CLAUDE-CODE (connecting backend services to API)
"""
from __future__ import annotations

from fastapi import APIRouter, Query
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

try:
    from platform.edge.critical_endpoints import (
        recommendations_degraded,
        recommendations_ok,
    )
except Exception:  # pragma: no cover
    def _edge_meta(source, fallback: bool):
        return {
            "source": list(source),
            "freshness_s": None,
            "request_id": uuid.uuid4().hex[:12],
            "schema_version": "fc-edge-v1",
            "fallback": fallback,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def recommendations_ok(data, **_):  # type: ignore
        return {
            "ok": True,
            "status": "ok",
            "data": data,
            "error": None,
            "meta": _edge_meta(["recommendations_daily", "weekly_brief_snapshot"], False),
        }

    def recommendations_degraded(data, detail=None, **_):  # type: ignore
        return {
            "ok": True,
            "status": "degraded",
            "data": data,
            "error": {
                "code": "recommendations_unavailable",
                "message": "Recommendations temporarily unavailable, fallback payload returned.",
                "detail": detail,
            },
            "meta": _edge_meta(["recommendations_daily", "critical_error_fallback"], True),
        }

try:
    try:
        from domains.forecasts.application.recommendations_service import RecommendationsService  # type: ignore
    except ImportError:  # pragma: no cover
        try:
            from services.recommendations_service import RecommendationsService  # type: ignore
        except ImportError as exc:  # pragma: no cover
            RecommendationsService = None  # type: ignore
            _IMPORT_ERROR = exc
        else:
            _IMPORT_ERROR = None
except ImportError:  # pragma: no cover
    try:
        from backend.services.recommendations_service import RecommendationsService  # type: ignore
    except ImportError as exc:  # pragma: no cover
        RecommendationsService = None  # type: ignore
        _IMPORT_ERROR = exc
    else:
        _IMPORT_ERROR = None
else:
    _IMPORT_ERROR = None

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/daily")
async def get_daily_recommendations(
    universe: Optional[List[str]] = Query(None, description="Optional list of tickers to analyze"),
    limit: int = Query(3, ge=1, le=10, description="Number of recommendations (1-10)")
):
    """
    Get daily top recommendations with ML scoring + LLM validation.

    Query parameters:
        - universe: Optional list of tickers (e.g., ?universe=AAPL&universe=MSFT)
        - limit: Number of recommendations (default: 3, max: 10)

    Returns:
        - recommendations: List of top N recommendations with:
            - ticker, action (BUY/SELL/HOLD)
            - score (ML composite score)
            - reasoning (LLM-generated explanation)
            - catalysts (key factors)
            - risk_level, confidence
            - supporting_data (breakdown of scores)
        - market_context: Current regime + summary
        - generated_at, valid_until timestamps

    Response structure matches frontend useRecommendations hook expectations.
    """
    try:
        if RecommendationsService is None:
            raise _IMPORT_ERROR or ModuleNotFoundError("services.recommendations_service")
        service = RecommendationsService()
        recommendations = await service.generate_daily_recommendations(
            universe=universe,
            limit=limit
        )
        return recommendations_ok(recommendations)

    except Exception as e:
        logger.error(f"Recommendations service error: {str(e)}", exc_info=True)

        # Return graceful fallback
        return recommendations_degraded({
            "recommendations": [],
            "market_context": {
                "regime": "NORMAL",
                "summary": "Recommendations service temporarily unavailable",
                "key_drivers": []
            },
            "generated_at": None,
            "valid_until": None,
            "status": "fallback"
        }, detail=str(e))

# Export router with expected name for main.py registration
recommendations_router = router
