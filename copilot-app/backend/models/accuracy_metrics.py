"""
Prediction Accuracy Metrics Model - Finance Copilot
Defines the structures for evaluating forecast quality and performance
Task: FC-API-032 - ALEX-FINANCE-ANALYST-SUPERMAN-29
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np


class AccuracyMetricCalculator:
    """
    Calculator for forecast accuracy metrics including hit rate, MAE, RMSE, and directional accuracy
    """
    
    def __init__(self):
        pass
    
    def calculate_hit_rate(self, predicted_directions: List[str], actual_directions: List[str]) -> float:
        """
        Calculate hit rate: percentage of correct directional predictions
        """
        if not predicted_directions or not actual_directions or len(predicted_directions) != len(actual_directions):
            return 0.0
        
        correct = sum(1 for pred, actual in zip(predicted_directions, actual_directions) if pred == actual)
        return correct / len(predicted_directions) if len(predicted_directions) > 0 else 0.0
    
    def calculate_mae(self, predicted_values: List[float], actual_values: List[float]) -> float:
        """
        Calculate Mean Absolute Error
        """
        if not predicted_values or not actual_values or len(predicted_values) != len(actual_values):
            return 0.0
        
        errors = [abs(pred - actual) for pred, actual in zip(predicted_values, actual_values)]
        return sum(errors) / len(errors) if errors else 0.0
    
    def calculate_rmse(self, predicted_values: List[float], actual_values: List[float]) -> float:
        """
        Calculate Root Mean Squared Error
        """
        if not predicted_values or not actual_values or len(predicted_values) != len(actual_values):
            return 0.0
        
        squared_errors = [(pred - actual)**2 for pred, actual in zip(predicted_values, actual_values)]
        mse = sum(squared_errors) / len(squared_errors) if squared_errors else 0.0
        return mse ** 0.5
    
    def calculate_directional_accuracy(self, predicted_returns: List[float], actual_returns: List[float]) -> Dict[str, float]:
        """
        Calculate accuracy of directional predictions (up vs down vs neutral)
        """
        if not predicted_returns or not actual_returns or len(predicted_returns) != len(actual_returns):
            return {"up_accuracy": 0.0, "down_accuracy": 0.0, "neutral_accuracy": 0.0, "overall_direction_accuracy": 0.0}
        
        # Define directions based on returns
        def get_direction(ret):
            if ret > 0.005:  # Up if > 0.5%
                return "up"
            elif ret < -0.005:  # Down if < -0.5%
                return "down"
            else:  # Neutral for small movements
                return "neutral"
        
        predicted_dirs = [get_direction(ret) for ret in predicted_returns]
        actual_dirs = [get_direction(ret) for ret in actual_returns]
        
        # Calculate per-direction accuracy
        up_correct = sum(1 for pred, actual in zip(predicted_dirs, actual_dirs) if pred == "up" and actual == "up")
        up_total = sum(1 for pred in predicted_dirs if pred == "up")
        up_acc = up_correct / up_total if up_total > 0 else 0.0
        
        down_correct = sum(1 for pred, actual in zip(predicted_dirs, actual_dirs) if pred == "down" and actual == "down")
        down_total = sum(1 for pred in predicted_dirs if pred == "down")
        down_acc = down_correct / down_total if down_total > 0 else 0.0
        
        neutral_correct = sum(1 for pred, actual in zip(predicted_dirs, actual_dirs) if pred == "neutral" and actual == "neutral")
        neutral_total = sum(1 for pred in predicted_dirs if pred == "neutral")
        neutral_acc = neutral_correct / neutral_total if neutral_total > 0 else 0.0
        
        overall_correct = sum(1 for pred, actual in zip(predicted_dirs, actual_dirs) if pred == actual)
        overall_acc = overall_correct / len(predicted_dirs) if predicted_dirs else 0.0
        
        return {
            "up_accuracy": up_acc,
            "down_accuracy": down_acc,
            "neutral_accuracy": neutral_acc,
            "overall_direction_accuracy": overall_acc
        }
    
    def calculate_profit_factor(self, predictions: List[Dict], actual_returns: List[float]) -> float:
        """
        Calculate profit factor based on forecast confidence and actual outcomes
        """
        if not predictions or not actual_returns or len(predictions) != len(actual_returns):
            return 0.0
        
        gross_profit = 0
        gross_loss = 0
        
        for i, pred in enumerate(predictions):
            if i < len(actual_returns):
                # Calculate profit/loss based on prediction and actual outcome
                if pred.get('direction') == 'up' and actual_returns[i] > 0:
                    # Correct bullish prediction
                    gross_profit += abs(actual_returns[i]) * pred.get('confidence', 1.0)
                elif pred.get('direction') == 'down' and actual_returns[i] < 0:
                    # Correct bearish prediction
                    gross_profit += abs(actual_returns[i]) * pred.get('confidence', 1.0)
                else:
                    # Wrong prediction
                    gross_loss += abs(actual_returns[i]) * pred.get('confidence', 1.0)
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 1.0
        
        return gross_profit / gross_loss if gross_profit > 0 else 0.0
    
    def calculate_sharpe_ratio_for_predictions(self, predictions: List[Dict], actual_returns: List[float]) -> float:
        """
        Calculate sharpe ratio considering prediction accuracy
        """
        if not predictions or not actual_returns or len(predictions) != len(actual_returns):
            return 0.0
        
        # Calculate returns based on following correct predictions
        strategy_returns = []
        for i, pred in enumerate(predictions):
            if i < len(actual_returns):
                # If we followed the prediction, apply the actual return (scaled by confidence)
                if pred.get('direction') == 'up' and actual_returns[i] > 0:
                    # Correct bullish - follow and benefit
                    strategy_returns.append(actual_returns[i] * pred.get('confidence', 1.0))
                elif pred.get('direction') == 'down' and actual_returns[i] < 0:
                    # Correct bearish - follow and benefit (multiply by -1 since direction is down)
                    strategy_returns.append(-actual_returns[i] * pred.get('confidence', 1.0))
                elif pred.get('direction') == 'neutral':
                    # Don't trade on neutral
                    strategy_returns.append(0.0)
                else:
                    # Wrong prediction
                    strategy_returns.append(-abs(actual_returns[i]) * pred.get('confidence', 1.0))
        
        if not strategy_returns or len(strategy_returns) == 0:
            return 0.0
        
        # Calculate Sharpe ratio
        avg_return = sum(strategy_returns) / len(strategy_returns)
        volatility = np.std(strategy_returns) if strategy_returns else 0.0
        
        risk_free_rate = 0.02 / 252  # Daily risk free rate (annual 2%)
        excess_return = avg_return - risk_free_rate
        
        if volatility == 0:
            return 0.0
        
        return excess_return / volatility
    
    def calculate_all_metrics(self, historical_forecasts: List[Dict], actual_returns: List[float]) -> Dict[str, any]:
        """
        Calculate all accuracy metrics for a given set of historical forecasts
        """
        if not historical_forecasts or not actual_returns:
            return {
                "hit_rate": 0.0,
                "mae": 0.0,
                "rmse": 0.0,
                "directional_accuracy": {
                    "up_accuracy": 0.0,
                    "down_accuracy": 0.0,
                    "neutral_accuracy": 0.0,
                    "overall_direction_accuracy": 0.0
                },
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "total_predictions": 0,
                "total_correct": 0,
                "accuracy_trend": "unknown",
                "generated_at": datetime.now().isoformat(),
                "source": ["historical_comparison", "prediction_analysis"]
            }
        
        # Extract prediction values and directions
        predicted_directions = [pred.get('direction', 'neutral') for pred in historical_forecasts]
        actual_directions = []
        for ret in actual_returns:
            if ret > 0.005:  # Up if > 0.5%
                actual_directions.append("up")
            elif ret < -0.005:  # Down if < -0.5%
                actual_directions.append("down")
            else:  # Neutral for small movements
                actual_directions.append("neutral")
        
        # Extract prediction values for MAE/RMSE
        predicted_values = [pred.get('expected_return', 0.0) for pred in historical_forecasts]
        
        # Calculate all metrics
        hit_rate = self.calculate_hit_rate(predicted_directions, actual_directions[:len(predicted_directions)])
        mae = self.calculate_mae(predicted_values, actual_returns[:len(predicted_values)])
        rmse = self.calculate_rmse(predicted_values, actual_returns[:len(predicted_values)])
        directional_accuracy = self.calculate_directional_accuracy(predicted_values, actual_returns[:len(predicted_values)])
        profit_factor = self.calculate_profit_factor(historical_forecasts, actual_returns)
        sharpe_ratio = self.calculate_sharpe_ratio_for_predictions(historical_forecasts, actual_returns)
        
        correct_predictions = sum(1 for pred, actual in zip(predicted_directions, actual_directions[:len(predicted_directions)]) if pred == actual)
        
        return {
            "hit_rate": hit_rate,
            "mae": mae,
            "rmse": rmse,
            "directional_accuracy": directional_accuracy,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "total_predictions": len(historical_forecasts),
            "total_correct": correct_predictions,
            "accuracy_trend": "stable",  # Would be calculated based on time-series in production
            "generated_at": datetime.now().isoformat(),
            "source": ["historical_comparison", "prediction_analysis", "ml_forecast_validation"]
        }


def validate_forecast_accuracy_vs_benchmark(forecast_metrics: Dict, benchmark_hit_rate: float = 0.52) -> Dict[str, any]:
    """
    Compare forecast accuracy to benchmark performance
    """
    performance_vs_benchmark = {
        "relative_performance": forecast_metrics.get("hit_rate", 0) - benchmark_hit_rate,
        "outperforms_benchmark": forecast_metrics.get("hit_rate", 0) > benchmark_hit_rate,
        "benchmark_used": benchmark_hit_rate,
        "improvement_percentage": ((forecast_metrics.get("hit_rate", 0) - benchmark_hit_rate) / benchmark_hit_rate * 100) if benchmark_hit_rate > 0 else 0
    }
    
    return performance_vs_benchmark