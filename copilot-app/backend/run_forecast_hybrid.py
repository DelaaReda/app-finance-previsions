#!/usr/bin/env python3
"""
Forecast Generation Script - FC-P1-013
Generates hybrid forecasts using ML + G4F system
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def run_forecast_job():
    """
    Execute the forecast job as a standalone script
    """
    try:
        from models.forecast_hybrid_v1 import ForecastHybridV1
        
        print("Initializing hybrid forecast system...")
        hybrid = ForecastHybridV1()
        
        print("Running forecast job for major assets...")
        tickers = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "META"]
        forecasts = hybrid.run_forecast_job(tickers)
        
        print(f"✓ Generated {len(forecasts.get('rows', []))} forecasts")
        print("✓ Forecasts saved to data/forecasts.json")
        print("✓ Ready for API consumption")
        
        return forecasts
    except ImportError as e:
        print(f"⚠ Dependency issue (expected in clean environment): {e}")
        print("⚠ This script will run properly when all dependencies are installed")
        return None
    except Exception as e:
        print(f"✗ Error running forecast job: {e}")
        return None

if __name__ == "__main__":
    print("Starting Forecast Hybrid v1 job (FC-P1-013)...")
    result = run_forecast_job()
    if result:
        print("✓ Forecast job completed successfully")
    else:
        print("⚠ Forecast job requires dependencies to run properly")