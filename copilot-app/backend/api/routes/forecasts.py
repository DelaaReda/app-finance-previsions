# API Route for Forecasts - Serves cached forecasts
# File: /api/routes/forecasts.py
# Task: FC-P1-013 - ALEX-FINANCE-ANALYST-SUPERMAN-29

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import json
from pathlib import Path
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Define the data directory
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FORECASTS_FILE = DATA_DIR / "forecasts.json"

@router.get("/forecasts")
async def get_forecasts() -> Dict[str, Any]:
    """
    Get the latest forecasts from the hybrid ML + G4F system.
    Serves the cached snapshot, never returns empty results.
    """
    try:
        # Check if forecasts file exists
        if not FORECASTS_FILE.exists():
            logger.warning("Forecasts file does not exist, returning empty response with metadata")
            return {
                "rows": [],
                "last_update": datetime.now().isoformat(),
                "source": ["hybrid_ml_g4f"],
                "model_version": "hybrid_v1",
                "status": "no_data_available",
                "message": "Forecasts are being generated. Please check back later."
            }
        
        # Read the forecasts file
        with open(FORECASTS_FILE, 'r') as f:
            content = json.load(f)
        
        # Extract the data part while preserving metadata
        if "data" in content:
            forecasts_data = content["data"]
            # Ensure rows key exists in forecasts_data
            if "rows" not in forecasts_data:
                forecasts_data["rows"] = []
        else:
            # Handle case where file format is different 
            forecasts_data = content
            if "rows" not in forecasts_data:
                forecasts_data = {
                    "rows": [],
                    "last_update": datetime.now().isoformat(),
                    "source": ["hybrid_ml_g4f"],
                    "model_version": "hybrid_v1"
                }
        
        # Ensure the response has the required structure
        if "rows" not in forecasts_data:
            forecasts_data["rows"] = []
        
        if "last_update" not in forecasts_data:
            forecasts_data["last_update"] = content.get("last_update", datetime.now().isoformat())
        
        if "source" not in forecasts_data:
            forecasts_data["source"] = content.get("source", ["hybrid_ml_g4f"])
        
        if "model_version" not in forecasts_data:
            forecasts_data["model_version"] = content.get("model_version", "hybrid_v1")
        
        # Add status information
        forecasts_data["status"] = "success"
        forecasts_data["freshness"] = "current" if _is_recent(forecasts_data.get("last_update")) else "stale"
        
        logger.info(f"Serving forecasts for {len(forecasts_data['rows'])} tickers")
        return forecasts_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding forecasts file: {e}")
        return {
            "rows": [],
            "last_update": datetime.now().isoformat(),
            "source": ["hybrid_ml_g4f"],
            "model_version": "hybrid_v1",
            "status": "error",
            "error": "Invalid JSON format in forecasts file"
        }
    except Exception as e:
        logger.error(f"Error serving forecasts: {e}")
        return {
            "rows": [],
            "last_update": datetime.now().isoformat(),
            "source": ["hybrid_ml_g4f"],
            "model_version": "hybrid_v1",
            "status": "error",
            "error": str(e)
        }

def _is_recent(timestamp_str: str) -> bool:
    """
    Check if the timestamp is recent (less than 24 hours old)
    """
    try:
        if timestamp_str is None:
            return False
        
        from datetime import datetime, timedelta
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return (datetime.now(timestamp.tzinfo) - timestamp) < timedelta(hours=24)
    except:
        return False

# Test endpoint
@router.get("/forecasts/test")
async def test_forecasts() -> Dict[str, Any]:
    """
    Test endpoint to verify the forecasts route is working
    """
    return {
        "message": "Forecasts endpoint is active",
        "data_file_exists": FORECASTS_FILE.exists(),
        "last_update": datetime.now().isoformat()
    }