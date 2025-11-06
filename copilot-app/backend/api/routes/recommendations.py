"""
Recommendations API Routes

Endpoints for smart daily recommendations.

Author: ELENA-39
Task: FC-INT-023
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional

try:
    from backend.services.recommendations_service import get_recommendations_service
except ImportError:
    get_recommendations_service = None

router = APIRouter()


@router.get("/daily")
async def get_daily_recommendations(
    universe: Optional[List[str]] = Query(None, description="List of tickers to consider"),
    limit: int = Query(3, ge=1, le=10, description="Number of recommendations (1-10)")
):
    """
    Get daily smart recommendations
    
    Combines ML ranking with LLM validation to generate
    actionable daily recommendations.
    
    Args:
        universe: Optional list of tickers to analyze. If not provided, uses default universe.
        limit: Number of recommendations to return (1-10, default 3)
    
    Returns:
        JSON with recommendations, market context, and validity period
        
    Example response:
        {
          "recommendations": [
            {
              "ticker": "AAPL",
              "action": "BUY",
              "score": 0.87,
              "reasoning": "Strong momentum post-earnings...",
              "catalysts": ["Q4 earnings beat", "..."],
              "risk_level": "MEDIUM",
              "confidence": 0.85,
              "supporting_data": {...}
            }
          ],
          "market_context": {
            "regime": "NORMAL",
            "summary": "...",
            "key_drivers": [...]
          },
          "generated_at": "2025-11-06T...",
          "valid_until": "2025-11-07T..."
        }
    """
    if not get_recommendations_service:
        raise HTTPException(
            status_code=503,
            detail="Recommendations service not available"
        )
    
    try:
        service = get_recommendations_service()
        recommendations = await service.generate_daily_recommendations(
            universe=universe,
            limit=limit
        )
        return recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )
