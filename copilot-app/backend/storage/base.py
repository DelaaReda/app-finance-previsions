"""
Persistent storage layer for Finance Copilot
Implements save_json and load_json with metadata
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, Union
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define storage directory
STORAGE_DIR = Path(__file__).parent.parent / "data"
STORAGE_DIR.mkdir(exist_ok=True)


def save_json(data: Any, filename: str, source: Optional[Union[str, list]] = None) -> str:
    """
    Save data to a JSON file with metadata
    
    Args:
        data: Data to save
        filename: Name of the file to save to (without path)
        source: Source information for data lineage
        
    Returns:
        Path to the saved file
    """
    try:
        # Create full file path
        filepath = STORAGE_DIR / filename
        
        # Prepare metadata
        metadata = {
            "last_update": datetime.utcnow().isoformat(),
            "source": source or [],
            "data": data
        }
        
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write data to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Data saved successfully to {filepath}")
        return str(filepath)
        
    except Exception as e:
        logger.error(f"Error saving JSON to {filename}: {str(e)}")
        raise


def load_json(filename: str) -> Optional[Dict[str, Any]]:
    """
    Load data from a JSON file with metadata
    
    Args:
        filename: Name of the file to load from (without path)
        
    Returns:
        Loaded data dictionary or None if file doesn't exist
    """
    try:
        filepath = STORAGE_DIR / filename
        
        if not filepath.exists():
            logger.info(f"File {filepath} does not exist, returning None")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Data loaded successfully from {filepath}")
        return data
        
    except Exception as e:
        logger.error(f"Error loading JSON from {filename}: {str(e)}")
        return None


def save_forecasts(data: Any, source: Optional[Union[str, list]] = None) -> str:
    """
    Save forecasts data specifically
    """
    return save_json(data, "forecasts.json", source or ["forecast_model"])


def load_forecasts() -> Optional[Dict[str, Any]]:
    """
    Load forecasts data specifically
    """
    return load_json("forecasts.json")


def save_news_feed(data: Any, source: Optional[Union[str, list]] = None) -> str:
    """
    Save news feed data specifically
    """
    return save_json(data, "news_feed.json", source or ["rss_ingestion"])


def load_news_feed() -> Optional[Dict[str, Any]]:
    """
    Load news feed data specifically
    """
    return load_json("news_feed.json")


def save_weekly_brief(data: Any, source: Optional[Union[str, list]] = None) -> str:
    """
    Save weekly brief data specifically
    """
    return save_json(data, "brief_weekly.json", source or ["weekly_analysis"])


def load_weekly_brief() -> Optional[Dict[str, Any]]:
    """
    Load weekly brief data specifically
    """
    return load_json("brief_weekly.json")


def save_backtests(data: Any, source: Optional[Union[str, list]] = None) -> str:
    """
    Save backtests data specifically
    """
    return save_json(data, "backtests.json", source or ["backtest_engine"])


def load_backtests() -> Optional[Dict[str, Any]]:
    """
    Load backtests data specifically
    """
    return load_json("backtests.json")


# Update todo status
if __name__ == "__main__":
    # Test the storage functions
    test_data = {
        "test": "data",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print("Testing storage functions...")
    
    # Test save
    filepath = save_json(test_data, "test.json", ["test_source"])
    print(f"Saved to: {filepath}")
    
    # Test load
    loaded_data = load_json("test.json")
    print(f"Loaded: {loaded_data}")
    
    # Clean up test file
    test_path = STORAGE_DIR / "test.json"
    if test_path.exists():
        os.remove(test_path)
        print("Cleaned up test file")
    
    print("Storage functions test completed successfully")