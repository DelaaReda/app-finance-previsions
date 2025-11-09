"""
Prediction Analyzer Service
Task: FC-API-032 - Prediction Accuracy Analytics
Author: ALEX-FINANCE-ANALYST-SUPERMAN-29
"""
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime
from pathlib import Path
import json

from backend.storage.base import save_json, load_json


class AccuracyMetrics:
    """
    Class to represent prediction accuracy metrics
    """
    def __init__(self, **kwargs):
        self.total_predictions = kwargs.get('total_predictions', 0)
        self.hit_rate = kwargs.get('hit_rate', 0.0)
        self.mse = kwargs.get('mse', 0.0)
        self.mae = kwargs.get('mae', 0.0)
        self.rmse = kwargs.get('rmse', 0.0)
        self.avg_confidence = kwargs.get('avg_confidence', 0.0)
        self.avg_return_if_correct = kwargs.get('avg_return_if_correct', 0.0)
        self.success_rate = kwargs.get('success_rate', 0.0)
        self.directional_accuracy = kwargs.get('directional_accuracy', 0.0)
        self.generated_at = kwargs.get('generated_at', datetime.utcnow().isoformat() + "Z")
        self.source = kwargs.get('source', [])
    
    def dict(self):
        return {
            'total_predictions': self.total_predictions,
            'hit_rate': self.hit_rate,
            'mse': self.mse,
            'mae': self.mae,
            'rmse': self.rmse,
            'avg_confidence': self.avg_confidence,
            'avg_return_if_correct': self.avg_return_if_correct,
            'success_rate': self.success_rate,
            'directional_accuracy': self.directional_accuracy,
            'generated_at': self.generated_at,
            'source': self.source
        }


class PredictionAnalyzerService:
    """
    Service for analyzing prediction accuracy and generating performance metrics.
    Compares historical predictions with actual outcomes to calculate hit rates,
    accuracy metrics, and other performance indicators.
    """
    
    def __init__(self):
        self.data_path = Path("data/analytics/prediction_accuracy.json")
        
    def calculate_accuracy_metrics(self, predictions: List[Dict], actuals: List[Dict], horizon: str = "all") -> AccuracyMetrics:
        """
        Calculate accuracy metrics comparing predictions with actual outcomes.
        
        Args:
            predictions: List of prediction dictionaries with 'ticker', 'predicted_return', 'confidence', 'date', 'horizon'
            actuals: List of actual outcome dictionaries with 'ticker', 'actual_return', 'date'
            horizon: Filter by prediction horizon ('1d', '1w', '1m', 'all')
            
        Returns:
            AccuracyMetrics object with calculated performance metrics
        """
        if not predictions or not actuals:
            return self._generate_empty_metrics()
        
        # Filter by horizon if specified
        if horizon != "all":
            predictions = [p for p in predictions if p.get('horizon') == horizon]
        
        # Match predictions with actuals by ticker and date
        matched_pairs = []
        for pred in predictions:
            pred_ticker = pred.get('ticker', '').upper()
            pred_date = pred.get('date', '')
            
            # Find corresponding actual outcome
            for actual in actuals:
                actual_ticker = actual.get('ticker', '').upper()
                actual_date = actual.get('date', '')
                
                # Match based on ticker and same date
                if pred_ticker == actual_ticker and pred_date == actual_date:
                    matched_pairs.append({
                        'prediction': pred,
                        'actual': actual
                    })
                    break  # Stop looking for this prediction once matched
        
        # Calculate performance metrics
        total_predictions = len(matched_pairs)
        directional_correct = 0
        squared_errors = []
        absolute_errors = []
        confidences = []
        returns_if_correct = []
        
        for pair in matched_pairs:
            pred = pair['prediction']
            actual = pair['actual']
            
            # Get values
            pred_return = pred.get('expected_return', pred.get('predicted_return', 0))
            actual_return = actual.get('actual_return', actual.get('return', 0))
            confidence = pred.get('confidence', pred.get('confidence_score', 0))
            
            # Directional accuracy (same sign)
            if (pred_return >= 0 and actual_return >= 0) or (pred_return < 0 and actual_return < 0):
                directional_correct += 1
            
            # Errors
            error = pred_return - actual_return
            squared_errors.append(error ** 2)
            absolute_errors.append(abs(error))
            
            # Confidence tracking
            if confidence is not None:
                confidences.append(confidence)
            
            # Return if correct (only track when direction was correct)
            if ((pred_return >= 0 and actual_return >= 0) or (pred_return < 0 and actual_return < 0)):
                returns_if_correct.append(actual_return)
        
        # Compute final metrics
        hit_rate = directional_correct / total_predictions if total_predictions > 0 else 0
        mse = sum(squared_errors) / len(squared_errors) if squared_errors else 0
        mae = sum(absolute_errors) / len(absolute_errors) if absolute_errors else 0
        rmse = (mse ** 0.5) if mse >= 0 else 0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        avg_return_if_correct = sum(returns_if_correct) / len(returns_if_correct) if returns_if_correct and len(returns_if_correct) > 0 else 0
        success_rate = len(returns_if_correct) / total_predictions if total_predictions > 0 else 0
        
        return AccuracyMetrics(
            total_predictions=total_predictions,
            hit_rate=hit_rate,
            mse=mse,
            mae=mae,
            rmse=rmse,
            avg_confidence=avg_confidence,
            avg_return_if_correct=avg_return_if_correct,
            success_rate=success_rate,
            directional_accuracy=hit_rate,
            generated_at=datetime.utcnow().isoformat() + "Z",
            source=["prediction_analyzer_service", "historical_comparison", "fc-api-032"]
        )
    
    def analyze_predictions(self, horizon: str = "all", tickers: Optional[List[str]] = None) -> Dict:
        """
        Main analysis function that loads historical data and generates accuracy report.
        
        Args:
            horizon: Prediction horizon to analyze ('1d', '1w', '1m', 'all')
            tickers: Specific tickers to analyze (None for all)
            
        Returns:
            Dictionary with complete analysis report
        """
        try:
            # Load historical predictions and actual outcomes 
            # from the existing data files
            forecasts_data = load_json("forecasts.json") or {}
            prices_data = load_json("prices_history.json") or {}  # This might not exist yet
            
            predictions = forecasts_data.get('rows', []) if isinstance(forecasts_data, dict) else []
            actuals = prices_data.get('rows', []) if isinstance(prices_data, dict) else []
            
            # If no prices_history.json exists, try to load from prices snapshots
            if not actuals:
                prices_data = load_json("stocks_prices.json") or {}
                actuals = prices_data.get('rows', []) if isinstance(prices_data, dict) else []
            
            # Filter by tickers if specified
            if tickers:
                ticker_set = {t.upper() for t in tickers}
                predictions = [p for p in predictions if p.get('ticker', '').upper() in ticker_set]
                actuals = [a for a in actuals if a.get('ticker', '').upper() in ticker_set]
            
            # Calculate accuracy metrics
            metrics = self.calculate_accuracy_metrics(predictions, actuals, horizon)
            
            # Prepare detailed report
            report = {
                "accuracy_metrics": metrics.__dict__,
                "summary": {
                    "total_predictions_analyzed": metrics.total_predictions,
                    "hit_rate_percentage": round(metrics.hit_rate * 100, 2),
                    "average_confidence": round(metrics.avg_confidence, 4),
                    "average_absolute_error": round(metrics.mae, 4),
                    "directional_accuracy": round(metrics.directional_accuracy * 100, 2),
                    "rmse": round(metrics.rmse, 4),
                    "success_rate": round(metrics.success_rate, 4)
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "parameters": {
                    "horizon": horizon,
                    "tickers": tickers
                },
                "source": ["prediction_analyzer_service", "accuracy_report", "fc-api-032"]
            }
            
            # Save to persistent storage
            save_json("prediction_accuracy", report, source=["prediction_analyzer_service", "fc-api-032"])
            
            return report
        except Exception as e:
            print(f"Error in prediction analysis: {str(e)}")
            # Return fallback structure to maintain never-empty contract
            return {
                "accuracy_metrics": self._generate_empty_metrics().__dict__,
                "summary": {
                    "total_predictions_analyzed": 0,
                    "hit_rate_percentage": 0.0,
                    "average_confidence": 0.0,
                    "average_absolute_error": 0.0,
                    "directional_accuracy": 0.0,
                    "rmse": 0.0,
                    "success_rate": 0.0
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "parameters": {
                    "horizon": horizon,
                    "tickers": tickers
                },
                "source": ["prediction_analyzer_service", "error_fallback", "fc-api-032"],
                "error": str(e),
                "message": "Prediction analysis failed but fallback data returned to maintain never-empty contract"
            }
    
    def _generate_empty_metrics(self) -> AccuracyMetrics:
        """Generate empty metrics to maintain never-empty contract."""
        return AccuracyMetrics(
            total_predictions=0,
            hit_rate=0.0,
            mse=0.0,
            mae=0.0,
            rmse=0.0,
            avg_confidence=0.0,
            avg_return_if_correct=0.0,
            success_rate=0.0,
            directional_accuracy=0.0,
            generated_at=datetime.utcnow().isoformat() + "Z",
            source=["prediction_analyzer_service", "empty_fallback", "fc-api-032"]
        )


# Singleton instance
prediction_analyzer_service = PredictionAnalyzerService()