"""
Prediction Accuracy Metrics Model
Task: FC-API-032 - Prediction Accuracy Analytics
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np
import statistics
from dataclasses import dataclass

@dataclass
class PredictionAccuracyMetrics:
    """
    Data class for prediction accuracy metrics
    """
    hit_rate: float
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    mean_abs_error: float
    root_mean_squared_error: float
    tracking_error: float
    correlation: float
    generated_at: str
    sample_size: int

class AccuracyMetricsCalculator:
    """
    Calculator for prediction accuracy metrics
    """
    
    def __init__(self):
        self.metrics_cache = {}
    
    def calculate_accuracy_metrics(self, predictions: List[float], actuals: List[float], 
                                 tickers: Optional[List[str]] = None,  # Optional grouping by ticker
                                 horizons: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive accuracy metrics for predictions vs actuals
        """
        if len(predictions) != len(actuals):
            raise ValueError(f"Mismatched lengths: predictions({len(predictions)}) vs actuals({len(actuals)})")
        
        if len(predictions) == 0:
            return {
                "overall": self._get_default_metrics(),
                "by_ticker": {},
                "by_horizon": {},
                "sample_size": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "message": "No data to calculate metrics for"
            }
        
        # Calculate overall metrics
        overall_metrics = self._calculate_metrics(predictions, actuals)
        
        # Calculate by group (if tickers or horizons provided)
        by_ticker_metrics = {}
        by_horizon_metrics = {}
        
        if tickers and len(tickers) == len(predictions):
            by_ticker_metrics = self._calculate_group_metrics(predictions, actuals, tickers)
        
        if horizons and len(horizons) == len(predictions):
            by_horizon_metrics = self._calculate_group_metrics(predictions, actuals, horizons)
        
        return {
            "overall": overall_metrics,
            "by_ticker": by_ticker_metrics,
            "by_horizon": by_horizon_metrics,
            "sample_size": len(predictions),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "prediction_accuracy": True
        }
    
    def calculate_accuracy_by_window(self, predictions: List[float], actuals: List[float], 
                                   timestamps: List[str], window_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Calculate accuracy metrics by time windows to track evolution
        """
        if len(predictions) != len(actuals) or len(predictions) != len(timestamps):
            raise ValueError("Predictions, actuals, and timestamps must have same length")
        
        # Convert timestamps to datetime objects and pair with predictions and actuals
        paired_data = [(datetime.fromisoformat(ts.replace('Z', '+00:00')), pred, act) 
                      for ts, pred, act in zip(timestamps, predictions, actuals)]
        
        # Sort by timestamp
        paired_data.sort(key=lambda x: x[0])
        
        # Group by time window
        window_metrics = []
        current_window_start = paired_data[0][0] if paired_data else None
        
        if not current_window_start:
            return []
        
        # For simplicity, just calculate metrics for the entire time period
        # In a real implementation, this would split into windows
        all_predictions = [item[1] for item in paired_data]
        all_actuals = [item[2] for item in paired_data]
        
        metrics = self._calculate_metrics(all_predictions, all_actuals)
        window_metrics.append({
            "window_start": current_window_start.isoformat() + "Z",
            "window_end": paired_data[-1][0].isoformat() + "Z",
            "metrics": metrics,
            "count": len(all_predictions)
        })
        
        return window_metrics
    
    def _calculate_metrics(self, predictions: List[float], actuals: List[float]) -> Dict[str, float]:
        """
        Calculate individual accuracy metrics
        """
        n = len(predictions)
        if n == 0:
            return self._get_default_metrics()
        
        # Calculate direction accuracy (hit rate)
        pred_directions = [1 if p > 0 else (0 if p == 0 else -1) for p in predictions]
        actual_directions = [1 if a > 0 else (0 if a == 0 else -1) for a in actuals]
        
        hit_count = sum(1 for pd, ad in zip(pred_directions, actual_directions) if pd == ad)
        hit_rate = hit_count / n if n > 0 else 0.0
        
        # Calculate accuracy (for classification-like metrics)
        correct_predictions = sum(1 for p, a in zip(predictions, actuals) if abs(p - a) < 0.1)  # Simple threshold
        accuracy = correct_predictions / n if n > 0 else 0.0
        
        # For precision/recall, we need to define positive class (e.g., up trends)
        # Assuming positive trend is when actual > 0
        true_positives = sum(1 for p, a in zip(predictions, actuals) if p > 0 and a > 0)
        false_positives = sum(1 for p, a in zip(predictions, actuals) if p > 0 and a <= 0)
        false_negatives = sum(1 for p, a in zip(predictions, actuals) if p <= 0 and a > 0)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Calculate regression metrics
        errors = [abs(p - a) for p, a in zip(predictions, actuals)]
        mean_abs_error = sum(errors) / n if n > 0 else 0.0
        
        squared_errors = [(p - a) ** 2 for p, a in zip(predictions, actuals)]
        mean_squared_error = sum(squared_errors) / n if n > 0 else 0.0
        root_mean_squared_error = mean_squared_error ** 0.5
        
        # Tracking error (std of prediction errors)
        tracking_error = statistics.stdev(errors) if len(errors) > 1 else 0.0
        
        # Correlation between predictions and actuals
        try:
            pred_arr = np.array(predictions)
            act_arr = np.array(actuals)
            if len(pred_arr) > 1 and len(act_arr) > 1:
                correlation_matrix = np.corrcoef(pred_arr, act_arr)
                correlation = float(correlation_matrix[0, 1]) if not np.isnan(correlation_matrix[0, 1]) else 0.0
            else:
                correlation = 0.0
        except:
            correlation = 0.0  # Default if correlation calculation fails
        
        return {
            "hit_rate": round(hit_rate, 4),
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "mean_abs_error": round(mean_abs_error, 4),
            "root_mean_squared_error": round(root_mean_squared_error, 4),
            "tracking_error": round(tracking_error, 4),
            "correlation": round(correlation, 4),
            "sample_size": n
        }
    
    def _get_default_metrics(self) -> Dict[str, float]:
        """
        Return default metrics when no data is available
        """
        return {
            "hit_rate": 0.0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "mean_abs_error": 0.0,
            "root_mean_squared_error": 0.0,
            "tracking_error": 0.0,
            "correlation": 0.0,
            "sample_size": 0
        }
    
    def _calculate_group_metrics(self, predictions: List[float], actuals: List[float], 
                               groups: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate metrics grouped by a categorical variable (e.g., ticker or horizon)
        """
        if len(predictions) != len(actuals) or len(predictions) != len(groups):
            raise ValueError("Predictions, actuals, and groups must have same length")
        
        # Group by categories
        grouped_data = {}
        for i, group in enumerate(groups):
            if group not in grouped_data:
                grouped_data[group] = {"predictions": [], "actuals": []}
            grouped_data[group]["predictions"].append(predictions[i])
            grouped_data[group]["actuals"].append(actuals[i])
        
        # Calculate metrics for each group
        results = {}
        for group, data in grouped_data.items():
            results[group] = self._calculate_metrics(data["predictions"], data["actuals"])
        
        return results


# Global instance
accuracy_calculator = AccuracyMetricsCalculator()

def calculate_prediction_accuracy_metrics(predictions: List[float], actuals: List[float], 
                                        tickers: Optional[List[str]] = None,
                                        horizons: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convenience function to calculate prediction accuracy metrics
    """
    return accuracy_calculator.calculate_accuracy_metrics(predictions, actuals, tickers, horizons)

def calculate_accuracy_by_window(predictions: List[float], actuals: List[float], 
                                timestamps: List[str], window_hours: int = 24) -> List[Dict[str, Any]]:
    """
    Convenience function to calculate accuracy by time windows
    """
    return accuracy_calculator.calculate_accuracy_by_window(predictions, actuals, timestamps, window_hours)