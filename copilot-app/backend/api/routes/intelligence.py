"""
Intelligence API Routes
File: backend/api/routes/intelligence.py
Task: FC-INT-020 - ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from services.intelligence_service import get_intelligence_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/snapshot")
async def get_intelligence_snapshot() -> Dict[str, Any]:
    """
    Get comprehensive market intelligence snapshot.
    
    Combines forecasts, macro indicators, news, and stocks data
    with LLM-generated insights.
    
    Returns:
        {
            'data': {
                'forecasts': [...],
                'macro': {...},
                'news': [...],
                'stocks': {...}
            },
            'insights': {
                'market_regime': {...},
                'opportunities': [...],
                'risks': [...],
                'summary': str
            },
            'metadata': {
                'generated_at': str,
                'freshness': {...}
            }
        }
    """
    try:
        service = get_intelligence_service()
        snapshot = await service.get_market_snapshot_intelligence()
        return snapshot
    except Exception as e:
        logger.error(f"Failed to get intelligence snapshot: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate intelligence snapshot: {str(e)}"
        )
