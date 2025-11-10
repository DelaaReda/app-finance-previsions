"""
API Routes for LLM Judge - Dashboard Integration
Provides LLM judge verdicts and analysis for the dashboard
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from core.response import ok
from storage.io import load_json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/judge")
def get_judge_verdicts(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of verdicts to return"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")
) -> Dict[str, Any]:
    """
    Get LLM judge verdicts for tickers.
    Returns verdicts with buy/sell/neutral recommendations based on forecasts analysis.
    """
    try:
        # Load judge data (généré par validate_and_generate_data.py)
        judge_data = load_json("llm_judge") or {}
        
        rows = judge_data.get("rows", [])
        
        # If no judge data, try to generate from forecasts
        if not rows:
            logger.info("No judge data found, generating from forecasts...")
            forecasts_data = load_json("forecasts") or {}
            forecast_rows = forecasts_data.get("rows", []) or forecasts_data.get("data", {}).get("rows", [])
            
            # Generate verdicts from forecasts
            rows = []
            for forecast in forecast_rows[:limit * 2]:
                confidence = forecast.get("confidence", 0)
                expected_return = forecast.get("expected_return", 0)
                direction = forecast.get("direction", "neutral")
                
                # Determine verdict based on direction and confidence
                if direction.lower() in ["up", "bullish", "buy"]:
                    verdict = "buy"
                elif direction.lower() in ["down", "bearish", "sell"]:
                    verdict = "sell"
                else:
                    verdict = "neutral"
                
                rows.append({
                    "ticker": forecast.get("ticker") or forecast.get("symbol"),
                    "verdict": verdict,
                    "confidence": confidence,
                    "expected_return": expected_return,
                    "horizon": forecast.get("horizon", "1d"),
                    "reasoning": f"ML model predicts {direction} with {confidence:.0%} confidence",
                    "risk_level": "low" if confidence > 0.7 else "medium" if confidence > 0.5 else "high"
                })
        
        # Filter by confidence
        if min_confidence > 0:
            rows = [r for r in rows if r.get("confidence", 0) >= min_confidence]
        
        # Sort by confidence * expected_return
        rows.sort(
            key=lambda x: x.get("confidence", 0) * abs(x.get("expected_return", 0)),
            reverse=True
        )
        
        # Calculate stats
        total = len(rows)
        buys = sum(1 for r in rows if r.get("verdict") == "buy")
        sells = sum(1 for r in rows if r.get("verdict") == "sell")
        neutrals = sum(1 for r in rows if r.get("verdict") == "neutral")
        avg_confidence = sum(r.get("confidence", 0) for r in rows) / total if total > 0 else 0
        
        return ok({
            "verdicts": rows[:limit],
            "count": len(rows[:limit]),
            "stats": {
                "total": total,
                "buys": buys,
                "sells": sells,
                "neutrals": neutrals,
                "avg_confidence": round(avg_confidence, 4)
            },
            "generated_at": judge_data.get("generated_at", datetime.utcnow().isoformat())
        })
    except Exception as e:
        logger.error(f"Error in get_judge_verdicts: {e}", exc_info=True)
        return ok({
            "verdicts": [],
            "count": 0,
            "stats": {
                "total": 0,
                "buys": 0,
                "sells": 0,
                "neutrals": 0,
                "avg_confidence": 0
            },
            "error": str(e),
            "generated_at": datetime.utcnow().isoformat()
        })


judge_router = router

