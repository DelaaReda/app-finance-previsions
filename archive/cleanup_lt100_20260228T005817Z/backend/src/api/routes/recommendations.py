"""
Recommendations API Routes
Provides daily ML+LLM powered stock recommendations

Task: FC-INT-023
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Integration: CLAUDE-CODE (connecting backend services to API)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from core.response import ok, err
import logging

try:
    from backend.services.recommendations_service import RecommendationsService  # type: ignore
except ImportError:  # pragma: no cover
    try:
        from services.recommendations_service import RecommendationsService  # type: ignore
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

        return ok(recommendations)

    except Exception as e:
        logger.error(f"Recommendations service error: {str(e)}", exc_info=True)

        # Return graceful fallback
        return ok({
            "recommendations": [],
            "market_context": {
                "regime": "NORMAL",
                "summary": "Recommendations service temporarily unavailable",
                "key_drivers": []
            },
            "generated_at": None,
            "valid_until": None,
            "status": "fallback"
        })

# Export router with expected name for main.py registration
recommendations_router = router
