"""
Context API Routes
Provides market regime detection and adaptive UI recommendations

Task: FC-INT-021
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Integration: CLAUDE-CODE (connecting backend services to API)
"""
from fastapi import APIRouter, HTTPException
from core.response import ok, err
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/current")
async def get_current_context():
    """
    Get current market context with regime classification and UI recommendations.

    Returns:
        - Market regime (HIGH_VOLATILITY, BULL_MARKET, BEAR_MARKET, etc.)
        - Confidence score
        - Key drivers
        - Market characteristics (volatility, sentiment, trend, momentum, risk_level)
        - Recommended layout (primary/secondary widgets, filters, emphasis)

    Response structure matches frontend useMarketContext hook expectations.
    """
    try:
        try:
            from domains.copilot.application.context_service import ContextService
        except Exception:
            from services.context_service import ContextService  # type: ignore

        service = ContextService()
        if hasattr(service, "get_current_market_context"):
            context = await service.get_current_market_context()
        else:
            context = await service.get_current_context()  # type: ignore[attr-defined]

        return ok(context)

    except Exception as e:
        logger.error(f"Context service error: {str(e)}", exc_info=True)

        # Return graceful fallback
        return ok({
            "regime": "NORMAL",
            "confidence": 0.5,
            "key_drivers": ["Market analysis in progress"],
            "characteristics": {
                "volatility": "medium",
                "sentiment": "neutral",
                "trend": "sideways",
                "momentum": "moderate",
                "risk_level": "medium"
            },
            "recommended_layout": {
                "primary_widgets": ["ForecastsWidget", "NewsWidget"],
                "secondary_widgets": ["BacktestsWidget"],
                "filters": {},
                "emphasis": "balanced"
            },
            "timestamp": None,
            "status": "fallback"
        })

# Export router with expected name for main.py registration
context_router = router
