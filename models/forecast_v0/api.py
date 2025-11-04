"""
Metrics Logging and Inference API for Forecasting Engine
Part of the Finance Copilot forecasting engine
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path
import threading
import queue

from model import HybridForecastModel
from market_embedding import MarketEmbedding
from llm_scoring import LLMScoringLayer
from utils import ModelRegistry, save_forecast_results

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('forecast_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MetricsLogger:
    """
    Metrics logging system for tracking model performance and forecast accuracy
    """
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.metrics_buffer = []
        
    def log_prediction(self, 
                      ticker: str, 
                      forecast: Dict[str, Any], 
                      actual: Optional[float] = None,
                      timestamp: datetime = None):
        """
        Log a prediction with optional actual value for accuracy tracking
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        metrics = {
            "timestamp": timestamp.isoformat(),
            "ticker": ticker,
            "forecast": forecast,
            "actual": actual,
            "forecast_error": None,
            "accuracy": None
        }
        
        # Calculate error metrics if actual value provided
        if actual is not None and forecast.get('predictions', {}).get('combined') is not None:
            forecast_value = forecast['predictions']['combined']
            error = actual - forecast_value
            metrics["forecast_error"] = error
            metrics["accuracy"] = 1 / (1 + abs(error))  # Simple accuracy metric
        
        self.metrics_buffer.append(metrics)
        
        # Write to file periodically
        if len(self.metrics_buffer) >= 10:  # Batch write every 10 entries
            self._flush_buffer()
    
    def _flush_buffer(self):
        """Write buffered metrics to file"""
        if not self.metrics_buffer:
            return
            
        filename = self.log_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(filename, 'a') as f:
            for metric in self.metrics_buffer:
                f.write(json.dumps(metric) + '\n')
        
        self.metrics_buffer = []
    
    def get_performance_metrics(self, ticker: str = None) -> Dict[str, Any]:
        """
        Calculate performance metrics for a specific ticker or overall
        """
        # Read all metric files for today
        today_file = self.log_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        if not today_file.exists():
            return {"error": "No metrics data available"}
        
        metrics_data = []
        with open(today_file, 'r') as f:
            for line in f:
                metric = json.loads(line)
                if ticker is None or metric['ticker'] == ticker:
                    metrics_data.append(metric)
        
        if not metrics_data:
            return {"error": "No metrics data for specified ticker"}
        
        # Calculate metrics
        errors = [m['forecast_error'] for m in metrics_data if m['forecast_error'] is not None]
        accuracies = [m['accuracy'] for m in metrics_data if m['accuracy'] is not None]
        
        if not errors:
            return {"message": "No error data available for accuracy calculation"}
        
        performance_metrics = {
            "total_predictions": len(metrics_data),
            "mean_error": np.mean(errors) if errors else 0,
            "mean_absolute_error": np.mean(np.abs(errors)) if errors else 0,
            "std_error": np.std(errors) if errors else 0,
            "accuracy_mean": np.mean(accuracies) if accuracies else 0,
            "accuracy_std": np.std(accuracies) if accuracies else 0,
            "direction_accuracy": self._calculate_direction_accuracy(metrics_data),
            "timestamp": datetime.now().isoformat()
        }
        
        return performance_metrics
    
    def _calculate_direction_accuracy(self, metrics_data: List[Dict]) -> float:
        """
        Calculate accuracy of direction predictions
        """
        correct_directions = 0
        total = 0
        
        for metric in metrics_data:
            if (metric['actual'] is not None and 
                metric['forecast'].get('predictions', {}).get('combined') is not None):
                
                actual_direction = 1 if metric['actual'] > metric['forecast']['metrics']['current_price'] else -1
                forecast_direction = 1 if metric['forecast'].get('expected_return', 0) > 0 else -1
                
                if actual_direction == forecast_direction:
                    correct_directions += 1
                total += 1
        
        return correct_directions / total if total > 0 else 0
    
    def save_model_performance(self, model_name: str, performance_data: Dict[str, Any]):
        """
        Save model performance to the registry
        """
        registry = ModelRegistry()
        registry.register_model(
            model_name=model_name,
            model_path=f"./models/forecast_v0/saved_models/{model_name}.pkl",
            performance_metrics=performance_data,
            features_used=["returns", "sma_5", "sma_20", "rsi", "volatility"],
            training_data_info={"start_date": "2022-01-01", "end_date": datetime.now().isoformat()}
        )


class ForecastAPI:
    """
    Inference API for the forecasting engine
    """
    
    def __init__(self):
        self.model = None
        self.market_embedding = None
        self.llm_scoring = None
        self.metrics_logger = MetricsLogger()
        self.model_registry = ModelRegistry()
        
        # Thread-safe queue for async processing
        self.request_queue = queue.Queue()
        self.response_cache = {}
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all forecasting components"""
        try:
            self.model = HybridForecastModel(arima_order=(2, 1, 2))
            logger.info("Hybrid forecast model initialized")
        except Exception as e:
            logger.error(f"Failed to initialize forecast model: {e}")
            self.model = None
        
        try:
            self.market_embedding = MarketEmbedding(dimensions=10)
            logger.info("Market embedding initialized")
        except Exception as e:
            logger.error(f"Failed to initialize market embedding: {e}")
            self.market_embedding = None
        
        try:
            self.llm_scoring = LLMScoringLayer()
            logger.info("LLM scoring layer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize LLM scoring: {e}")
            self.llm_scoring = None
    
    def predict(self, 
                ticker: str, 
                data: pd.DataFrame, 
                include_llm_analysis: bool = True) -> Dict[str, Any]:
        """
        Generate prediction for a given ticker
        
        Args:
            ticker: Stock ticker symbol
            data: Historical price data
            include_llm_analysis: Whether to include LLM analysis
            
        Returns:
            Prediction result with all relevant information
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if data.empty:
                raise ValueError("Input data is empty")
            
            if 'close' not in data.columns:
                raise ValueError("Data must contain 'close' column")
            
            # Generate base forecast using the hybrid model
            if self.model is None:
                raise ValueError("Forecast model not initialized")
            
            # Fit and predict
            self.model.fit(data, target_col='close')
            base_forecast = self.model.predict(data, steps=1, target_col='close')
            
            # Add ticker and horizon info
            base_forecast['ticker'] = ticker
            base_forecast['horizon'] = '1d'
            base_forecast['processing_time'] = time.time() - start_time
            
            # Add market embedding if available
            if self.market_embedding:
                try:
                    self.market_embedding.fit(data, method='correlation')
                    base_forecast['market_context'] = {
                        'embeddings': {col: str(data[col].iloc[-1]) for col in data.select_dtypes(include=[np.number]).columns if col != 'close'}
                    }
                except Exception as e:
                    logger.warning(f"Error in market embedding: {e}")
                    base_forecast['market_context'] = {}
            
            # Enhance with LLM analysis if requested and available
            enhanced_forecast = base_forecast.copy()
            if include_llm_analysis and self.llm_scoring:
                try:
                    # Prepare market context for LLM
                    market_context = {
                        "volatility": float(data['close'].pct_change().rolling(20).std().iloc[-1]),
                        "trend": "up" if data['close'].iloc[-1] > data['close'].iloc[-5] else "down",
                        "volume_trend": "increasing" if data['volume'].iloc[-1] > data['volume'].rolling(5).mean().iloc[-1] else "decreasing"
                    }
                    
                    enhanced_forecast = self.llm_scoring.enhance_forecast(base_forecast, market_context)
                except Exception as e:
                    logger.error(f"Error in LLM enhancement: {e}")
                    # Fallback to base forecast
                    enhanced_forecast = base_forecast
                    enhanced_forecast['llm_error'] = str(e)
            
            # Log the prediction
            self.metrics_logger.log_prediction(ticker, enhanced_forecast)
            
            # Add metadata
            enhanced_forecast['api_response_time'] = time.time() - start_time
            enhanced_forecast['timestamp'] = datetime.now().isoformat()
            
            return enhanced_forecast
            
        except Exception as e:
            logger.error(f"Prediction error for {ticker}: {e}")
            # Return error response
            return {
                "error": str(e),
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
    
    def batch_predict(self, predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Perform batch predictions
        
        Args:
            predictions: List of prediction requests with 'ticker' and 'data' keys
            
        Returns:
            List of prediction results
        """
        results = []
        for req in predictions:
            ticker = req.get('ticker')
            data = req.get('data')
            include_llm = req.get('include_llm_analysis', True)
            
            if isinstance(data, dict):
                data = pd.DataFrame(data)
            
            result = self.predict(ticker, data, include_llm)
            results.append(result)
        
        return results
    
    def get_performance_metrics(self, ticker: str = None) -> Dict[str, Any]:
        """
        Get performance metrics for the forecasting model
        """
        return self.metrics_logger.get_performance_metrics(ticker)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model state
        """
        return {
            "model_initialized": self.model is not None,
            "market_embedding_initialized": self.market_embedding is not None,
            "llm_scoring_initialized": self.llm_scoring is not None,
            "timestamp": datetime.now().isoformat()
        }


# Global API instance
forecast_api = ForecastAPI()


def get_forecast(ticker: str, data: pd.DataFrame, include_llm_analysis: bool = True) -> Dict[str, Any]:
    """
    Get forecast for a ticker using the API
    
    Args:
        ticker: Stock ticker symbol
        data: Historical price data
        include_llm_analysis: Whether to include LLM analysis
        
    Returns:
        Forecast result
    """
    return forecast_api.predict(ticker, data, include_llm_analysis)


def get_batch_forecasts(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get forecasts for multiple tickers at once
    
    Args:
        predictions: List of prediction requests
        
    Returns:
        List of forecast results
    """
    return forecast_api.batch_predict(predictions)


def get_performance_metrics(ticker: str = None) -> Dict[str, Any]:
    """
    Get performance metrics for the forecasting model
    
    Args:
        ticker: Optional ticker to get metrics for specific ticker
        
    Returns:
        Performance metrics
    """
    return forecast_api.get_performance_metrics(ticker)


def get_model_info() -> Dict[str, Any]:
    """
    Get information about the model state
    
    Returns:
        Model information
    """
    return forecast_api.get_model_info()


def example_usage_api():
    """
    Example of how to use the Forecast API
    """
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq='D')
    
    # Generate realistic price data
    returns = np.random.normal(0.0005, 0.02, 252)
    prices = [100]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    df = pd.DataFrame({
        'date': dates,
        'open': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, len(prices))
    })
    
    print("MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7: Testing Forecast API...")
    print(f"Sample data shape: {df.shape}")
    
    # Single prediction
    result = get_forecast("SPY", df, include_llm_analysis=True)
    
    print("\nSingle Forecast Result:")
    print(json.dumps(result, indent=2))
    
    # Get performance metrics
    metrics = get_performance_metrics("SPY")
    print("\nPerformance Metrics:")
    print(json.dumps(metrics, indent=2))
    
    # Get model info
    model_info = get_model_info()
    print("\nModel Info:")
    print(json.dumps(model_info, indent=2))
    
    # Batch prediction
    batch_requests = [
        {"ticker": "SPY", "data": df},
        {"ticker": "QQQ", "data": df}  # Using same data for example
    ]
    
    batch_results = get_batch_forecasts(batch_requests)
    print(f"\nBatch Results (count: {len(batch_results)}):")
    for i, res in enumerate(batch_results):
        print(f"Result {i+1} for {res.get('ticker', 'N/A')}: Success = {'error' not in res}")
    
    return result, metrics, batch_results


if __name__ == "__main__":
    example_usage_api()