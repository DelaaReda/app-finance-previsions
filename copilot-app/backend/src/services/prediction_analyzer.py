"""
Prediction Analyzer Service
Task: FC-API-032 - Prediction Accuracy Analytics
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime
from pathlib import Path
from backend.storage.base import load_json, save_json


class PredictionAnalyzerService:
    """
    Service for analyzing prediction accuracy and generating performance metrics.
    Compares historical predictions with actual outcomes to calculate hit rates,
    accuracy metrics, and other performance indicators.
    """
    
    def __init__(self):
        self.data_path = Path("data/analytics/prediction_accuracy.json")
        
    def calculate_accuracy_metrics(self, predictions: List[Dict], actuals: List[Dict], horizon: str = "all") -> Dict:
        """
        Calculate accuracy metrics comparing predictions with actual outcomes.
        
        Args:
            predictions: List of prediction dictionaries with 'ticker', 'predicted_return', 'confidence', 'date', 'horizon'
            actuals: List of actual outcome dictionaries with 'ticker', 'actual_return', 'date'
            horizon: Filter by prediction horizon ('1d', '1w', '1m', 'all')
            
        Returns:
            Dictionary with calculated performance metrics
        """
        if not predictions or not actuals:
            return self._generate_empty_metrics()
        
        # Filter by horizon if specified
        if horizon != "all":
            predictions = [p for p in predictions if p.get('horizon') == horizon]
        
        # Match predictions with actuals by ticker and date proximity
        matched_pairs = []
        for pred in predictions:
            pred_ticker = pred.get('ticker', '').upper()
            pred_date = pred.get('date', pred.get('calculation_timestamp', ''))
            
            # Find corresponding actual outcome
            for actual in actuals:
                actual_ticker = actual.get('ticker', '').upper()
                actual_date = actual.get('date', actual.get('actual_timestamp', ''))
                
                try:
                    # Match based on ticker and date proximity
                    if pred_ticker == actual_ticker and pred_date == actual_date:
                        matched_pairs.append({
                            'prediction': pred,
                            'actual': actual,
                        })
                        break  # Stop looking once matched
                except Exception:
                    # If date parsing fails, continue
                    continue
        
        if not matched_pairs:
            return self._generate_empty_metrics()
        
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
            
            # Convert to float if string
            try:
                if isinstance(pred_return, str):
                    pred_return = float(pred_return)
                if isinstance(actual_return, str):
                    actual_return = float(actual_return)
                if isinstance(confidence, str):
                    confidence = float(confidence)
            except (ValueError, TypeError):
                # If conversion fails, continue with defaults
                continue
            
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
            if ((pred_return >= 0 and actual_return >= 0) or (pred_return < 0 and actual_return < 0)) and actual_return is not None:
                returns_if_correct.append(actual_return)
        
        # Compute final metrics
        hit_rate = directional_correct / total_predictions if total_predictions > 0 else 0
        mse = sum(squared_errors) / len(squared_errors) if squared_errors else 0
        mae = sum(absolute_errors) / len(absolute_errors) if absolute_errors else 0
        rmse = np.sqrt(mse) if mse >= 0 else 0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        avg_return_if_correct = sum(returns_if_correct) / len(returns_if_correct) if returns_if_correct and len(returns_if_correct) > 0 else 0
        success_rate = len(returns_if_correct) / total_predictions if total_predictions > 0 else 0
        
        return {
            "total_predictions": total_predictions,
            "hit_rate": hit_rate,
            "mse": mse,
            "mae": mae,
            "rmse": rmse,
            "avg_confidence": avg_confidence,
            "avg_return_if_correct": avg_return_if_correct,
            "success_rate": success_rate,
            "directional_accuracy": hit_rate,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["prediction_analyzer_service", "historical_comparison", "fc-api-032"]
        }
    
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
            forecasts_data = load_json("forecasts.json") or {}
            actuals_data = load_json("prices_history.json") or {}  # Historical price changes
            
            predictions = forecasts_data.get('rows', []) if isinstance(forecasts_data, dict) and 'rows' in forecasts_data else []
            actuals = actuals_data.get('rows', []) if isinstance(actuals_data, dict) and 'rows' in actuals_data else []
            
            # If no prices_history.json exists, try alternative data sources
            if not actuals:
                actuals_data = load_json("stocks_prices.json") or {}
                if isinstance(actuals_data, dict) and 'rows' in actuals_data:
                    actuals = actuals_data['rows']
                else:
                    # Create mock actuals from forecasts if needed (fallback)
                    actuals = []
            
            # Filter by tickers if specified
            if tickers:
                ticker_set = {t.upper() for t in tickers}
                predictions = [p for p in predictions if p.get('ticker', '').upper() in ticker_set]
                actuals = [a for a in actuals if a.get('ticker', '').upper() in ticker_set]
            
            # Calculate overall accuracy metrics
            overall_metrics = self.calculate_accuracy_metrics(predictions, actuals, horizon)
            
            # Prepare detailed report
            report = {
                "accuracy_metrics": overall_metrics,
                "summary": {
                    "total_predictions_analyzed": overall_metrics["total_predictions"],
                    "hit_rate_percentage": round(overall_metrics["hit_rate"] * 100, 2),
                    "average_confidence": round(overall_metrics["avg_confidence"], 4),
                    "average_absolute_error": round(overall_metrics["mae"], 4),
                    "directional_accuracy": round(overall_metrics["directional_accuracy"] * 100, 2),
                    "success_rate": round(overall_metrics["success_rate"], 4)
                },
                "by_horizon": self._analyze_by_horizon(predictions, actuals) if horizon == "all" else {},
                "by_asset": self._analyze_by_asset(predictions, actuals, horizon),
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
                "accuracy_metrics": self._generate_empty_metrics(),
                "summary": {
                    "total_predictions_analyzed": 0,
                    "hit_rate_percentage": 0.0,
                    "average_confidence": 0.0,
                    "average_absolute_error": 0.0,
                    "directional_accuracy": 0.0,
                    "success_rate": 0.0
                },
                "by_horizon": {},
                "by_asset": {},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "parameters": {
                    "horizon": horizon,
                    "tickers": tickers
                },
                "source": ["prediction_analyzer_service", "error_fallback", "fc-api-032"],
                "error": str(e),
                "message": "Prediction analysis failed but fallback data returned to maintain never-empty contract"
            }
    
    def _analyze_by_horizon(self, predictions: List[Dict], actuals: List[Dict]) -> Dict:
        """Analyze accuracy by different prediction horizons."""
        horizons = ['1d', '1w', '1m', '3m']
        results = {}
        
        for horizon in horizons:
            horizon_predictions = [p for p in predictions if p.get('horizon') == horizon]
            if horizon_predictions:
                metrics = self.calculate_accuracy_metrics(horizon_predictions, actuals, horizon)
                results[horizon] = {
                    "hit_rate": metrics["hit_rate"],
                    "mae": metrics["mae"],
                    "avg_confidence": metrics["avg_confidence"],
                    "count": metrics["total_predictions"]
                }
        
        return results
    
    def _analyze_by_asset(self, predictions: List[Dict], actuals: List[Dict], horizon: str) -> Dict:
        """Analyze accuracy by different assets."""
        # Get unique tickers
        tickers = list(set(p.get('ticker', '').upper() for p in predictions if p.get('ticker')))
        results = {}
        
        for ticker in tickers:
            ticker_predictions = [p for p in predictions if p.get('ticker', '').upper() == ticker]
            if ticker_predictions:
                metrics = self.calculate_accuracy_metrics(ticker_predictions, actuals, horizon)
                results[ticker] = {
                    "hit_rate": metrics["hit_rate"],
                    "mae": metrics["mae"],
                    "avg_confidence": metrics["avg_confidence"],
                    "count": metrics["total_predictions"]
                }
        
        return results
    
    def _generate_empty_metrics(self) -> Dict:
        """Generate empty metrics to maintain never-empty contract."""
        return {
            "total_predictions": 0,
            "hit_rate": 0.0,
            "mse": 0.0,
            "mae": 0.0,
            "rmse": 0.0,
            "avg_confidence": 0.0,
            "avg_return_if_correct": 0.0,
            "success_rate": 0.0,
            "directional_accuracy": 0.0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["prediction_analyzer_service", "empty_fallback", "fc-api-032"]
        }


# Singleton instance
prediction_analyzer_service = PredictionAnalyzerService()