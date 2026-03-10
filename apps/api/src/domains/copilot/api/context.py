"""
Context API Routes
Provides market regime detection and adaptive UI recommendations

Task: FC-INT-021
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Integration: CLAUDE-CODE (connecting backend services to API)
BATCH-15-DEV-02: Added playbook resolution to context response
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
        - Strategy playbook (BATCH-15-DEV-02): playbook_id, name, description, guardrails

    Response structure matches frontend useMarketContext hook expectations.
    BATCH-15-DEV-02: Now includes playbook_id for recommendation alignment.
    """
    try:
        try:
            from domains.copilot.application.context_service import ContextService
        except Exception:
            from services.context_service import ContextService  # type: ignore

        # Import playbook resolver (BATCH-15-DEV-02)
        try:
            from domains.copilot.application.playbook_resolver import resolve_playbook_for_context
        except Exception:
            resolve_playbook_for_context = None  # type: ignore

        service = ContextService()
        if hasattr(service, "get_current_market_context"):
            context = await service.get_current_market_context()
        else:
            context = await service.get_current_context()  # type: ignore[attr-defined]

        # Enrich with playbook (BATCH-15-DEV-02)
        if resolve_playbook_for_context:
            regime = context.get("regime", "NORMAL")
            # Default to moderate risk profile for context endpoint
            # (user-specific profile will be used in recommendation endpoint)
            risk_profile = "moderate"
            
            playbook_data = resolve_playbook_for_context(regime, risk_profile)
            context["strategy_playbook"] = playbook_data
            context["playbook_id"] = playbook_data.get("id")

        return ok(context)

    except Exception as e:
        logger.error(f"Context service error: {str(e)}", exc_info=True)

        # Return graceful fallback
        fallback = {
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
        }
        
        # Add fallback playbook (BATCH-15-DEV-02)
        try:
            from domains.copilot.application.playbook_resolver import resolve_playbook_for_context
            playbook_data = resolve_playbook_for_context("normal", "moderate")
            fallback["strategy_playbook"] = playbook_data
            fallback["playbook_id"] = playbook_data.get("id")
        except Exception:
            fallback["strategy_playbook"] = None
            fallback["playbook_id"] = "normal_moderate_001"
        
        return ok(fallback)

# Export router with expected name for main.py registration
context_router = router
