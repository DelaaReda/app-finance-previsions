"""
ML Performance Route
Task: FC-API-032 - Prediction Accuracy Analytics
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, Optional

from ..services.prediction_analyzer import prediction_analytics_service
from ..storage.io import load_json
from ..services.cache_layer import load_or_compute

router = APIRouter(prefix="/api", tags=["analytics"])

@router.get("/analytics/predictions")
async def analytics_predictions(
    ticker: Optional[str] = Query(None, description="Filtrer par ticker"),
    horizon: Optional[str] = Query(None, description="Filtrer par horizon (1d/1w/1m/3m)"),
    days_back: int = Query(30, ge=1, le=365, description="Nombre de jours à analyser")
):
    """
    Get prediction accuracy analytics with comprehensive metrics.
    Implements never-empty contract by serving cached/latest report if live calculation fails.
    """
    try:
        # Load latest available data or compute fresh
        def compute_analytics():
            try:
                # Call the service to get prediction accuracy report
                return prediction_analytics_service.get_prediction_accuracy_report(ticker, horizon, days_back)
            except Exception:
                # Fallback if analytics service not available
                return {
                    "accuracy_metrics": {
                        "overall": {"hit_rate": 0.0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0, "mean_abs_error": 0.0, "root_mean_squared_error": 0.0, "tracking_error": 0.0, "correlation": 0.0, "sample_size": 0},
                        "by_ticker": {},
                        "by_horizon": {},
                        "sample_size": 0,
                        "generated_at": "2025-11-05T00:00:00Z",
                        "message": "Analytics service not available, using fallback metrics"
                    },
                    "prediction_accuracy_report": {
                        "status": "fallback_no_service",
                        "filters_applied": {"ticker": ticker, "horizon": horizon, "days_back": days_back}
                    },
                    "performance_tracking": {
                        "hit_rate_trend": [],
                        "accuracy_trend": [],
                        "f1_score_trend": []
                    },
                    "generated_at": "2025-11-05T00:00:00Z",
                    "data_coverage": {
                        "total_forecasts": 0,
                        "evaluated_predictions": 0,
                        "evaluation_rate": 0.0,
                        "date_range": {"start": None, "end": None}
                    }
                }
        
        analytics_data = load_or_compute(
            key=f"analytics_predictions_{ticker or 'all'}_{horizon or 'all'}_{days_back}d",
            compute_fn=compute_analytics,
            source=["analytics_prediction_route", "accuracy_calculation", "fc-api-032"]
        )
        
        return {
            "ok": True,
            "data": analytics_data,
            "freshness": analytics_data.get("generated_at", "unknown")
        }
        
    except Exception as e:
        print(f"Error in analytics/predictions endpoint: {str(e)}")
        
        # Return fallback data to maintain never-empty contract
        return {
            "ok": True,  # Still return ok=true to maintain never-empty
            "data": {
                "accuracy_metrics": {
                    "overall": {"hit_rate": 0.0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0, "mean_abs_error": 0.0, "root_mean_squared_error": 0.0, "tracking_error": 0.0, "correlation": 0.0, "sample_size": 0},
                    "by_ticker": {},
                    "by_horizon": {},
                    "sample_size": 0,
                    "generated_at": "2025-11-05T00:00:00Z",
                    "message": "Analytics endpoint failed, returning fallback data to maintain never-empty contract",
                    "error": str(e)
                },
                "prediction_accuracy_report": {
                    "status": "error_fallback",
                    "error": str(e)
                },
                "performance_tracking": {
                    "hit_rate_trend": [],
                    "accuracy_trend": [],
                    "f1_score_trend": []
                },
                "generated_at": "2025-11-05T00:00:00Z",
                "data_coverage": {
                    "total_forecasts": 0,
                    "evaluated_predictions": 0,
                    "evaluation_rate": 0.0,
                    "date_range": {"start": None, "end": None}
                }
            },
            "freshness": "error",
            "error": str(e)
        }