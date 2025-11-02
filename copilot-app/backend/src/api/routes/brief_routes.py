# src/api/routes/brief_routes.py
"""
Routes for brief and signals endpoints (scoring composite 40/40/20)
"""
from fastapi import APIRouter, Query, HTTPException, status
from typing import List, Optional

from api.schemas import (
    BriefResponse, SignalsResponse,
    ErrorResponse
)
from api.services.scoring_service import (
    build_brief,
    get_signals_top
)

router = APIRouter(prefix="/api", tags=["brief"])


@router.get(
    "/brief",
    response_model=BriefResponse,
    summary="Market brief with composite scoring"
)
async def get_brief(
    period: str = Query("weekly", regex="^(daily|weekly)$"),
    universe: Optional[List[str]] = Query(None, description="Tickers to analyze")
):
    """
    Get market brief with composite scoring (40% macro + 40% tech + 20% news).
    
    Returns:
    - Top 3 signals (high scores)
    - Top 3 risks (low scores)
    - Top 3 picks with rationale
    - Citations and sources
    """
    try:
        data = build_brief(
            period=period,
            universe=universe or ["SPY", "QQQ", "AAPL", "NVDA", "MSFT"]
        )
        return BriefResponse(ok=True, data=data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate brief: {str(e)}"
        )


@router.get(
    "/signals/top",
    response_model=SignalsResponse,
    summary="Top 3 signals and top 3 risks"
)
async def signals_top():
    """
    Get top 3 bullish signals and top 3 bearish risks based on composite scoring.
    
    Scoring breakdown:
    - Macro: 40%
    - Technical: 40%
    - News: 20%
    """
    try:
        data = get_signals_top()
        return SignalsResponse(ok=True, data=data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute signals: {str(e)}"
        )
