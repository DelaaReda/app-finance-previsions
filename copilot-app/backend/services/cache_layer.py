"""
Cache layer for Finance Copilot
Implements load_or_compute pattern for never-empty responses
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import time
import logging
from typing import Any, Callable, Optional, Dict, Union
from pathlib import Path
import threading
from functools import wraps

from backend.storage.base import load_json, save_json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for in-memory storage of frequently accessed items
MEMORY_CACHE = {}
CACHE_LOCK = threading.Lock()


def load_or_compute(key: str, compute_fn: Callable[[], Any], source: Optional[Union[str, list]] = None) -> Dict[str, Any]:
    """
    Load data from persistent storage, or compute and save if not available.
    
    Args:
        key: Unique identifier for the data (without extension)
        compute_fn: Function to compute the data if not available
        source: Source information for data lineage
        
    Returns:
        Loaded or computed data with metadata
    """
    # Create filename from key
    filename = f"{key}.json"
    
    # First, check in-memory cache
    with CACHE_LOCK:
        if key in MEMORY_CACHE:
            logger.info(f"Cache hit for {key} (in-memory)")
            return MEMORY_CACHE[key]
    
    # Then check persistent storage
    logger.info(f"Attempting to load {filename} from persistent storage")
    cached_data = load_json(filename)
    
    if cached_data is not None:
        logger.info(f"Cache hit for {key} (disk)")
        
        # Update in-memory cache
        with CACHE_LOCK:
            MEMORY_CACHE[key] = cached_data
        
        return cached_data
    else:
        logger.info(f"Cache miss for {key}, computing fresh data...")
        
        # Compute new data
        start_time = time.time()
        try:
            fresh_data = compute_fn()
            compute_time = time.time() - start_time
            logger.info(f"Computed fresh data for {key} in {compute_time:.2f}s")
        except Exception as e:
            logger.error(f"Error computing data for {key}: {str(e)}")
            # If computation fails, try to return any backup/old data
            fallback_data = _get_fallback_data(key)
            if fallback_data:
                logger.info(f"Returning fallback data for {key}")
                return fallback_data
            # If no fallback, raise the error
            raise e
        
        # Prepare metadata
        source_info = source or [f"compute_fn_{key}"]
        if isinstance(source_info, str):
            source_info = [source_info]
        
        # Save to persistent storage
        try:
            save_path = save_json(fresh_data, filename, source_info)
            logger.info(f"Saved computed data to {save_path}")
        except Exception as e:
            logger.error(f"Error saving data for {key}: {str(e)}")
        
        # Prepare return data with metadata
        result = {
            "data": fresh_data,
            "last_update": _get_current_timestamp(),
            "source": source_info,
            "compute_time": compute_time,
            "status": "fresh"
        }
        
        # Update in-memory cache
        with CACHE_LOCK:
            MEMORY_CACHE[key] = result
        
        return result


def _get_fallback_data(key: str) -> Optional[Dict[str, Any]]:
    """
    Get fallback data when computation fails
    """
    # Try to load any existing data even if it's old
    filename = f"{key}.json"
    data = load_json(filename)
    
    if data:
        # Add fallback status
        if isinstance(data, dict) and "data" in data:
            data["status"] = "fallback"
        else:
            # If it's raw data, wrap it
            data = {
                "data": data,
                "last_update": _get_current_timestamp(),
                "source": ["fallback"],
                "status": "fallback"
            }
        return data
    
    return None


def _get_current_timestamp() -> str:
    """Helper to get current UTC timestamp"""
    from datetime import datetime
    return datetime.utcnow().isoformat()


def cache_with_ttl(ttl_seconds: int = 3600):
    """
    Decorator to add TTL (time-to-live) behavior to cache
    """
    def decorator(func):
        last_run_times = {}
        
        @wraps(func)
        def wrapper(key: str, compute_fn: Callable[[], Any], source: Optional[Union[str, list]] = None):
            current_time = time.time()
            
            # Check if we have a recent run time for this key
            if key in last_run_times:
                time_since_last_run = current_time - last_run_times[key]
                
                # If TTL hasn't expired, try to load from disk first
                if time_since_last_run < ttl_seconds:
                    cached_data = load_json(f"{key}.json")
                    if cached_data is not None:
                        logger.info(f"Using TTL-cached data for {key}")
                        return cached_data
            
            # Otherwise, run the full load_or_compute
            result = load_or_compute(key, compute_fn, source)
            
            # Update the last run time
            last_run_times[key] = time.time()
            
            return result
        
        return wrapper
    return decorator


# Predefined cache functions for common data types
def load_or_compute_forecasts(compute_fn: Callable[[], Any]) -> Dict[str, Any]:
    """
    Load or compute forecasts data
    """
    return load_or_compute("forecasts", compute_fn, ["forecast_model", "ml_prediction"])


def load_or_compute_news_feed(compute_fn: Callable[[], Any]) -> Dict[str, Any]:
    """
    Load or compute news feed data
    """
    return load_or_compute("news_feed", compute_fn, ["rss_ingestion", "news_processing"])


def load_or_compute_weekly_brief(compute_fn: Callable[[], Any]) -> Dict[str, Any]:
    """
    Load or compute weekly brief data
    """
    return load_or_compute("brief_weekly", compute_fn, ["weekly_analysis", "market_summary"])


def load_or_compute_backtests(compute_fn: Callable[[], Any]) -> Dict[str, Any]:
    """
    Load or compute backtests data
    """
    return load_or_compute("backtests", compute_fn, ["backtest_engine", "performance_analysis"])


def load_or_compute_macro_data(compute_fn: Callable[[], Any]) -> Dict[str, Any]:
    """
    Load or compute macro data
    """
    return load_or_compute("macro_data", compute_fn, ["macro_ingestion", "economic_indicators"])


# Function to clear in-memory cache for a specific key
def clear_cache_key(key: str):
    """
    Clear a specific key from in-memory cache
    """
    with CACHE_LOCK:
        if key in MEMORY_CACHE:
            del MEMORY_CACHE[key]
            logger.info(f"Cleared cache for key: {key}")


# Function to clear entire in-memory cache
def clear_all_cache():
    """
    Clear entire in-memory cache
    """
    with CACHE_LOCK:
        MEMORY_CACHE.clear()
        logger.info("Cleared entire cache")


if __name__ == "__main__":
    # Test the cache layer
    print("Testing cache layer...")
    
    # Define a test computation function
    def test_compute():
        import time
        time.sleep(0.1)  # Simulate some work
        return {"test_data": "computed", "timestamp": _get_current_timestamp()}
    
    # Test load_or_compute (first time should compute)
    print("First call (should compute):")
    result1 = load_or_compute("test_cache", test_compute, ["test_source"])
    print(f"Result: {result1}")
    
    # Test load_or_compute again (should load from disk)
    print("\nSecond call (should load from disk):")
    result2 = load_or_compute("test_cache", test_compute, ["test_source"])
    print(f"Result: {result2}")
    
    # Clean up test file
    import os
    from backend.storage.base import STORAGE_DIR
    test_file = STORAGE_DIR / "test_cache.json"
    if test_file.exists():
        os.remove(test_file)
        print("\nCleaned up test file")
    
    print("\nCache layer test completed successfully")