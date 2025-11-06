"""
Context API Routes
File: backend/api/routes/context.py
Task: FC-INT-021 - ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from services.context_service import get_context_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/current")
async def get_current_context() -> Dict[str, Any]:
    """
    Get current market context with regime classification and
    adaptive UI layout recommendations.
    
    Returns:
        {
            'regime': str (HIGH_VOLATILITY, BULL_MARKET, RISK_OFF, etc.),
            'confidence': float (0-1),
            'key_drivers': List[str],
            'recommended_layout': {
                'primary_widgets': List[str],
                'filters': Dict,
                'emphasis': str
            },
            'characteristics': {
                'volatility': str,
                'sentiment': str,
                'trend': str,
                'momentum': str,
                'risk_level': str
            },
            'metadata': {...}
        }
    """
    try:
        service = get_context_service()
        context = await service.get_current_market_context()
        return context
    except Exception as e:
        logger.error(f"Failed to get market context: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to determine market context: {str(e)}"
        )
