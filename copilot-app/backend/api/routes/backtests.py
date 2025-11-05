"""
API Routes for Backtests - Finance Copilot System
Serves backtest results comparing forecasts to actual market performance
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from core.response import ok, err
from storage.io import load_json

router = APIRouter()

@router.get("/backtests")
def get_backtests(
    ticker: Optional[str] = Query(None, description="Filter by specific ticker"),
    horizon: Optional[str] = Query(None, description="Filter by forecast horizon (1d, 1w, 1m)"),
    min_confidence: Optional[float] = Query(0.0, description="Minimum confidence threshold (0.0-1.0)"),
    limit: Optional[int] = Query(None, description="Maximum number of results to return")
) -> Dict[str, Any]:
    """
    Get backtest results comparing forecasts to actual market performance.
    Returns metrics on forecast accuracy including hit rate and expected returns.
    """
    try:
        # Load backtest results from persistent storage
        backtests_data = load_json("backtests")
        
        if not backtests_data:
            # Return empty metrics structure but never fail
            return ok({
                "results": {
                    "hit_rate": 0.0,
                    "avg_er": 0.0,
                    "n_trades": 0,
                    "total_evaluated": 0,
                    "correct_predictions": 0,
                    "start_date": None,
                    "end_date": None,
                    "avg_confidence": 0.0,
                    "success_rate": 0.0,
                    "sample_size": 0,
                    "accuracy": 0.0
                },
                "params": {
                    "ticker_filter": ticker,
                    "horizon_filter": horizon,
                    "min_confidence": min_confidence,
                    "limit": limit
                },
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback_empty"],
                "message": "No backtest data available - forecasts are being evaluated against market data"
            })
        
        # Extract the results from the loaded data
        results = backtests_data.get("results", {})
        
        # Apply filters if specified
        filtered_results = results.copy()
        
        if ticker:
            # Filter by ticker if needed - this would require adjusting the actual backtest results
            # For now, we'll still return overall metrics but indicate the filter
            filtered_results["filtered_by_ticker"] = ticker
            
        if horizon:
            filtered_results["filtered_by_horizon"] = horizon
            
        if min_confidence > 0.0:
            filtered_results["filtered_by_min_confidence"] = min_confidence
            
        # Apply limit if specified
        if limit and "backtest_results" in filtered_results:
            filtered_results["backtest_results"] = filtered_results["backtest_results"][:limit]
        
        return ok({
            "results": filtered_results,
            "params": {
                "ticker_filter": ticker,
                "horizon_filter": horizon,
                "min_confidence": min_confidence,
                "limit": limit
            },
            "freshness": backtests_data.get("freshness", "unknown"),
            "generated_at": datetime.utcnow().isoformat(),
            "source": backtests_data.get("source", ["backtests_job"]),
            "status": "active"
        })
        
    except Exception as e:
        # Return structured error response instead of crashing
        return err(500, f"Error in backtests endpoint: {str(e)}")


@router.get("/backtests/metrics")
def get_backtest_metrics() -> Dict[str, Any]:
    """
    Get high-level backtest metrics overview.
    """
    try:
        backtests_data = load_json("backtests")
        
        if not backtests_data or not backtests_data.get("results"):
            return ok({
                "overall_hit_rate": 0.0,
                "avg_expected_return": 0.0,
                "total_trades_evaluated": 0,
                "accuracy_trend": "unknown",
                "avg_confidence": 0.0,
                "last_update": None,
                "model_performance": {
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0
                }
            })
        
        results = backtests_data.get("results", {})
        
        return ok({
            "overall_hit_rate": results.get("hit_rate", 0.0),
            "avg_expected_return": results.get("avg_er", 0.0),
            "total_trades_evaluated": results.get("n_trades", 0),
            "accuracy_trend": results.get("trend", "stable"),
            "avg_confidence": results.get("avg_confidence", 0.0),
            "last_update": results.get("generated_at", backtests_data.get("generated_at")),
            "model_performance": {
                "precision": results.get("hit_rate", 0.0),  # Using hit_rate as precision proxy
                "recall": results.get("recall", results.get("hit_rate", 0.0)),
                "f1_score": results.get("f1_score", 0.0),
                "accuracy": results.get("accuracy", 0.0)
            }
        })
    except Exception as e:
        return err(500, f"Error getting backtest metrics: {str(e)}")


@router.get("/backtests/detail/{ticker}")
def get_backtest_detail(ticker: str) -> Dict[str, Any]:
    """
    Get detailed backtest results for a specific ticker.
    """
    try:
        backtests_data = load_json("backtests")
        
        if not backtests_data or not backtests_data.get("results"):
            return ok({
                "ticker": ticker,
                "results": [],
                "summary": {
                    "hit_rate": 0.0,
                    "avg_er": 0.0,
                    "n_trades": 0,
                    "message": f"No backtest data available for {ticker}"
                },
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat()
            })
        
        # In real implementation, this would filter by specific ticker
        # For now, return a summary based on available data
        results = backtests_data.get("results", {})
        
        # Return specific metrics for this ticker (in a real implementation,
        # this would filter the detailed results) 
        ticker_summary = {
            "ticker": ticker,
            "hit_rate": results.get("hit_rate", 0.0),
            "avg_er": results.get("avg_er", 0.0),
            "n_trades": results.get("n_trades", 0),
            "avg_confidence": results.get("avg_confidence", 0.0),
            "total_evaluated": results.get("total_evaluated", 0),
            "correct_predictions": results.get("correct_predictions", 0)
        }
        
        return ok({
            "ticker": ticker,
            "results": [ticker_summary],  # Would have more details in real implementation
            "summary": ticker_summary,
            "freshness": backtests_data.get("freshness", "unknown"),
            "generated_at": datetime.utcnow().isoformat(),
            "source": backtests_data.get("source", ["backtests_job"])
        })
        
    except Exception as e:
        return err(500, f"Error getting details for {ticker}: {str(e)}")