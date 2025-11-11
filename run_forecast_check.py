#!/usr/bin/env python3
"""
Script to run the forecast job and generate real forecast data
"""
import sys
import os
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'copilot-app', 'backend'))

def run_forecast_job_direct():
    """Direct execution of the forecast job"""
    print("Running forecast job...")
    
    try:
        from jobs.forecasts import run_forecasts_job
        result = run_forecasts_job()
        print(f"SUCCESS: Generated {result.get('count', 0)} forecasts")
        print(f"Status: {result.get('pipeline', {}).get('ml_model', 'unknown')} + {result.get('pipeline', {}).get('llm_model', 'unknown')}")
        return result
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    run_forecast_job_direct()