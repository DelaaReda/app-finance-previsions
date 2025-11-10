"""
Forecasts Materialization Job - FC-DATA-004
Author: ALEX-API-ARCHITECT-SUPERMAN-7

Task: Create daily forecasts cache with materialized data for instant serving.
"""
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import necessary modules
import sys
import os
# Add the backend root to sys.path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.io import load_json, save_json
from core.data_quality import validate_forecasts_structure

def materialize_daily_forecasts() -> Dict[str, Any]:
    """
    Generate daily materialized forecasts and save to cache for fast serving.
    
    **Process**:
    - Load latest forecasts from active models
    - Apply validation and quality checks
    - Save to dated directory with symlinks
    - Preserve metadata for freshness tracking
    """
    try:
        logger.info("Starting daily forecasts materialization...")
        
        # Load current forecasts from the system (from existing storage)
        raw_forecasts = load_json("forecasts") or {}
        forecast_rows = raw_forecasts.get("rows", raw_forecasts.get("data", []))
        
        # Validate structure before proceeding
        if not validate_forecasts_structure(forecast_rows):
            logger.warning("Forecast data structure validation failed, using empty fallback")
            forecast_rows = []
        
        # Add metadata about the materialization
        materialized_data = {
            "rows": forecast_rows,
            "count": len(forecast_rows),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "materialized_at": datetime.now().isoformat(),
            "source": ["materialization_job", "validated_forecasts"],
            "metrics": {
                "total_symbols": len(list(set(f.get("ticker", f.get("symbol", "")) for f in forecast_rows if f.get("ticker") or f.get("symbol"))),
                "horizons_covered": list(set(f.get("horizon", "") for f in forecast_rows if f.get("horizon"))),
                "model_coverage": list(set(f.get("model", "default") for f in forecast_rows))
            }
        }
        
        # Save to dated directory
        today = datetime.now().strftime("%Y%m%d")
        forecast_dir = Path("data/forecast") / f"dt={today}"
        forecast_dir.mkdir(parents=True, exist_ok=True)
        
        # Write the materialized forecasts
        output_file = forecast_dir / "forecasts.parquet"
        if forecast_rows:
            df = pd.DataFrame(forecast_rows)
            df.to_parquet(output_file, engine='pyarrow')
        
        # Also create the JSON backup format used by our system
        json_output_file = forecast_dir / "forecasts.json"
        json_output_file.write_text(json.dumps(materialized_data, indent=2, ensure_ascii=False))
        
        # Create/update symlink to latest
        latest_symlink = Path("data/forecast/latest")
        if latest_symlink.exists() and latest_symlink.is_symlink():
            latest_symlink.unlink()
        
        latest_symlink.symlink_to(forecast_dir)
        
        # Also store in the main forecasts.json for compatibility with existing endpoints
        save_json("forecasts", materialized_data, source=["materialization_job", "daily_cache"])
        
        logger.info(f"Daily forecasts materialized successfully: {len(forecast_rows)} forecasts for {today}")
        return materialized_data
        
    except Exception as e:
        logger.error(f"Error in forecasts materialization: {str(e)}", exc_info=True)
        # Return safe fallback structure
        return {
            "rows": [],
            "count": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "materialized_at": datetime.now().isoformat(),
            "source": ["materialization_job", "fallback"],
            "error": str(e),
            "metrics": {
                "total_symbols": 0,
                "horizons_covered": [],
                "model_coverage": []
            }
        }


def run_forecast_materialization_job():
    """
    Main entry point for the forecast materialization job.
    Designed to be run daily via scheduler.
    """
    logger.info("Running forecast materialization job...")
    result = materialize_daily_forecasts()
    logger.info(f"Forecast materialization job completed. Generated {result.get('count', 0)} forecasts.")
    return result


if __name__ == "__main__":
    # When run as script, execute the materialization
    print("Running forecast materialization job...")
    result = run_forecast_materialization_job()
    print(f"Materialization complete: {result.get('count', 0)} forecasts for {datetime.now().strftime('%Y-%m-%d')}")