"""
Analytics routes for prediction accuracy and other metrics
Task: FC-API-032 - Prediction Accuracy Analytics
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from core.response import ok, err
from storage.io import load_json
from services.prediction_analyzer import prediction_analyzer

router = APIRouter()

@router.get("/analytics/predictions")
def get_prediction_accuracy(
    ticker: Optional[str] = Query(None, description="Filter by specific ticker"),
    horizon: Optional[str] = Query(None, description="Filter by forecast horizon"),
    period: Optional[str] = Query("30d", description="Analysis period (7d, 30d, 90d)")
) -> Dict[str, Any]:
    """
    Get prediction accuracy metrics comparing forecasts to actual market performance.
    Returns hit rate, MAE, RMSE, and other performance metrics.
    """
    try:
        # Generate accuracy report
        params = {
            "ticker": ticker,
            "horizon": horizon,
            "period": period
        }
        
        accuracy_report = prediction_analyzer.generate_accuracy_report(params)
        
        return ok({
            "report": accuracy_report,
            "params": params,
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["prediction_analyzer", "accuracy_comparison"],
            "version": "v1.0"
        })
        
    except Exception as e:
        # Return structured response instead of crashing
        return ok({
            "report": {
                "metrics": {
                    "hit_rate": 0.0,
                    "mae": 0.0,
                    "rmse": 0.0,
                    "total_predictions": 0,
                    "total_correct": 0
                },
                "summary": {
                    "hit_rate_grade": "F",
                    "confidence_level": 0.0,
                    "performance_vs_benchmark": False,
                    "signal_reliability": 0.0
                },
                "generated_at": datetime.now().isoformat(),
                "source": ["prediction_analyzer", "fallback_empty"]
            },
            "params": {"ticker": ticker, "horizon": horizon, "period": period},
            "error": str(e),
            "message": "Accuracy metrics temporarily unavailable",
            "generated_at": datetime.utcnow().isoformat()
        })

@router.get("/analytics/predictions/metrics")
def get_prediction_metrics_summary() -> Dict[str, Any]:
    """
    Get a summary of prediction metrics across all tickers and horizons
    """
    try:
        # Calculate metrics for all forecasts in the system
        all_metrics = prediction_analyzer.calculate_forecast_accuracy()
        
        return ok({
            "summary": {
                "overall_hit_rate": all_metrics.get("hit_rate", 0.0),
                "avg_mae": all_metrics.get("mae", 0.0),
                "avg_rmse": all_metrics.get("rmse", 0.0),
                "total_predictions_evaluated": all_metrics.get("total_predictions", 0),
                "total_correct_predictions": all_metrics.get("total_correct", 0),
                "avg_accuracy_grade": all_metrics.get("summary", {}).get("hit_rate_grade", "F"),
                "avg_confidence": all_metrics.get("summary", {}).get("confidence_level", 0.0)
            },
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["prediction_analyzer", "metrics_summary"]
        })
    except Exception as e:
        return ok({
            "summary": {
                "overall_hit_rate": 0.0,
                "avg_mae": 0.0,
                "avg_rmse": 0.0,
                "total_predictions_evaluated": 0,
                "total_correct_predictions": 0,
                "avg_accuracy_grade": "F",
                "avg_confidence": 0.0
            },
            "error": str(e),
            "message": "Prediction metrics summary temporarily unavailable",
            "generated_at": datetime.utcnow().isoformat()
        })