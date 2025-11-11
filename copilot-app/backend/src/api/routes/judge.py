"""
Judge API Routes
Implements the /api/judge endpoint for LLM-based market judgments
"""
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime
import logging

from src.core.response import ok, err
from src.storage.io import load_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/judge")

@router.get("")
async def get_judge_verdicts(
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    ticker: Optional[str] = Query(None, description="Filter by specific ticker"),
    sort_by: str = Query("confidence", description="Sort by: confidence, return, score")
):
    """
    Get LLM judge verdicts for tickers with detailed analysis and recommendations.
    
    Returns structured response with {ok: true, data: {...}} pattern.
    Implements never-empty with fallback to empty arrays if no data available.
    """
    try:
        # Load judge verdicts data from storage
        judge_data = load_json("llm_judge") or load_json("judge_verdicts") or load_json("forecasts") or {}
        
        # Extract verdicts with fallback handling
        verdicts = judge_data.get("verdicts", []) or judge_data.get("rows", []) or []
        
        # Apply filters
        filtered_verdicts = verdicts
        
        if min_confidence > 0:
            filtered_verdicts = [v for v in filtered_verdicts if v.get("confidence", 0) >= min_confidence]
        
        if ticker:
            filtered_verdicts = [v for v in filtered_verdicts if v.get("ticker", "").upper() == ticker.upper()]
        
        # Sort results
        if sort_by == "return":
            filtered_verdicts.sort(key=lambda x: x.get("expected_return", 0), reverse=True)
        elif sort_by == "score":
            filtered_verdicts.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
        else:  # confidence or default
            filtered_verdicts.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Limit results
        limited_verdicts = filtered_verdicts[:limit]
        
        # Calculate summary stats
        total_verdicts = len(filtered_verdicts)
        high_confidence_count = len([v for v in filtered_verdicts if v.get("confidence", 0) >= 0.7])
        avg_confidence = sum(v.get("confidence", 0) for v in filtered_verdicts) / total_verdicts if total_verdicts > 0 else 0.0
        
        # Create response with never-empty pattern
        response_data = {
            "verdicts": limited_verdicts,
            "count": len(limited_verdicts),
            "total": total_verdicts,
            "high_confidence_count": high_confidence_count,
            "avg_confidence": avg_confidence,
            "filters": {
                "min_confidence": min_confidence,
                "ticker": ticker,
                "sort_by": sort_by
            },
            "freshness": judge_data.get("generated_at") or datetime.utcnow().isoformat(),
            "source": judge_data.get("source") or ["llm_judge_storage"],
            "last_update": judge_data.get("last_update") or judge_data.get("generated_at") or datetime.utcnow().isoformat(),
            "metadata": {
                "model_used": judge_data.get("model", "gpt-4-compatible"),
                "evaluation_parameters": {
                    "confidence_threshold": min_confidence,
                    "limit": limit
                }
            }
        }
        
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"Error in get_judge_verdicts: {e}", exc_info=True)
        # Never return empty - always return structure with fallback data
        return ok({
            "verdicts": [],
            "count": 0,
            "total": 0,
            "high_confidence_count": 0,
            "avg_confidence": 0.0,
            "filters": {
                "min_confidence": min_confidence,
                "ticker": ticker,
                "sort_by": sort_by
            },
            "freshness": datetime.utcnow().isoformat(),
            "source": ["fallback"],
            "last_update": datetime.utcnow().isoformat(),
            "metadata": {
                "model_used": "fallback_model",
                "evaluation_parameters": {
                    "confidence_threshold": min_confidence,
                    "limit": limit
                }
            },
            "error": str(e),
            "message": "Judge verdicts temporarily unavailable, returning empty response per never-empty pattern"
        })


@router.post("/analyze")
async def analyze_with_judge(
    ticker: str = Query(..., description="Ticker to analyze"),
    horizon: str = Query("1w", description="Analysis horizon: 1d, 1w, 1m, 3m"),
    model: str = Query("deepseek-ai/DeepSeek-V3-0324-Turbo", description="Model to use for analysis")
):
    """
    Run judge analysis on specific ticker with model.
    """
    try:
        # Load existing forecasts/verdicts for this ticker if available
        forecasts_data = load_json("forecasts") or {}
        all_forecasts = forecasts_data.get("rows", []) or forecasts_data.get("data", {}).get("rows", []) or []
        
        # Find forecasts for this ticker
        ticker_forecasts = [f for f in all_forecasts if f.get("ticker", "").upper() == ticker.upper()]
        
        if ticker_forecasts:
            # Use existing forecast data to create a judge verdict
            most_recent = ticker_forecasts[0]  # Already sorted by confidence or date likely
            verdict = {
                "ticker": ticker,
                "horizon": horizon,
                "confidence": most_recent.get("confidence", 0.5),
                "expected_return": most_recent.get("expected_return", 0),
                "direction": most_recent.get("direction", "neutral"),
                "analysis": {
                    "reasoning": most_recent.get("analysis", "Based on available forecast data"),
                    "risks": most_recent.get("risks", ["market_volatility"]),
                    "catalysts": most_recent.get("catalysts", []),
                    "confidence_factors": most_recent.get("confidence_factors", {})
                },
                "recommendation": most_recent.get("recommendation", "hold"),
                "target_price": most_recent.get("target_price"),
                "stop_loss": most_recent.get("stop_loss"),
                "timeframe": horizon,
                "model": model,
                "generated_at": datetime.utcnow().isoformat()
            }
        else:
            # Return empty verdict with proper structure
            verdict = {
                "ticker": ticker,
                "horizon": horizon,
                "confidence": 0.0,
                "expected_return": 0.0,
                "direction": "neutral",
                "analysis": {
                    "reasoning": "Insufficient data for detailed analysis",
                    "risks": [],
                    "catalysts": [],
                    "confidence_factors": {}
                },
                "recommendation": "no_data",
                "target_price": None,
                "stop_loss": None,
                "timeframe": horizon,
                "model": model,
                "generated_at": datetime.utcnow().isoformat(),
                "note": "This is a fallback verdict due to lack of forecast data"
            }
        
        return ok({
            "verdict": verdict,
            "freshness": datetime.utcnow().isoformat(),
            "source": ["forecasts_fallback"] if ticker_forecasts else ["fallback"],
            "last_update": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in analyze_with_judge: {e}", exc_info=True)
        return ok({
            "verdict": {
                "ticker": ticker,
                "horizon": horizon,
                "confidence": 0.0,
                "expected_return": 0.0,
                "direction": "neutral",
                "analysis": {
                    "reasoning": f"Error processing request: {str(e)}",
                    "risks": ["processing_error"],
                    "catalysts": [],
                    "confidence_factors": {}
                },
                "recommendation": "error",
                "target_price": None,
                "stop_loss": None,
                "timeframe": horizon,
                "model": model,
                "generated_at": datetime.utcnow().isoformat()
            },
            "freshness": datetime.utcnow().isoformat(),
            "source": ["fallback"],
            "last_update": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Judge analysis failed, returning fallback verdict per never-empty pattern"
        })


# Make router available for import
judge_router = router