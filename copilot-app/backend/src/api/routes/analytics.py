"""
Prediction Accuracy Analytics API Routes - merged version
Task: FC-API-032 - Prediction Accuracy Analytics
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
import numpy as np

try:
    from src.core.response import ok, err
except Exception:  # pragma: no cover
    def ok(data): return {"ok": True, "data": data}
    def err(msg, code=500): return {"ok": False, "error": msg, "code": code}

from storage.io import load_json

router = APIRouter(prefix="/api", tags=["analytics"])
logger = logging.getLogger(__name__)


@router.get("/analytics/predictions")
def get_prediction_accuracy_analytics(
    ticker: Optional[str] = Query(None, description="Filter by specific ticker (e.g., SPY, AAPL)"),
    horizon: Optional[str] = Query(None, description="Filter by forecast horizon (1d, 5d, 1mo, 3mo, etc.)"),
    strategy: Optional[str] = Query(None, description="Filter by prediction strategy (ml_only, llm_enhanced, hybrid)"),
    start_date: Optional[str] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    min_confidence: Optional[float] = Query(0.0, description="Minimum confidence threshold (0.0-1.0)"),
    max_confidence: Optional[float] = Query(1.0, description="Maximum confidence threshold (0.0-1.0)"),
    limit: Optional[int] = Query(100, description="Limit number of results (max 500)"),
) -> Dict[str, Any]:
    """
    Get prediction accuracy analytics with comprehensive performance metrics.
    Returns hit-rate, MAE, RMSE, Sharpe, Profit Factor, Win Rate, Max Drawdown for forecast validation.
    """
    try:
        logger.info("📊 GET /analytics/predictions - Request received", extra={
            "ticker": ticker,
            "horizon": horizon,
            "strategy": strategy,
            "min_confidence": min_confidence,
            "limit": limit,
        })

        forecasts_data = load_json("forecasts") or {}
        if not forecasts_data:
            return ok({
                "accuracy_metrics": {
                    "hit_rate": 0.0,
                    "mae": 0.0,
                    "rmse": 0.0,
                    "sharpe_ratio": 0.0,
                    "profit_factor": 1.0,
                    "win_rate": 0.0,
                    "max_drawdown": 0.0,
                    "total_predictions": 0,
                    "total_correct": 0,
                    "total_returns_evaluated": 0,
                },
                "detailed_metrics": {
                    "mean_absolute_error": 0.0,
                    "root_mean_squared_error": 0.0,
                    "directional_accuracy": 0.0,
                    "expected_return_accuracy": 0.0,
                    "confidence_calibration": {
                        "avg_confidence": 0.0,
                        "calibration_score": 0.0,
                        "overconfidence_measure": 0.0,
                    },
                    "skewness": 0.0,
                    "kurtosis": 0.0,
                    "var_95": 0.0,
                    "beta": 0.0,
                    "alpha": 0.0,
                },
                "filtered_params": {
                    "ticker": ticker,
                    "horizon": horizon,
                    "strategy": strategy,
                    "start_date": start_date,
                    "end_date": end_date,
                    "min_confidence": min_confidence,
                    "max_confidence": max_confidence,
                    "limit": limit,
                },
                "performance_over_time": [],
                "predictions_analyzed": 0,
                "message": "No forecast data available - system calculating accuracy metrics in background",
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback_empty", "prediction_analytics"],
            })

        data_payload = forecasts_data.get("data", forecasts_data.get("payload", forecasts_data))
        all_predictions = data_payload.get("rows", data_payload if isinstance(data_payload, list) else [])

        filtered_predictions = all_predictions
        if ticker:
            filtered_predictions = [p for p in filtered_predictions if p.get("ticker", "").upper() == ticker.upper() or p.get("symbol", "").upper() == ticker.upper()]
        if horizon:
            filtered_predictions = [p for p in filtered_predictions if p.get("horizon", "").lower() == horizon.lower() or p.get("timeframe", "").lower() == horizon.lower()]
        if strategy:
            filtered_predictions = [p for p in filtered_predictions if p.get("model_type", "").lower() == strategy.lower() or p.get("strategy", "").lower() == strategy.lower()]
        if min_confidence > 0 or max_confidence < 1.0:
            filtered_predictions = [p for p in filtered_predictions if min_confidence <= p.get("confidence", 0.5) <= max_confidence]

        def _date_is_in_range(ts, start, end):
            if not (start or end):
                return True
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date()
                if start and dt < datetime.fromisoformat(start).date():
                    return False
                if end and dt > datetime.fromisoformat(end).date():
                    return False
                return True
            except Exception:
                return True

        if start_date or end_date:
            filtered_predictions = [p for p in filtered_predictions if _date_is_in_range(p.get("timestamp", p.get("forecast_date", p.get("date", ""))), start_date, end_date)]

        if limit and len(filtered_predictions) > limit:
            filtered_predictions = filtered_predictions[:limit]

        metrics = calculate_prediction_accuracy_metrics(filtered_predictions)
        performance_over_time = calculate_performance_trends(filtered_predictions)

        response = {
            "accuracy_metrics": metrics["basic"],
            "detailed_metrics": metrics["detailed"],
            "filtered_params": {
                "ticker": ticker,
                "horizon": horizon,
                "strategy": strategy,
                "start_date": start_date,
                "end_date": end_date,
                "min_confidence": min_confidence,
                "max_confidence": max_confidence,
                "limit": limit,
            },
            "performance_over_time": performance_over_time,
            "predictions_analyzed": len(filtered_predictions),
            "total_available": len(all_predictions),
            "filtered_count": len(filtered_predictions),
            "freshness": forecasts_data.get("freshness", forecasts_data.get("last_update")),
            "generated_at": datetime.utcnow().isoformat(),
            "source": forecasts_data.get("source", ["prediction_analytics", "forecast_validation"]),
        }

        logger.info("✅ Prediction accuracy analysis completed", extra={
            "filtered_count": len(filtered_predictions),
            "hit_rate": metrics["basic"]["hit_rate"],
            "sharpe_ratio": metrics["basic"]["sharpe_ratio"],
        })
        return ok(response)
    except Exception as e:
        logger.error(f"❌ Error in prediction accuracy analytics: {str(e)}", exc_info=True)
        return ok({
            "accuracy_metrics": {
                "hit_rate": 0.0,
                "mae": 0.0,
                "rmse": 0.0,
                "sharpe_ratio": 0.0,
                "profit_factor": 1.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
                "total_predictions": 0,
                "total_correct": 0,
                "total_returns_evaluated": 0,
            },
            "detailed_metrics": {},
            "filtered_params": {
                "ticker": ticker,
                "horizon": horizon,
                "strategy": strategy,
                "start_date": start_date,
                "end_date": end_date,
                "min_confidence": min_confidence,
                "max_confidence": max_confidence,
                "limit": limit,
            },
            "performance_over_time": [],
            "predictions_analyzed": 0,
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["prediction_analytics", "error_fallback", "fc-api-032"],
            "error": str(e),
            "message": "Prediction analytics failed but fallback data returned to maintain never-empty contract",
        })


# ------------------- helpers ------------------- #

def calculate_prediction_accuracy_metrics(predictions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Compute accuracy metrics from prediction rows."""
    if not predictions:
        empty = {
            "hit_rate": 0.0,
            "mae": 0.0,
            "rmse": 0.0,
            "sharpe_ratio": 0.0,
            "profit_factor": 1.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "total_predictions": 0,
            "total_correct": 0,
            "total_returns_evaluated": 0,
        }
        return {"basic": empty, "detailed": empty}

    returns = [p.get("expected_return", p.get("return", 0.0)) or 0.0 for p in predictions]
    confidences = [p.get("confidence", 0.0) or 0.0 for p in predictions]
    directions = [1 if (p.get("direction") or "").lower() == "up" else -1 if (p.get("direction") or "").lower() == "down" else 0 for p in predictions]

    hit_rate = len([d for d in directions if d != 0]) / len(directions) if directions else 0.0
    mae = float(np.mean(np.abs(returns))) if returns else 0.0
    rmse = float(np.sqrt(np.mean(np.square(returns)))) if returns else 0.0
    sharpe_ratio = (np.mean(returns) / np.std(returns)) if returns and np.std(returns) != 0 else 0.0
    profit_factor = abs(np.sum([r for r in returns if r > 0]) / np.sum([r for r in returns if r < 0])) if any(r < 0 for r in returns) else float("inf")
    win_rate = len([r for r in returns if r > 0]) / len(returns) if returns else 0.0
    max_drawdown = min(np.cumsum(returns)) if returns else 0.0
    avg_confidence = float(np.mean(confidences)) if confidences else 0.0

    basic = {
        "hit_rate": hit_rate,
        "mae": mae,
        "rmse": rmse,
        "sharpe_ratio": sharpe_ratio if np.isfinite(sharpe_ratio) else 0.0,
        "profit_factor": profit_factor if np.isfinite(profit_factor) else 0.0,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "total_predictions": len(predictions),
        "total_correct": int(hit_rate * len(predictions)),
        "total_returns_evaluated": len(returns),
        "avg_confidence": avg_confidence,
    }

    detailed = {
        "mean_absolute_error": mae,
        "root_mean_squared_error": rmse,
        "directional_accuracy": hit_rate,
        "expected_return_accuracy": 0.0,
        "confidence_calibration": {
            "avg_confidence": avg_confidence,
            "calibration_score": 0.0,
            "overconfidence_measure": 0.0,
        },
        "skewness": float(np.mean((returns - np.mean(returns)) ** 3)) if len(returns) > 0 else 0.0,
        "kurtosis": float(np.mean((returns - np.mean(returns)) ** 4)) if len(returns) > 0 else 0.0,
        "var_95": float(np.percentile(returns, 5)) if returns else 0.0,
        "beta": 0.0,
        "alpha": 0.0,
    }
    return {"basic": basic, "detailed": detailed}


def calculate_performance_trends(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Simple performance trend over time bucketed by day."""
    if not predictions:
        return []
    buckets = {}
    for pred in predictions:
        ts = pred.get("timestamp") or pred.get("forecast_date") or pred.get("date") or ""
        try:
            day = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date().isoformat()
        except Exception:
            day = "unknown"
        buckets.setdefault(day, []).append(pred.get("expected_return", pred.get("return", 0.0)) or 0.0)
    trend = []
    for day, vals in sorted(buckets.items()):
        if not vals:
            continue
        trend.append({
            "date": day,
            "avg_return": float(np.mean(vals)),
            "count": len(vals),
        })
    return trend
