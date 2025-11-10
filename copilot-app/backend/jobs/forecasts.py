"""
Forecasts Job Module - Generates ML-based forecasts for financial assets
Part of Finance Copilot Architecture Enhancement Initiative

Implements the forecasting job that generates real market forecasts using ML models and market data
Integration by: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: FC-INT-009 - Connect job to real ForecastHybridV1 system
"""
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Dict, Any, List

# Add parent directory to path to import models
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

logger = logging.getLogger(__name__)

def run_forecasts_job(tickers: List[str] = None) -> Dict[str, Any]:
    """
    Main function to run forecasts generation job
    NOW ACTUALLY GENERATES REAL DATA using ForecastHybridV1
    """
    logger.info("Starting forecasts job with REAL data generation...")
    
    try:
        # Import the hybrid forecast system
        from models.forecast_hybrid_v1 import ForecastHybridV1
        from storage.io import save_json
        
        # Initialize the hybrid forecast system
        forecast_system = ForecastHybridV1()
        
        # Use default tickers if none provided
        if tickers is None:
            tickers = ["SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "META"]
        
        logger.info(f"Generating forecasts for {len(tickers)} tickers: {tickers}")
        
        # Generate forecasts using ML + LLM hybrid system
        forecasts = forecast_system.run_forecast_job(tickers)
        
        # Save to persistent storage using correct format: key, payload
        logger.info("Saving forecasts to storage...")
        save_json("forecasts", forecasts, source=["job:forecasts", "ml_model", "g4f_llm"])
        
        # Return summary
        result = {
            "forecast_count": len(forecasts.get('data', {}).get('rows', [])) if 'data' in forecasts else len(forecasts.get('rows', [])),
            "models_used": ["ml_model_v1", "g4f_hybrid"],
            "tickers_processed": tickers,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
            "source": ["forecast_hybrid_v1", "ml_model", "g4f_llm"]
        }
        
        logger.info(f"✅ Forecasts job completed successfully. Generated {result['forecast_count']} forecasts.")
        return result
        
    except ImportError as e:
        logger.error(f"Import error in forecasts job: {str(e)}", exc_info=True)
        logger.info("Dependencies may be missing - returning fallback result")
        # Return a minimal result indicating the system is set up but deps missing
        return {
            "forecast_count": 0,
            "models_used": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "pending_dependencies",
            "error": f"Import error: {str(e)}",
            "note": "System is configured but some dependencies are not installed"
        }
    except Exception as e:
        logger.error(f"Forecasts job failed: {str(e)}", exc_info=True)
        return {
            "forecast_count": 0,
            "models_used": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": str(e)
        }