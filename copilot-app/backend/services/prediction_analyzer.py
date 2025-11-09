"""
Prediction Analytics Service
Task: FC-API-031 - Prediction Accuracy Analytics
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from models.accuracy_metrics import accuracy_metrics_calculator, calculate_accuracy_metrics
from storage.io import load_json
from services.cache_layer import load_or_compute


class PredictionAnalyzerService:
    """
    Service for analyzing prediction accuracy and generating performance reports
    """
    
    def __init__(self):
        self.calculator = accuracy_metrics_calculator
    
    def get_prediction_accuracy_report(self,
                                     tickers: Optional[List[str]] = None,
                                     horizon: Optional[str] = None,
                                     days_back: int = 30,
                                     model_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive prediction accuracy report
        
        Args:
            tickers: Optional list of tickers to analyze
            horizon: Optional horizon filter (1d, 1w, 1m, etc.)
            days_back: Number of days of historical data to analyze
            model_version: Optional model version filter
        
        Returns:
            Comprehensive prediction accuracy report
        """
        def compute_accuracy_report():
            """
            Compute fresh accuracy metrics from stored prediction and actual data
            """
            try:
                # Load prediction history data
                predictions_data = load_json("predictions_history") or {}
                
                # This might be in different formats depending on how it's stored
                predictions_list = []
                
                # Try different possible structures for predictions
                if "predictions" in predictions_data:
                    predictions_list = predictions_data["predictions"]
                elif "data" in predictions_data:
                    if "predictions" in predictions_data["data"]:
                        predictions_list = predictions_data["data"]["predictions"]
                    elif "rows" in predictions_data["data"]:
                        predictions_list = predictions_data["data"]["rows"]
                    else:
                        predictions_list = predictions_data["data"] if isinstance(predictions_data["data"], list) else []
                elif "rows" in predictions_data:
                    predictions_list = predictions_data["rows"]
                else:
                    predictions_list = []  # Default to empty if no known structure found
                
                # Filter predictions based on criteria if specified
                filtered_predictions = []
                
                for pred in predictions_list:
                    include_pred = True
                    
                    # Apply ticker filter
                    if tickers and pred.get("ticker"):
                        if pred["ticker"].upper() not in [t.upper() for t in tickers]:
                            include_pred = False
                    elif tickers and pred.get("symbol"):
                        if pred["symbol"].upper() not in [t.upper() for t in tickers]:
                            include_pred = False
                    
                    # Apply horizon filter
                    if horizon and pred.get("horizon") != horizon:
                        include_pred = False
                    
                    # Apply date filter
                    if pred.get("predicted_at") or pred.get("timestamp"):
                        pred_time_str = pred.get("predicted_at") or pred.get("timestamp")
                        try:
                            from datetime import datetime
                            pred_time = datetime.fromisoformat(pred_time_str.replace('Z', '+00:00'))
                            cutoff_time = datetime.utcnow() - timedelta(days=days_back)
                            if pred_time < cutoff_time:
                                include_pred = False
                        except:
                            # If date parsing fails, include the prediction anyway
                            pass
                    
                    # Apply model version filter
                    if model_version and pred.get("model_version") != model_version:
                        include_pred = False
                    
                    if include_pred:
                        filtered_predictions.append(pred)
                
                # Load actual outcomes data to compare against predictions
                actuals_data = load_json("actual_outcomes") or {}
                
                # This would typically contain the actual results after the prediction horizon
                actuals_map = {}
                if "outcomes" in actuals_data:
                    outcomes = actuals_data["outcomes"]
                    for outcome in outcomes:
                        ticker = outcome.get("ticker") or outcome.get("symbol", "UNKNOWN")
                        timestamp = outcome.get("timestamp") or outcome.get("date", "")
                        actuals_map[f"{ticker}_{timestamp}"] = outcome
                elif "data" in actuals_data:
                    outcomes = actuals_data["data"]
                    for outcome in outcomes:
                        ticker = outcome.get("ticker") or outcome.get("symbol", "UNKNOWN")
                        timestamp = outcome.get("timestamp") or outcome.get("date", "")
                        actuals_map[f"{ticker}_{timestamp}"] = outcome
                elif isinstance(actuals_data, list):
                    for outcome in actuals_data:
                        ticker = outcome.get("ticker") or outcome.get("symbol", "UNKNOWN") 
                        timestamp = outcome.get("timestamp") or outcome.get("date", "")
                        actuals_map[f"{ticker}_{timestamp}"] = outcome
                # If no actuals found, the system will proceed with empty actuals map
                
                # Match predictions to actual outcomes
                prediction_actual_pairs = []
                
                for pred in filtered_predictions:
                    pred_ticker = pred.get("ticker") or pred.get("symbol", "UNKNOWN")
                    pred_timestamp = pred.get("predicted_at") or pred.get("timestamp", "")
                    
                    # Look for matching actual outcome
                    actual_key_exact = f"{pred_ticker}_{pred_timestamp}"
                    actual_key_date_only = f"{pred_ticker}_{pred_timestamp.split('T')[0] if 'T' in pred_timestamp else pred_timestamp}"
                    
                    actual_outcome = None
                    if actual_key_exact in actuals_map:
                        actual_outcome = actuals_map[actual_key_exact]
                    elif actual_key_date_only in actuals_map:
                        actual_outcome = actuals_map[actual_key_date_only]
                    else:
                        # If no exact match found, try to find by ticker and approximate date window
                        for key, value in actuals_map.items():
                            if pred_ticker in key and (pred_timestamp.split('T')[0] in key or 
                                                      (datetime.fromisoformat(pred_timestamp.replace('Z', '+00:00')) - 
                                                       datetime.fromisoformat(value.get('timestamp', value.get('date', datetime.min.isoformat() + '+00:00')))).days <= 7):
                                actual_outcome = value
                                break
                    
                    if actual_outcome:
                        # Extract predicted and actual values for comparison
                        predicted_return = pred.get("predicted_return") or pred.get("expected_return") or pred.get("return", 0.0)
                        predicted_value = pred.get("predicted_value") or pred.get("expected_value", 0.0)
                        actual_return = actual_outcome.get("actual_return") or actual_outcome.get("return", 0.0)
                        actual_value = actual_outcome.get("actual_value") or actual_outcome.get("value", 0.0)
                        
                        # Use available values to form prediction-actual pairs
                        pair = {
                            "ticker": pred_ticker,
                            "horizon": pred.get("horizon", "unknown"),
                            "predicted_return": predicted_return,
                            "actual_return": actual_return,
                            "predicted_value": predicted_value,
                            "actual_value": actual_value,
                            "confidence": pred.get("confidence", 0.5),
                            "model_version": pred.get("model_version", "unknown"),
                            "predicted_at": pred_timestamp,
                            "actualized_at": actual_outcome.get("timestamp") or actual_outcome.get("date", "unknown")
                        }
                        
                        prediction_actual_pairs.append(pair)
                
                # Calculate overall metrics
                if prediction_actual_pairs:
                    predicted_returns = [p["predicted_return"] for p in prediction_actual_pairs]
                    actual_returns = [p["actual_return"] for p in prediction_actual_pairs]
                    
                    overall_metrics = self.calculator.calculate_comprehensive_metrics(predicted_returns, actual_returns)
                    
                    # Calculate metrics by ticker if multiple tickers
                    ticker_metrics = {}
                    if tickers:
                        for ticker in tickers:
                            ticker_pairs = [p for p in prediction_actual_pairs if p["ticker"].upper() == ticker.upper()]
                            if ticker_pairs:
                                ticker_predicted_returns = [p["predicted_return"] for p in ticker_pairs]
                                ticker_actual_returns = [p["actual_return"] for p in ticker_pairs]
                                ticker_metrics[ticker.upper()] = self.calculator.calculate_comprehensive_metrics(
                                    ticker_predicted_returns, 
                                    ticker_actual_returns
                                )
                    
                    # Calculate metrics by horizon
                    horizon_metrics = {}
                    horizons = set([p["horizon"] for p in prediction_actual_pairs])
                    for h in horizons:
                        horizon_pairs = [p for p in prediction_actual_pairs if p["horizon"] == h]
                        if horizon_pairs:
                            horizon_predicted_returns = [p["predicted_return"] for p in horizon_pairs]
                            horizon_actual_returns = [p["actual_return"] for p in horizon_pairs]
                            horizon_metrics[h] = self.calculator.calculate_comprehensive_metrics(
                                horizon_predicted_returns,
                                horizon_actual_returns
                            )
                    
                    report = {
                        "overall_metrics": overall_metrics,
                        "by_ticker": ticker_metrics,
                        "by_horizon": horizon_metrics,
                        "prediction_count": len(prediction_actual_pairs),
                        "analysis_period": {
                            "days_back": days_back,
                            "start_date": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z",
                            "end_date": datetime.utcnow().isoformat() + "Z"
                        },
                        "filters_applied": {
                            "tickers": tickers,
                            "horizon": horizon,
                            "model_version": model_version,
                            "days_back": days_back
                        },
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["prediction_analyzer_service", "accuracy_calculation", "fc-api-031"]
                    }
                else:
                    # If no prediction-actual pairs available, return empty metrics with explanation
                    report = {
                        "overall_metrics": self.calculator._get_empty_metrics(),
                        "by_ticker": {},
                        "by_horizon": {},
                        "prediction_count": 0,
                        "analysis_period": {
                            "days_back": days_back,
                            "start_date": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z",
                            "end_date": datetime.utcnow().isoformat() + "Z"
                        },
                        "filters_applied": {
                            "tickers": tickers,
                            "horizon": horizon,
                            "model_version": model_version,
                            "days_back": days_back
                        },
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["prediction_analyzer_service", "no_data_fallback", "fc-api-031"],
                        "message": "No prediction-actual pairs found for the specified criteria. This is expected if no historical predictions have been matched to outcomes yet. The system will continue to build this history over time."
                    }
                
                return report
                
            except Exception as e:
                print(f"Error in prediction accuracy calculation: {str(e)}")
                
                # Return fallback structure to maintain never-empty contract
                return {
                    "overall_metrics": self.calculator._get_empty_metrics(),
                    "by_ticker": {},
                    "by_horizon": {},
                    "prediction_count": 0,
                    "analysis_period": {
                        "days_back": days_back,
                        "start_date": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z",
                        "end_date": datetime.utcnow().isoformat() + "Z"
                    },
                    "filters_applied": {
                        "tickers": tickers,
                        "horizon": horizon,
                        "model_version": model_version,
                        "days_back": days_back
                    },
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["prediction_analyzer_service", "error_fallback", "fc-api-031"],
                    "error": str(e),
                    "message": "Prediction accuracy calculation failed but fallback report generated to maintain never-empty contract"
                }
        
        # Use cache layer to serve latest available data, compute fresh if none available
        cache_key = f"prediction_accuracy_{'_'.join(sorted([t.upper() for t in tickers or []]))}_{horizon or 'all'}_{days_back}d_{model_version or 'all'}"
        accuracy_report = load_or_compute(
            key=cache_key,
            compute_fn=compute_accuracy_report,
            source=["prediction_analyzer_service", "accuracy_calculation", "fc-api-031"]
        )
        
        return {
            "ok": True,  # Always maintain never-empty contract
            "data": accuracy_report,
            "freshness": accuracy_report.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
    
    def get_prediction_trend_analysis(self, 
                                    ticker: Optional[str] = None,
                                    days_back: int = 90,
                                    granularity: str = "weekly") -> Dict[str, Any]:
        """
        Get trend analysis of prediction accuracy over time
        
        Args:
            ticker: Optional ticker to analyze
            days_back: Number of days to analyze
            granularity: Granularity for trend analysis (daily, weekly, monthly)
        
        Returns:
            Prediction accuracy trend analysis
        """
        try:
            # For now, return a simulation of how this would work
            # In a real implementation, this would aggregate metrics by time period
            return {
                "trend_analysis": {
                    "period": f"last_{days_back}_days",
                    "granularity": granularity,
                    "data_points": [],
                    "summary": {
                        "improvement_trend": "unknown",  # Would be calculated based on data
                        "consistency_score": 0.0,  # Would be calculated based on data
                        "recent_performance_change": 0.0  # Would be calculated based on data
                    },
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["prediction_analyzer_service", "trend_analysis", "fc-api-031"],
                    "message": "Trend analysis not yet implemented in data but structure prepared for future integration"
                },
                "ok": True,
                "data": {},
                "freshness": datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            return {
                "trend_analysis": {
                    "error": str(e),
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["prediction_analyzer_service", "trend_analysis", "fc-api-031"],
                    "message": "Trend analysis temporarily unavailable but fallback returned to maintain never-empty contract"
                },
                "ok": True,
                "data": {},
                "freshness": "error"
            }
    
    def get_model_comparison_report(self, 
                                  model_versions: List[str],
                                  tickers: Optional[List[str]] = None,
                                  days_back: int = 30) -> Dict[str, Any]:
        """
        Compare different model versions' prediction accuracy
        
        Args:
            model_versions: List of model versions to compare
            tickers: Optional list of tickers to analyze
            days_back: Number of days to analyze
        
        Returns:
            Comparison report between different model versions
        """
        try:
            comparison_results = {}
            
            for version in model_versions:
                # Get accuracy report for each model version
                report = self.get_prediction_accuracy_report(
                    tickers=tickers,
                    model_version=version,
                    days_back=days_back
                )
                comparison_results[version] = report["data"]["overall_metrics"]
            
            comparison_summary = {
                "best_model_by_metric": {},
                "model_rankings": {},
                "comparison_metrics": ["hit_rate", "accuracy", "precision", "recall", "f1_score", "sharpe_ratio"]
            }
            
            # Calculate which model is best for each metric
            for metric in comparison_summary["comparison_metrics"]:
                sorted_models = sorted(
                    comparison_results.items(),
                    key=lambda x: x[1].get(metric, 0),
                    reverse=True  # Higher is better for most metrics
                )
                comparison_summary["best_model_by_metric"][metric] = sorted_models[0][0] if sorted_models else "unknown"
                
                # Create rankings
                comparison_summary["model_rankings"][metric] = [
                    {"model": model[0], "value": model[1].get(metric, 0), "rank": i+1}
                    for i, model in enumerate(sorted_models)
                ]
            
            result = {
                "model_comparisons": comparison_results,
                "comparison_summary": comparison_summary,
                "compared_versions": model_versions,
                "analysis_period": {
                    "days_back": days_back,
                    "start_date": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z",
                    "end_date": datetime.utcnow().isoformat() + "Z"
                },
                "filters_applied": {"tickers": tickers},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["prediction_analyzer_service", "model_comparison", "fc-api-031"]
            }
            
            return {
                "ok": True,
                "data": result,
                "freshness": result["generated_at"]
            }
            
        except Exception as e:
            return {
                "ok": True,  # Maintain never-empty contract
                "data": {
                    "model_comparisons": {},
                    "comparison_summary": {},
                    "compared_versions": model_versions,
                    "analysis_period": {
                        "days_back": days_back,
                        "start_date": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z",
                        "end_date": datetime.utcnow().isoformat() + "Z"
                    },
                    "filters_applied": {"tickers": tickers},
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["prediction_analyzer_service", "model_comparison", "fc-api-031"],
                    "error": str(e),
                    "message": "Model comparison failed but fallback returned to maintain never-empty contract"
                },
                "freshness": "error"
            }


# Global instance
prediction_analyzer_service = PredictionAnalyzerService()

# Convenience functions
def get_prediction_accuracy(tickers: Optional[List[str]] = None, 
                          horizon: Optional[str] = None,
                          days_back: int = 30,
                          model_version: Optional[str] = None):
    """
    Get prediction accuracy report
    """
    return prediction_analyzer_service.get_prediction_accuracy_report(tickers, horizon, days_back, model_version)

def get_prediction_trends(ticker: Optional[str] = None, 
                        days_back: int = 90,
                        granularity: str = "weekly"):
    """
    Get prediction accuracy trends
    """
    return prediction_analyzer_service.get_prediction_trend_analysis(ticker, days_back, granularity)

def compare_prediction_models(model_versions: List[str],
                           tickers: Optional[List[str]] = None,
                           days_back: int = 30):
    """
    Compare different model versions
    """
    return prediction_analyzer_service.get_model_comparison_report(model_versions, tickers, days_back)