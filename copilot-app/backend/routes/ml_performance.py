"""
ML Performance Route - Exposes model performance metrics
Task: FC-P2-018
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from fastapi import APIRouter
from typing import Dict, Any

from services.cache_layer import load_or_compute
from storage.io import load_json

router = APIRouter(prefix="/api", tags=["ml-performance"])

@router.get("/ml-performance")
async def get_ml_performance():
    """
    Get ML model performance metrics with real metrics from the tracking system.
    Implements never-empty contract by serving cached/latest report if live calculation fails.
    """
    def compute_performance():
        """Compute fresh performance metrics"""
        try:
            # Try to get fresh data from the performance tracker
            from models.performance_tracker import performance_tracker
            return performance_tracker.get_performance_report()
        except ImportError:
            # Fallback if performance tracker is not available
            return {
                "summary": {
                    "total_predictions": 0,
                    "evaluated_predictions": 0,
                    "evaluation_rate": 0.0,
                    "models_tracked": [],
                    "tickers_covered": [],
                    "horizons_covered": [],
                    "avg_confidence": 0.0
                },
                "overall_metrics": {
                    "classification_metrics": {
                        "accuracy": 0.0,
                        "precision": 0.0,
                        "recall": 0.0,
                        "f1_score": 0.0,
                        "hit_rate": 0.0,
                        "sample_size": 0
                    },
                    "regression_metrics": {
                        "mse": 0.0,
                        "rmse": 0.0,
                        "mae": 0.0,
                        "mape": 0.0,
                        "direction_accuracy": 0.0,
                        "sample_size": 0
                    },
                    "sharpe_ratio": 0.0,
                    "sortino_ratio": 0.0,
                    "total_predictions": 0,
                    "evaluated_predictions": 0,
                    "avg_confidence": 0.0,
                    "calculated_at": "2025-11-05T00:00:00Z"
                },
                "model_performance": {},
                "metrics_history": [],
                "generated_at": "2025-11-05T00:00:00Z",
                "last_update": None,
                "status": "fallback_no_tracker"
            }
    
    # Use cache layer to serve latest available data, compute fresh if none available
    performance_data = load_or_compute(
        key="ml_performance",
        compute_fn=compute_performance,
        source=["ml_performance_route", "live_calculation", "fallback"]
    )
    
    return {
        "ok": True,
        "data": performance_data
    }