"""
Intelligence API Routes
Provides LLM-powered market intelligence insights

Task: FC-INT-020
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Integration: CLAUDE-CODE (connecting backend services to API)
"""
from fastapi import APIRouter, HTTPException
from core.response import ok, err
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/snapshot")
async def get_intelligence_snapshot():
    """
    Get current market intelligence snapshot with LLM insights.

    Returns:
        - Market regime analysis
        - Top opportunities (tickers + reasoning)
        - Key risks (type + severity + description)
        - Summary with actionnable insights
        - Data freshness indicators

    Response structure matches frontend useIntelligence hook expectations.
    """
    try:
        from services.intelligence_service import get_market_intelligence_snapshot

        # Use the function-based service (not class-based)
        snapshot = get_market_intelligence_snapshot(use_cache=True, persist=True)
        
        # Ensure snapshot has the expected structure
        if not isinstance(snapshot, dict):
            logger.warning(f"Intelligence snapshot is not a dict: {type(snapshot)}")
            snapshot = {}

        return ok(snapshot)

    except ImportError as e:
        logger.error(f"Intelligence service import error: {str(e)}", exc_info=True)
        # Return graceful fallback
        return ok({
            "insights": {
                "summary": "Intelligence service temporarily unavailable. System is gathering market data.",
                "market_regime": {
                    "current": "NORMAL",
                    "explanation": "Market analysis in progress"
                },
                "opportunities": [],
                "risks": []
            },
            "data_freshness": {
                "forecasts_age": "unknown",
                "macro_age": "unknown",
                "news_age": "unknown"
            },
            "timestamp": None,
            "status": "fallback"
        })
    except Exception as e:
        logger.error(f"Intelligence snapshot error: {str(e)}", exc_info=True)

        # Return graceful fallback
        return ok({
            "insights": {
                "summary": "Intelligence service temporarily unavailable. System is gathering market data.",
                "market_regime": {
                    "current": "NORMAL",
                    "explanation": "Market analysis in progress"
                },
                "opportunities": [],
                "risks": []
            },
            "data_freshness": {
                "forecasts_age": "unknown",
                "macro_age": "unknown",
                "news_age": "unknown"
            },
            "timestamp": None,
            "status": "fallback"
        })

# Export router with expected name for main.py registration
intelligence_router = router
