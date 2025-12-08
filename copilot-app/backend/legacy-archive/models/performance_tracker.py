"""
ML Model Performance Tracker
Task: FC-P2-018 - ML Model Performance Tracking
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np

class ModelPerformanceTracker:
    """
    Track and evaluate ML model performance with real metrics
    """
    
    def __init__(self):
        self.tracking_data = {
            "models": {},
            "predictions": [],
            "metrics_history": []
        }
    
    def calculate_binary_classification_metrics(self, y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
        """
        Calculate performance metrics for binary classification (direction up/down)
        """
        if len(y_true) == 0 or len(y_pred) == 0:
            return {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "hit_rate": 0.0,
                "sample_size": 0
            }
        
        # Convert to binary (1 for positive, 0 for negative)
        true_binary = [1 if x > 0 else 0 for x in y_true]
        pred_binary = [1 if x > 0 else 0 for x in y_pred]
        
        # Calculate metrics manually
        tp = sum(1 for t, p in zip(true_binary, pred_binary) if t == 1 and p == 1)
        tn = sum(1 for t, p in zip(true_binary, pred_binary) if t == 0 and p == 0)
        fp = sum(1 for t, p in zip(true_binary, pred_binary) if t == 0 and p == 1)
        fn = sum(1 for t, p in zip(true_binary, pred_binary) if t == 1 and p == 0)
        
        total = len(true_binary)
        accuracy = (tp + tn) / total if total > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Hit rate (how often prediction direction matches actual direction)
        hits = sum(1 for t, p in zip(true_binary, pred_binary) if t == p)
        hit_rate = hits / total if total > 0 else 0.0
        
        return {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "hit_rate": float(hit_rate),
            "sample_size": len(y_true)
        }
    
    def calculate_regression_metrics(self, y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
        """
        Calculate performance metrics for regression (return prediction)
        """
        if len(y_true) == 0 or len(y_pred) == 0:
            return {
                "mse": 0.0,
                "rmse": 0.0,
                "mae": 0.0,
                "mape": 0.0,
                "direction_accuracy": 0.0,
                "sample_size": 0
            }
        
        # Calculate MSE
        squared_errors = [(t - p) ** 2 for t, p in zip(y_true, y_pred)]
        mse = sum(squared_errors) / len(squared_errors) if squared_errors else 0.0
        rmse = np.sqrt(mse)
        
        # Calculate MAE
        abs_errors = [abs(t - p) for t, p in zip(y_true, y_pred)]
        mae = sum(abs_errors) / len(abs_errors) if abs_errors else 0.0
        
        # Calculate MAPE (avoid division by zero)
        percentage_errors = []
        for t, p in zip(y_true, y_pred):
            if t != 0:
                percentage_error = abs((t - p) / t)
                percentage_errors.append(percentage_error)
        mape = (sum(percentage_errors) / len(percentage_errors) * 100) if percentage_errors else 0.0
        
        # Direction accuracy (did prediction say up/down correctly?)
        true_directions = [1 if t > 0 else (0 if t == 0 else -1) for t in y_true]
        pred_directions = [1 if p > 0 else (0 if p == 0 else -1) for p in y_pred]
        direction_hits = sum(1 for td, pd in zip(true_directions, pred_directions) if td == pd)
        direction_accuracy = direction_hits / len(true_directions) if true_directions else 0.0
        
        return {
            "mse": float(mse),
            "rmse": float(rmse),
            "mae": float(mae),
            "mape": float(mape),
            "direction_accuracy": float(direction_accuracy),
            "sample_size": len(y_true)
        }
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe ratio for forecast performance
        """
        if len(returns) < 2:
            return 0.0
        
        # Calculate daily risk-free rate
        daily_rf = risk_free_rate / 252
        excess_returns = [r - daily_rf for r in returns]
        mean_excess = sum(excess_returns) / len(excess_returns) if excess_returns else 0.0
        
        # Calculate standard deviation of excess returns
        if len(excess_returns) > 1:
            variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
            std_excess = np.sqrt(variance) if variance >= 0 else 0.0
        else:
            std_excess = 0.0
        
        if std_excess == 0:
            return 0.0
        
        # Annualized Sharpe ratio
        sharpe = mean_excess / std_excess
        return float(sharpe * np.sqrt(252))  # Annualized
    
    def calculate_sortino_ratio(self, returns: List[float], target_return: float = 0.0) -> float:
        """
        Calculate Sortino ratio for forecast performance
        """
        if len(returns) < 2:
            return 0.0
        
        expected_return = sum(returns) / len(returns) if returns else 0.0
        
        # Calculate downside deviation
        downside_returns = [r for r in returns if r < target_return]
        if len(downside_returns) > 0:
            downside_variance = sum((r - expected_return) ** 2 for r in downside_returns) / len(downside_returns)
            downside_deviation = np.sqrt(downside_variance)
        else:
            downside_deviation = 1e-8  # Avoid division by zero
        
        # Annualized Sortino ratio
        sortino = (expected_return - target_return) / downside_deviation
        return float(sortino * np.sqrt(252))  # Annualized
    
    def track_prediction(self, model_name: str, ticker: str, horizon: str, predicted_value: float, actual_value: Optional[float], confidence: float, timestamp: Optional[datetime] = None):
        """
        Track a single prediction with actual outcome if available
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        prediction_record = {
            "id": f"{model_name}_{ticker}_{timestamp.timestamp()}",
            "model": model_name,
            "ticker": ticker,
            "horizon": horizon,
            "predicted": predicted_value,
            "actual": actual_value,
            "confidence": confidence,
            "timestamp": timestamp.isoformat() + "Z",
            "evaluated": actual_value is not None
        }
        
        # Store the prediction
        self.tracking_data["predictions"].append(prediction_record)
        
        # If actual value is available, update model performance
        if actual_value is not None:
            # Update model-specific stats
            if model_name not in self.tracking_data["models"]:
                self.tracking_data["models"][model_name] = {
                    "name": model_name,
                    "predictions": [],
                    "evaluated_predictions": [],
                    "ticker_performance": {},
                    "horizon_performance": {}
                }
            
            model_stats = self.tracking_data["models"][model_name]
            model_stats["predictions"].append({
                "ticker": ticker,
                "horizon": horizon,
                "predicted": predicted_value,
                "actual": actual_value,
                "confidence": confidence,
                "timestamp": prediction_record["timestamp"],
                "evaluated": True
            })
            model_stats["evaluated_predictions"].append({
                "ticker": ticker,
                "predicted": predicted_value,
                "actual": actual_value,
                "confidence": confidence
            })
            
            # Update ticker-specific stats
            if ticker not in model_stats["ticker_performance"]:
                model_stats["ticker_performance"][ticker] = {
                    "predictions": 0,
                    "evaluated": 0,
                    "hit_rate": 0.0,
                    "avg_confidence": 0.0
                }
            
            ticker_stats = model_stats["ticker_performance"][ticker]
            ticker_stats["predictions"] += 1
            ticker_stats["evaluated"] += 1
            
            # Recalculate hit rate for this ticker
            ticker_evaluated = [p for p in model_stats["evaluated_predictions"] if p["ticker"] == ticker]
            if ticker_evaluated:
                direction_hits = sum(1 for p in ticker_evaluated 
                                   if (p["predicted"] > 0) == (p["actual"] > 0))
                ticker_stats["hit_rate"] = direction_hits / len(ticker_evaluated)
                
                avg_conf = sum(p["confidence"] for p in ticker_evaluated) / len(ticker_evaluated)
                ticker_stats["avg_confidence"] = avg_conf
    
    def calculate_performance_metrics(self, predictions: List[float], actuals: List[float]) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics
        """
        if len(predictions) == 0 or len(actuals) == 0:
            return {
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
                "calculated_at": datetime.utcnow().isoformat() + "Z"
            }
        
        # Calculate metrics - y_true are the actuals, y_pred are the predictions
        classification_metrics = self.calculate_binary_classification_metrics(actuals, predictions)
        regression_metrics = self.calculate_regression_metrics(actuals, predictions)
        
        # Calculate returns based on prediction accuracy (assuming profit from accurate predictions)
        returns = []
        for pred, actual in zip(predictions, actuals):
            # Simplified return calculation - in reality would be based on actual trading strategy
            if (pred > 0 and actual > 0) or (pred < 0 and actual < 0):  # Correct direction
                returns.append(abs(actual))  # Profit proportional to actual magnitude
            else:
                returns.append(-abs(actual))  # Loss when wrong direction
        
        sharpe_ratio = self.calculate_sharpe_ratio(returns)
        sortino_ratio = self.calculate_sortino_ratio(returns)
        
        # Calculate average confidence of evaluated predictions
        evaluated_preds = [p for p in self.tracking_data["predictions"] if p["evaluated"]]
        avg_confidence = sum(p["confidence"] for p in evaluated_preds) / len(evaluated_preds) if evaluated_preds else 0.0
        
        return {
            "classification_metrics": classification_metrics,
            "regression_metrics": regression_metrics,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "total_predictions": len(self.tracking_data["predictions"]),
            "evaluated_predictions": len(evaluated_preds),
            "avg_confidence": avg_confidence,
            "calculated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    def get_model_performance(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for a specific model or all models
        """
        if model_name:
            return self.tracking_data["models"].get(model_name, {})
        else:
            return self.tracking_data["models"]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report
        """
        all_predictions = self.tracking_data["predictions"]
        evaluated_predictions = [p for p in all_predictions if p["evaluated"]]
        
        # Extract prediction and actual values for metrics calculation
        predicted_values = [p["predicted"] for p in evaluated_predictions]
        actual_values = [p["actual"] for p in evaluated_predictions]
        confidences = [p["confidence"] for p in evaluated_predictions]
        
        overall_metrics = self.calculate_performance_metrics(predicted_values, actual_values)
        
        return {
            "summary": {
                "total_predictions": len(all_predictions),
                "evaluated_predictions": len(evaluated_predictions),
                "evaluation_rate": len(evaluated_predictions) / len(all_predictions) if all_predictions else 0.0,
                "models_tracked": list(self.tracking_data["models"].keys()),
                "tickers_covered": list(set(p["ticker"] for p in all_predictions)),
                "horizons_covered": list(set(p["horizon"] for p in all_predictions)),
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0
            },
            "overall_metrics": overall_metrics,
            "model_performance": self.tracking_data["models"],
            "metrics_history": self.tracking_data.get("metrics_history", []),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "last_update": self.tracking_data.get("metrics_history", [])[-1]["timestamp"] if self.tracking_data.get("metrics_history", []) else None
        }


# Global instance for shared tracking
performance_tracker = ModelPerformanceTracker()

# Convenience functions for easy access
def track_prediction(model_name: str, ticker: str, horizon: str, predicted_value: float, actual_value: Optional[float] = None, confidence: float = 1.0):
    """
    Convenience function to track a prediction
    """
    return performance_tracker.track_prediction(model_name, ticker, horizon, predicted_value, actual_value, confidence)

def get_performance_report():
    """
    Get the current performance report
    """
    return performance_tracker.get_performance_report()

def get_model_performance(model_name: str):
    """
    Get performance for a specific model
    """
    return performance_tracker.get_model_performance(model_name)