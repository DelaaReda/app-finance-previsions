"""
Accuracy Metrics Calculator
Task: FC-API-031 - Prediction Accuracy Analytics  
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import math
from statistics import mean, stdev
import numpy as np


class AccuracyMetricsCalculator:
    """
    Calculate accuracy metrics for ML predictions vs actual outcomes
    """
    
    def __init__(self):
        self.cached_metrics = {}
    
    def calculate_hit_rate(self, predictions: List[float], actuals: List[float]) -> float:
        """
        Calculate hit rate (percentage of correct directional predictions)
        
        Args:
            predictions: List of predicted returns/values
            actuals: List of actual returns/values
        
        Returns:
            Hit rate as percentage (0.0 to 1.0)
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return 0.0
        
        if len(predictions) == 0:
            return 0.0
        
        correct_directions = 0
        for pred, actual in zip(predictions, actuals):
            # Both positive or both negative (correct direction)
            if (pred >= 0 and actual >= 0) or (pred < 0 and actual < 0):
                correct_directions += 1
        
        return correct_directions / len(predictions)
    
    def calculate_accuracy(self, predictions: List[float], actuals: List[float], tolerance: float = 0.01) -> float:
        """
        Calculate accuracy within tolerance (percentage of predictions close to actuals)
        
        Args:
            predictions: List of predicted values
            actuals: List of actual values  
            tolerance: Tolerance for considering prediction "accurate"
        
        Returns:
            Accuracy as percentage (0.0 to 1.0)
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return 0.0
        
        if len(predictions) == 0:
            return 0.0
        
        accurate_predictions = 0
        for pred, actual in zip(predictions, actuals):
            if actual == 0:
                # Special case for actual value of 0
                if abs(pred) <= tolerance:
                    accurate_predictions += 1
            else:
                # Calculate percentage error
                percent_error = abs((pred - actual) / actual)
                if percent_error <= tolerance:
                    accurate_predictions += 1
        
        return accurate_predictions / len(predictions)
    
    def calculate_precision(self, predictions: List[float], actuals: List[float], positive_threshold: float = 0.0) -> float:
        """
        Calculate precision for positive predictions (TP / (TP + FP))
        
        Args:
            predictions: List of predicted values
            actuals: List of actual values
            positive_threshold: Threshold for considering a prediction positive
        
        Returns:
            Precision as percentage (0.0 to 1.0)
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return 0.0
        
        if len(predictions) == 0:
            return 0.0
        
        true_positives = 0
        false_positives = 0
        
        for pred, actual in zip(predictions, actuals):
            if pred >= positive_threshold:  # Model predicts positive
                if actual >= positive_threshold:  # Actually positive
                    true_positives += 1
                else:  # Actually negative (but predicted positive)
                    false_positives += 1
        
        if (true_positives + false_positives) == 0:
            return 0.0  # No positive predictions made
        
        return true_positives / (true_positives + false_positives)
    
    def calculate_recall(self, predictions: List[float], actuals: List[float], positive_threshold: float = 0.0) -> float:
        """
        Calculate recall for positive predictions (TP / (TP + FN))
        
        Args:
            predictions: List of predicted values  
            actuals: List of actual values
            positive_threshold: Threshold for considering a prediction positive
        
        Returns:
            Recall as percentage (0.0 to 1.0)
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return 0.0
        
        if len(predictions) == 0:
            return 0.0
        
        true_positives = 0
        false_negatives = 0
        
        for pred, actual in zip(predictions, actuals):
            if actual >= positive_threshold:  # Actually positive
                if pred >= positive_threshold:  # Predicted positive (correct)
                    true_positives += 1
                else:  # Predicted negative (but actually positive - missed)
                    false_negatives += 1
        
        if (true_positives + false_negatives) == 0:
            return 0.0  # No actual positives in dataset
        
        return true_positives / (true_positives + false_negatives)
    
    def calculate_f1_score(self, predictions: List[float], actuals: List[float], positive_threshold: float = 0.0) -> float:
        """
        Calculate F1 score (harmonic mean of precision and recall)
        
        Args:
            predictions: List of predicted values
            actuals: List of actual values  
            positive_threshold: Threshold for considering a prediction positive
        
        Returns:
            F1 score as percentage (0.0 to 1.0)
        """
        precision = self.calculate_precision(predictions, actuals, positive_threshold)
        recall = self.calculate_recall(predictions, actuals, positive_threshold)
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)
    
    def calculate_mae(self, predictions: List[float], actuals: List[float]) -> float:
        """
        Calculate Mean Absolute Error
        
        Args:
            predictions: List of predicted values
            actuals: List of actual values
        
        Returns:
            Mean Absolute Error
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return 0.0
        
        if len(predictions) == 0:
            return 0.0
        
        errors = [abs(pred - actual) for pred, actual in zip(predictions, actuals)]
        return sum(errors) / len(errors)
    
    def calculate_rmse(self, predictions: List[float], actuals: List[float]) -> float:
        """
        Calculate Root Mean Squared Error
        
        Args:
            predictions: List of predicted values
            actuals: List of actual values
        
        Returns:
            Root Mean Squared Error
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return 0.0
        
        if len(predictions) == 0:
            return 0.0
        
        squared_errors = [(pred - actual) ** 2 for pred, actual in zip(predictions, actuals)]
        mse = sum(squared_errors) / len(squared_errors)
        return math.sqrt(mse)
    
    def calculate_tracking_error(self, predictions: List[float], actuals: List[float]) -> float:
        """
        Calculate Tracking Error (std of differences between predictions and actuals)
        
        Args:
            predictions: List of predicted values
            actuals: List of actual values
        
        Returns:
            Tracking Error (standard deviation of errors)
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return 0.0
        
        if len(predictions) < 2:
            return 0.0
        
        errors = [pred - actual for pred, actual in zip(predictions, actuals)]
        
        # Calculate standard deviation of errors
        if len(errors) == 1:
            return 0.0  # Standard deviation of single value is 0
        
        avg_error = sum(errors) / len(errors)
        squared_deviations = [(e - avg_error) ** 2 for e in errors]
        variance = sum(squared_deviations) / (len(squared_deviations) - 1)  # Sample variance
        return math.sqrt(variance)
    
    def calculate_correlation(self, predictions: List[float], actuals: List[float]) -> float:
        """
        Calculate correlation coefficient between predictions and actuals
        
        Args:
            predictions: List of predicted values
            actuals: List of actual values
        
        Returns:
            Correlation coefficient (-1.0 to 1.0)
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return 0.0
        
        if len(predictions) < 2:
            return 0.0
        
        n = len(predictions)
        pred_mean = sum(predictions) / n
        actual_mean = sum(actuals) / n
        
        # Calculate numerator and denominator for correlation coefficient
        numerator = sum((predictions[i] - pred_mean) * (actuals[i] - actual_mean) for i in range(n))
        
        pred_sq_diff = sum((predictions[i] - pred_mean) ** 2 for i in range(n))
        actual_sq_diff = sum((actuals[i] - actual_mean) ** 2 for i in range(n))
        
        denominator = math.sqrt(pred_sq_diff * actual_sq_diff)
        
        if denominator == 0:
            return 0.0  # Avoid division by zero
        
        correlation = numerator / denominator
        # Clamp between -1 and 1 to handle floating-point errors
        return max(-1.0, min(1.0, correlation))
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02/252) -> float:
        """
        Calculate Sharpe Ratio of returns (excess return per unit of risk)
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Risk-free rate (per period)
        
        Returns:
            Sharpe Ratio
        """
        if not returns or len(returns) == 0:
            return 0.0
        
        if len(returns) == 1:
            return 0.0  # Cannot calculate sharpe with single return
        
        avg_return = sum(returns) / len(returns)
        excess_return = avg_return - risk_free_rate
        
        # Calculate volatility (standard deviation of returns)
        if len(returns) > 1:
            volatility = stdev(returns)
        else:
            volatility = 0.0
        
        if volatility == 0:
            return 0.0  # Avoid division by zero
        
        return excess_return / volatility
    
    def calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02/252, target_return: float = 0.0) -> float:
        """
        Calculate Sortino Ratio (return per unit of downside risk)
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Risk-free rate (per period)
            target_return: Minimum acceptable return (MAR)
        
        Returns:
            Sortino Ratio
        """
        if not returns or len(returns) == 0:
            return 0.0
        
        if len(returns) == 1:
            return 0.0
        
        # Calculate excess return over risk_free_rate
        excess_returns = [r - risk_free_rate for r in returns]
        avg_excess_return = sum(excess_returns) / len(excess_returns)
        
        # Calculate downside deviation (only negative deviations from target)
        downside_returns = [r for r in excess_returns if r < target_return]
        
        if len(downside_returns) == 0:
            # If no downside risk, return infinity-like value or high number
            return avg_excess_return / 0.0001 if avg_excess_return > 0 else 0.0
        
        # Calculate semi-deviation (downside risk)
        squared_downside = [(r - target_return) ** 2 for r in downside_returns]
        downside_variance = sum(squared_downside) / len(downside_returns)
        downside_deviation = math.sqrt(downside_variance)
        
        if downside_deviation == 0:
            return 0.0  # Avoid division by zero
        
        return avg_excess_return / downside_deviation
    
    def calculate_comprehensive_metrics(self, 
                                      predictions: List[float], 
                                      actuals: List[float],
                                      positive_threshold: float = 0.0,
                                      tolerance: float = 0.01) -> Dict[str, float]:
        """
        Calculate all accuracy metrics at once
        
        Args:
            predictions: List of predicted values
            actuals: List of actual values
            positive_threshold: Threshold for positive classification
            tolerance: Tolerance for accuracy calculation
        
        Returns:
            Dictionary with all calculated metrics
        """
        if not predictions or not actuals:
            return self._get_empty_metrics()
        
        if len(predictions) != len(actuals):
            return self._get_empty_metrics()
        
        # Calculate all metrics
        hit_rate = self.calculate_hit_rate(predictions, actuals)
        accuracy = self.calculate_accuracy(predictions, actuals, tolerance)
        precision = self.calculate_precision(predictions, actuals, positive_threshold)
        recall = self.calculate_recall(predictions, actuals, positive_threshold)
        f1_score = self.calculate_f1_score(predictions, actuals, positive_threshold)
        mae = self.calculate_mae(predictions, actuals)
        rmse = self.calculate_rmse(predictions, actuals)
        tracking_error = self.calculate_tracking_error(predictions, actuals)
        correlation = self.calculate_correlation(predictions, actuals)
        
        # Calculate returns-based metrics if dealing with returns
        prediction_returns = [(p - a) / abs(a) if a != 0 else 0 for p, a in zip(predictions, actuals) if isinstance(a, (int, float))]
        if prediction_returns:
            sharpe_ratio = self.calculate_sharpe_ratio(prediction_returns)
        else:
            sharpe_ratio = 0.0  # Default if no valid returns
        
        return {
            "hit_rate": round(hit_rate, 4),
            "accuracy": round(accuracy, 4), 
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "mean_absolute_error": round(mae, 6),
            "root_mean_squared_error": round(rmse, 6),
            "tracking_error": round(tracking_error, 6),
            "correlation": round(correlation, 4),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "sample_size": len(predictions),
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    def calculate_metrics_by_horizon(self, 
                                   predictions: List[Dict[str, Any]], 
                                   actuals: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """
        Calculate metrics grouped by prediction horizon
        
        Args:
            predictions: List of prediction dictionaries with horizon and value
            actuals: Dictionary mapping timestamps/tickers to actual values
        
        Returns:
            Dictionary with metrics by horizon
        """
        if not predictions:
            return {}
        
        # Group predictions by horizon
        horizon_groups = {}
        for pred in predictions:
            horizon = pred.get("horizon", "unknown")
            if horizon not in horizon_groups:
                horizon_groups[horizon] = {"predictions": [], "actuals": []}
            
            predicted_value = pred.get("predicted_value") or pred.get("expected_return") or pred.get("value", 0.0)
            ticker = pred.get("ticker") or pred.get("symbol", "UNKNOWN")
            
            # Try to find corresponding actual value
            actual_value = 0.0
            if ticker in actuals:
                actual_value = actuals[ticker]
            elif "values" in actuals and ticker in actuals["values"]:
                actual_value = actuals["values"][ticker]
            elif "data" in actuals and isinstance(actuals["data"], dict) and ticker in actuals["data"]:
                actual_value = actuals["data"][ticker]
            
            horizon_groups[horizon]["predictions"].append(predicted_value)
            horizon_groups[horizon]["actuals"].append(actual_value)
        
        # Calculate metrics for each horizon
        metrics_by_horizon = {}
        for horizon, data in horizon_groups.items():
            preds = data["predictions"]
            actuals_list = data["actuals"]
            
            if len(preds) > 0 and len(actuals_list) > 0:
                metrics_by_horizon[horizon] = self.calculate_comprehensive_metrics(preds, actuals_list)
            else:
                metrics_by_horizon[horizon] = self._get_empty_metrics()
        
        return metrics_by_horizon
    
    def calculate_metrics_by_asset(self,
                                 predictions: List[Dict[str, Any]],
                                 actuals: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """
        Calculate metrics grouped by asset/ticker
        
        Args:
            predictions: List of prediction dictionaries with ticker and value
            actuals: Dictionary mapping tickers to actual values
        
        Returns:
            Dictionary with metrics by asset
        """
        if not predictions:
            return {}
        
        # Group predictions by asset
        asset_groups = {}
        for pred in predictions:
            ticker = pred.get("ticker") or pred.get("symbol") or "UNKNOWN"
            if ticker not in asset_groups:
                asset_groups[ticker] = {"predictions": [], "actuals": []}
            
            predicted_value = pred.get("predicted_value") or pred.get("expected_return") or pred.get("value", 0.0)
            
            # Try to find corresponding actual value
            actual_value = 0.0
            if ticker in actuals:
                actual_value = actuals[ticker]
            elif "values" in actuals and ticker in actuals["values"]:
                actual_value = actuals["values"][ticker]
            elif "data" in actuals and isinstance(actuals["data"], dict) and ticker in actuals["data"]:
                actual_value = actuals["data"][ticker]
            
            asset_groups[ticker]["predictions"].append(predicted_value)
            asset_groups[ticker]["actuals"].append(actual_value)
        
        # Calculate metrics for each asset
        metrics_by_asset = {}
        for ticker, data in asset_groups.items():
            preds = data["predictions"]
            actuals_list = data["actuals"]
            
            if len(preds) > 0 and len(actuals_list) > 0:
                metrics_by_asset[ticker] = self.calculate_comprehensive_metrics(preds, actuals_list)
            else:
                metrics_by_asset[ticker] = self._get_empty_metrics()
        
        return metrics_by_asset
    
    def _get_empty_metrics(self) -> Dict[str, Any]:
        """
        Return empty metrics structure to maintain never-empty contract
        """
        return {
            "hit_rate": 0.0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "mean_absolute_error": 0.0,
            "root_mean_squared_error": 0.0,
            "tracking_error": 0.0,
            "correlation": 0.0,
            "sharpe_ratio": 0.0,
            "sample_size": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "message": "No prediction-actual pairs available for metrics calculation, returning empty structure to maintain never-empty contract"
        }


# Global instance
accuracy_metrics_calculator = AccuracyMetricsCalculator()


# Convenience functions
def calculate_accuracy_metrics(predictions: List[float], actuals: List[float], tolerance: float = 0.01):
    """
    Calculate accuracy metrics for predictions vs actuals
    """
    return accuracy_metrics_calculator.calculate_comprehensive_metrics(predictions, actuals, tolerance=tolerance)

def calculate_hit_rate(predictions: List[float], actuals: List[float]):
    """
    Calculate hit rate (directional accuracy)
    """
    return accuracy_metrics_calculator.calculate_hit_rate(predictions, actuals)

def calculate_precision(predictions: List[float], actuals: List[float], positive_threshold: float = 0.0):
    """
    Calculate precision of positive predictions
    """
    return accuracy_metrics_calculator.calculate_precision(predictions, actuals, positive_threshold)

def calculate_recall(predictions: List[float], actuals: List[float], positive_threshold: float = 0.0):
    """
    Calculate recall of positive predictions
    """
    return accuracy_metrics_calculator.calculate_recall(predictions, actuals, positive_threshold)

def calculate_f1_score(predictions: List[float], actuals: List[float], positive_threshold: float = 0.0):
    """
    Calculate F1 score
    """
    return accuracy_metrics_calculator.calculate_f1_score(predictions, actuals, positive_threshold)