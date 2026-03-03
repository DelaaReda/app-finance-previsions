"""
Correlations API Routes

Exposes correlation intelligence service endpoints.

Author: ELENA-39
Task: FC-INT-025
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException

try:
    from domains.market_data.application.correlation_intelligence_service import (
        get_correlation_intelligence_service,
    )
except ImportError:
    try:
        from backend.services.correlation_intelligence_service import get_correlation_intelligence_service  # type: ignore
    except ImportError:
        get_correlation_intelligence_service = None

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/analyzed")
async def get_analyzed_correlations(
    universe: Optional[List[str]] = Query(None, description="List of tickers to analyze"),
    window: str = Query('30d', description="Time window for correlation (e.g., '30d', '90d')"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum correlation strength (0.0-1.0)")
):
    """
    Get analyzed correlations with LLM explanations
    
    Returns:
    - Correlation matrix
    - Interesting pairs with strong correlations
    - LLM-powered explanations of WHY correlations exist
    - Actionable trading implications
    """
    try:
        if not get_correlation_intelligence_service:
            raise HTTPException(
                status_code=503,
                detail="Correlation Intelligence Service not available"
            )
        
        service = get_correlation_intelligence_service()
        result = await service.generate_correlation_intelligence(
            universe=universe,
            window=window,
            threshold=threshold
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get correlation intelligence: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate correlation intelligence: {str(e)}"
        )

# Export router with expected name for main.py registration
correlations_router = router
