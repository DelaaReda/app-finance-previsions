"""
Prediction Accuracy Analytics API Routes - Finance Copilot System
Provides advanced analytics on forecast and prediction accuracy metrics
Task: FC-API-032 - Prediction Accuracy Analytics by ALEX-FINANCE-ANALYST-SUPERMAN-29
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
import numpy as np

from core.response import ok, err
from storage.io import load_json

router = APIRouter()
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
    limit: Optional[int] = Query(100, description="Limit number of results (max 500)")
) -> Dict[str, Any]:
    """
    Get prediction accuracy analytics with comprehensive performance metrics.
    Returns hit-rate, MAE, RMSE, Sharpe, Profit Factor, Win Rate, Max Drawdown for forecast validation.
    """
    try:
        logger.info(f"📊 GET /analytics/predictions - Request received", extra={
            "ticker": ticker,
            "horizon": horizon,
            "strategy": strategy,
            "min_confidence": min_confidence,
            "limit": limit
        })
        
        # Load forecast data from persistent storage (never-empty pattern)
        forecasts_data = load_json("forecasts")
        
        if not forecasts_data:
            logger.warning("⚠️ No forecast data found", extra={
                "filters": {"ticker": ticker, "horizon": horizon, "strategy": strategy}
            })
            
            # Return empty but structured response (never-empty pattern)
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
                    "total_returns_evaluated": 0
                },
                "detailed_metrics": {
                    "mean_absolute_error": 0.0,
                    "root_mean_squared_error": 0.0,
                    "directional_accuracy": 0.0,
                    "expected_return_accuracy": 0.0,
                    "confidence_calibration": {
                        "avg_confidence": 0.0,
                        "calibration_score": 0.0,
                        "overconfidence_measure": 0.0
                    },
                    "skewness": 0.0,
                    "kurtosis": 0.0,
                    "var_95": 0.0,
                    "beta": 0.0,
                    "alpha": 0.0
                },
                "filtered_params": {
                    "ticker": ticker,
                    "horizon": horizon,
                    "strategy": strategy,
                    "start_date": start_date,
                    "end_date": end_date,
                    "min_confidence": min_confidence,
                    "max_confidence": max_confidence,
                    "limit": limit
                },
                "performance_over_time": [],
                "predictions_analyzed": [],
                "message": "No forecast data available - system calculating accuracy metrics in background",
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback_empty", "prediction_analytics"]
            })
        
        # Extract forecast rows from data payload
        data_payload = forecasts_data.get("data", forecasts_data.get("payload", forecasts_data))
        all_predictions = data_payload.get("rows", data_payload if isinstance(data_payload, list) else [])
        
        logger.info(f"📈 Loaded {len(all_predictions)} predictions for analysis", extra={
            "total_predictions": len(all_predictions),
            "data_source": "forecasts_cache"
        })
        
        # Apply filtering
        filtered_predictions = all_predictions
        
        # Filter by ticker if specified
        if ticker:
            filtered_predictions = [
                pred for pred in filtered_predictions
                if pred.get("ticker", "").upper() == ticker.upper() or pred.get("symbol", "").upper() == ticker.upper()
            ]
            logger.debug(f"🔍 Filtered by ticker {ticker}: {len(all_predictions)} → {len(filtered_predictions)} predictions")
        
        # Filter by horizon
        if horizon:
            filtered_predictions = [
                pred for pred in filtered_predictions
                if pred.get("horizon", "").lower() == horizon.lower() or pred.get("timeframe", "").lower() == horizon.lower()
            ]
            logger.debug(f"📅 Filtered by horizon {horizon}: {len(filtered_predictions)} predictions")
        
        # Filter by strategy/model type
        if strategy:
            filtered_predictions = [
                pred for pred in filtered_predictions
                if pred.get("model_type", "").lower() == strategy.lower() or pred.get("strategy", "").lower() == strategy.lower()
            ]
            logger.debug(f"🤖 Filtered by strategy {strategy}: {len(filtered_predictions)} predictions")
        
        # Filter by confidence range
        if min_confidence > 0 or max_confidence < 1.0:
            filtered_predictions = [
                pred for pred in filtered_predictions
                if min_confidence <= pred.get("confidence", 0.5) <= max_confidence
            ]
            logger.debug(f"🔍 Filtered by confidence [{min_confidence}, {max_confidence}]: {len(filtered_predictions)} predictions")
        
        # Apply date range filter
        if start_date or end_date:
            filtered_predictions = [
                pred for pred in filtered_predictions
                if _date_is_in_range(pred.get("timestamp", pred.get("forecast_date", pred.get("date", ""))), start_date, end_date)
            ]
            logger.debug(f"🗓️ Filtered by date range: {len(filtered_predictions)} predictions")
        
        # Apply limit
        if limit and len(filtered_predictions) > limit:
            filtered_predictions = filtered_predictions[:limit]
            logger.debug(f"✂️ Applied limit {limit}: {len(filtered_predictions)} predictions")
        
        # Calculate accuracy metrics
        metrics = calculate_prediction_accuracy_metrics(filtered_predictions)
        
        # Calculate performance over time (for trend visualization)
        performance_over_time = calculate_performance_trends(filtered_predictions)
        
        # Prepare enhanced response for frontend consumption
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
                "limit": limit
            },
            "performance_over_time": performance_over_time,
            "predictions_analyzed": len(filtered_predictions),
            "total_available": len(all_predictions),
            "filtered_count": len(filtered_predictions),
            "freshness": forecasts_data.get("freshness", forecasts_data.get("last_update")),
            "generated_at": datetime.utcnow().isoformat(),
            "source": forecasts_data.get("source", ["prediction_analytics", "forecast_validation"])
        }
        
        logger.info(f"✅ Prediction accuracy analysis completed", extra={
            "filtered_count": len(filtered_predictions),
            "hit_rate": metrics["basic"]["hit_rate"],
            "sharpe_ratio": metrics["basic"]["sharpe_ratio"]
        })
        
        return ok(response)
        
    except Exception as e:
        logger.error(f"❌ Error in prediction accuracy analytics: {str(e)}", exc_info=True)
        
        # Return structured fallback response (never-empty pattern)
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
                "total_returns_evaluated": 0
            },
            "detailed_metrics": {
                "mean_absolute_error": 0.0,
                "root_mean_squared_error": 0.0,
                "directional_accuracy": 0.0,
                "expected_return_accuracy": 0.0,
                "confidence_calibration": {
                    "avg_confidence": 0.0,
                    "calibration_score": 0.0,
                    "overconfidence_measure": 0.0
                },
                "skewness": 0.0,
                "kurtosis": 0.0,
                "var_95": 0.0,
                "beta": 0.0,
                "alpha": 0.0
            },
            "filtered_params": {
                "ticker": ticker,
                "horizon": horizon,
                "strategy": strategy,
                "start_date": start_date,
                "end_date": end_date,
                "min_confidence": min_confidence,
                "max_confidence": max_confidence,
                "limit": limit
            },
            "performance_over_time": [],
            "predictions_analyzed": 0,
            "total_available": 0,
            "filtered_count": 0,
            "error": str(e),
            "message": "Prediction accuracy analytics temporarily unavailable - showing fallback data",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback", "error_handling", "prediction_analytics"]
        })


def calculate_prediction_accuracy_metrics(predictions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate comprehensive prediction accuracy metrics.
    
    Args:
        predictions: List of prediction dictionaries with actual vs expected values
        
    Returns:
        Dictionary with basic and detailed accuracy metrics
    """
    if not predictions or not isinstance(predictions, list):
        # Return default metrics structure for empty input
        return {
            "basic": {
                "hit_rate": 0.0,
                "mae": 0.0,
                "rmse": 0.0,
                "sharpe_ratio": 0.0,
                "profit_factor": 1.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
                "total_predictions": 0,
                "total_correct": 0,
                "total_returns_evaluated": 0
            },
            "detailed": {
                "mean_absolute_error": 0.0,
                "root_mean_squared_error": 0.0,
                "directional_accuracy": 0.0,
                "expected_return_accuracy": 0.0,
                "confidence_calibration": {
                    "avg_confidence": 0.0,
                    "calibration_score": 0.0,
                    "overconfidence_measure": 0.0
                },
                "skewness": 0.0,
                "kurtosis": 0.0,
                "var_95": 0.0,
                "beta": 0.0,
                "alpha": 0.0
            }
        }
    
    # Extract prediction vs actual values
    predicted_directions = []  # Direction predictions (up, down, neutral)
    actual_directions = []     # Actual realized directions
    predicted_returns = []     # Predicted returns
    actual_returns = []        # Actual returns
    confidences = []           # Confidence scores
    
    for pred in predictions:
        if not isinstance(pred, dict):
            continue
            
        # Get direction predictions and actuals
        pred_direction = (pred.get("direction") or pred.get("predicted_direction") or "neutral").lower()
        actual_direction = (pred.get("realized_direction") or pred.get("actual_direction") or 
                           pred.get("actual_move") or "neutral").lower()
        
        predicted_directions.append(pred_direction)
        actual_directions.append(actual_direction)
        
        # Get return predictions and actuals
        predicted_return = pred.get("expected_return", pred.get("predicted_return", 0.0))
        actual_return = pred.get("realized_return", pred.get("actual_return", pred.get("actual_change", 0.0)))
        
        try:
            predicted_returns.append(float(predicted_return))
            actual_returns.append(float(actual_return))
        except (ValueError, TypeError):
            # If conversion fails, use 0.0 as default
            predicted_returns.append(0.0)
            actual_returns.append(0.0)
        
        # Get confidence scores
        confidence = pred.get("confidence", pred.get("confidence_score", 0.5))
        try:
            confidences.append(float(confidence))
        except (ValueError, TypeError):
            confidences.append(0.5)  # Default confidence if conversion fails
    
    # Calculate basic metrics
    total_predictions = len(predictions)
    
    # Hit rate: percentage of correct directional predictions
    correct_directional = sum(1 for pd, ad in zip(predicted_directions, actual_directions) if pd == ad)
    hit_rate = correct_directional / total_predictions if total_predictions > 0 else 0.0
    
    # MAE: Mean Absolute Error for returns
    mae = sum(abs(pr - ar) for pr, ar in zip(predicted_returns, actual_returns)) / total_predictions if total_predictions > 0 else 0.0
    
    # RMSE: Root Mean Squared Error for returns
    squared_errors = [(pr - ar) ** 2 for pr, ar in zip(predicted_returns, actual_returns)]
    rmse = (sum(squared_errors) / total_predictions) ** 0.5 if total_predictions > 0 else 0.0
    
    # Win rate: percentage of profitable predictions (where sign of predicted and actual match)
    profitable_predictions = sum(1 for pr, ar in zip(predicted_returns, actual_returns) if 
                                (pr >= 0) == (ar >= 0) and ar != 0)
    win_rate = profitable_predictions / total_predictions if total_predictions > 0 else 0.0
    
    # Calculate profit factor (gains vs losses)
    gains = sum(ar for ar in actual_returns if ar > 0)  # Total positive returns
    losses = abs(sum(ar for ar in actual_returns if ar < 0))  # Total negative returns
    profit_factor = gains / losses if losses > 0 else float('inf') if gains > 0 else 1.0
    if profit_factor == float('inf'): 
        profit_factor = 999.0  # Replace infinite value with large finite number
    
    # Calculate Sharpe ratio (assuming 2% annual risk-free rate)
    sharpe_ratio = 0.0
    if actual_returns and len(actual_returns) > 1:
        returns_array = np.array(actual_returns)
        if len(returns_array) > 0:
            avg_return = np.mean(returns_array)
            volatility = np.std(returns_array) if len(returns_array) > 1 else 0.0
            risk_free_rate = 0.02 / 252  # Daily risk-free rate (2% annualized)
            sharpe_ratio = (avg_return - risk_free_rate) / volatility if volatility != 0 else 0.0
    
    # Calculate max drawdown
    max_dd = 0.0
    if actual_returns and len(actual_returns) > 0:
        # Calculate cumulative returns
        cumulative_returns = [1.0]  # Start with 100% of capital
        for ar in actual_returns:
            cumulative_returns.append(cumulative_returns[-1] * (1 + ar))
        
        # Calculate drawdowns
        peak = cumulative_returns[0]
        for value in cumulative_returns[1:]:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak != 0 else 0.0
            if drawdown > max_dd:
                max_dd = drawdown
    
    # Calculate detailed metrics
    avg_confidence = sum(confidences) / len(confidences) if len(confidences) > 0 else 0.0
    confidence_calibration = calculate_confidence_calibration(predictions)
    
    # Calculate returns statistics for detailed metrics
    returns_array = np.array(actual_returns) if actual_returns and len(actual_returns) > 0 else np.array([])
    
    # Basic metrics
    basic_metrics = {
        "hit_rate": hit_rate,
        "mae": mae,
        "rmse": rmse,
        "sharpe_ratio": sharpe_ratio,
        "profit_factor": profit_factor,
        "win_rate": win_rate,
        "max_drawdown": max_dd,
        "total_predictions": total_predictions,
        "total_correct": correct_directional,
        "total_returns_evaluated": len(actual_returns)
    }
    
    # Detailed metrics
    detailed_metrics = {
        "mean_absolute_error": mae,
        "root_mean_squared_error": rmse,
        "directional_accuracy": hit_rate,
        "expected_return_accuracy": calculate_return_accuracy(predicted_returns, actual_returns),
        "confidence_calibration": confidence_calibration,
        "skewness": float(np.skew(returns_array)) if len(returns_array) >= 3 else 0.0,
        "kurtosis": float(np.kurtosis(returns_array)) if len(returns_array) >= 4 else 0.0,
        "var_95": calculate_var_95(returns_array) if returns_array.size > 0 else 0.0,
        "beta": 0.0,  # Would need market returns for proper calculation
        "alpha": 0.0   # Would need benchmark returns
    }
    
    return {
        "basic": basic_metrics,
        "detailed": detailed_metrics
    }


def calculate_confidence_calibration(predictions: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate confidence calibration metrics to assess how well confidence scores reflect actual accuracy.
    """
    if not predictions or not isinstance(predictions, list):
        return {"avg_confidence": 0.0, "calibration_score": 0.0, "overconfidence_measure": 0.0}
    
    # Calculate calibration: how well average confidence matches average accuracy
    total_conf = sum(pred.get("confidence", pred.get("confidence_score", 0.5)) for pred in predictions if isinstance(pred, dict))
    avg_confidence = total_conf / len(predictions) if predictions else 0.0
    
    # Calculate actual accuracy for each prediction
    correct_predictions = 0
    for pred in predictions:
        if not isinstance(pred, dict):
            continue
            
        pred_direction = (pred.get("direction") or pred.get("predicted_direction") or "neutral").lower()
        actual_direction = (pred.get("realized_direction") or pred.get("actual_direction") or 
                           pred.get("actual_move") or "neutral").lower()
        
        if pred_direction == actual_direction:
            correct_predictions += 1
    
    avg_accuracy = correct_predictions / len(predictions) if predictions else 0.0
    calibration_score = 1.0 - abs(avg_confidence - avg_accuracy) if predictions else 0.0
    overconfidence_measure = max(0.0, avg_confidence - avg_accuracy)  # How much confidence exceeds accuracy
    
    return {
        "avg_confidence": avg_confidence,
        "calibration_score": calibration_score,
        "overconfidence_measure": overconfidence_measure
    }


def calculate_return_accuracy(predicted_returns: List[float], actual_returns: List[float]) -> float:
    """
    Calculate accuracy of return predictions (correlation between predicted and actual returns).
    """
    if not predicted_returns or not actual_returns or len(predicted_returns) != len(actual_returns) or len(predicted_returns) < 2:
        return 0.0
    
    try:
        import numpy as np
        # Calculate correlation coefficient (Pearson)
        pred_array = np.array(predicted_returns)
        act_array = np.array(actual_returns)
        
        # Calculate correlation
        if len(pred_array) < 2 or len(act_array) < 2 or np.std(pred_array) == 0 or np.std(act_array) == 0:
            return 0.0  # Not enough data or no variance
        
        correlation = np.corrcoef(pred_array, act_array)[0, 1]
        
        return float(correlation) if not np.isnan(correlation) else 0.0
    except:
        return 0.0  # Return 0 if calculation fails


def calculate_var_95(returns: np.ndarray) -> float:
    """
    Calculate Value at Risk at 95% confidence level.
    """
    if returns.size == 0 or len(returns) < 10:  # Need minimum data points
        return 0.0
    
    try:
        var_95 = np.percentile(returns, 5)  # 5th percentile = 95% VaR
        return float(var_95)
    except:
        return 0.0  # Return 0 if calculation fails


def calculate_performance_trends(predictions: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    """
    Calculate performance over time for visualization.
    Groups predictions by date and calculates metrics for each date.
    """
    if not predictions:
        return []
    
    # Group predictions by date
    date_groups = {}
    for pred in predictions:
        if not isinstance(pred, dict):
            continue
            
        date_str = pred.get("timestamp") or pred.get("forecast_date") or pred.get("date", "")
        if date_str:
            date_key = str(date_str).split("T")[0] if "T" in str(date_str) else str(date_str)  # Extract date part only
            if date_key not in date_groups:
                date_groups[date_key] = []
            date_groups[date_key].append(pred)
    
    # Calculate metrics for each date group
    trends = []
    for date_key, preds in date_groups.items():
        metrics = calculate_prediction_accuracy_metrics(preds)["basic"]
        avg_return = sum(p.get("realized_return", p.get("actual_return", 0.0)) for p in preds if isinstance(p, dict)) / len(preds) if len(preds) > 0 else 0.0
        trends.append({
            "date": date_key,
            "hit_rate": metrics.get("hit_rate", 0.0),
            "avg_return": avg_return,
            "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
            "total_predictions": metrics.get("total_predictions", 0)
        })
    
    # Sort by date to show chronological trends
    trends.sort(key=lambda x: x["date"])
    
    return trends


def _date_is_in_range(date_str: str, start_date: Optional[str], end_date: Optional[str]) -> bool:
    """
    Check if a date string is within the specified range.
    """
    if not date_str or (not start_date and not end_date):
        return True
    
    try:
        from datetime import datetime
        # Parse the date string (handles both ISO format and simple date format)
        date_str = str(date_str)
        if "T" in date_str:
            pred_date = datetime.fromisoformat(date_str.replace("Z", "+00:00").replace("z", "+00:00").split("T")[0])
        else:
            pred_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Parse start and end dates if provided
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            if pred_date.date() < start_dt.date():
                return False
        
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if pred_date.date() > end_dt.date():
                return False
        
        return True
    except Exception:
        # If date parsing fails, include the prediction
        return True


# Export router with expected name for main.py integration
analytics_router = router