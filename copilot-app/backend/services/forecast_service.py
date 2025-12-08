from ..models.forecast_hybrid_v1 import ForecastHybridV1
import json
from pathlib import Path
import os

def compute_forecasts():
    """
    Generate real forecasts using the hybrid ML+G4F system
    """
    # Initialize the hybrid forecast system
    forecast_system = ForecastHybridV1()
    
    # Define the tickers to generate forecasts for
    default_tickers = ["SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "META", "AMZN", "NFLX"]
    
    # Generate forecasts using the hybrid system
    try:
        forecasts = forecast_system.run_forecast_job(default_tickers)
        return forecasts
    except Exception as e:
        # If hybrid system fails, return empty but valid structure
        return {
            "rows": [],
            "last_update": "error",
            "source": ["fallback"],
            "model_version": "hybrid_v1",
            "tickers_processed": default_tickers,
            "total_forecasts": 0
        }

def get_all_forecasts(cache):
    """
    Get all forecasts with cache mechanism
    """
    # Use the cache system to serve snapshots with fallback to compute
    if cache:
        return cache("forecasts", compute_forecasts, source=["hybrid_ml_g4f", "live_computation"])
    else:
        # Fallback if cache function not provided
        return compute_forecasts()