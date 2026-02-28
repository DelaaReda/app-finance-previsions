"""
Advanced Cache Invalidation System - Task FC-P2-019
Implements intelligent cache invalidation based on data freshness and dependencies.

Resolves cache invalidation challenges where:
- news updates should refresh dependent briefs/backtests
- forecasts updates should refresh backtests
- macro data updates should refresh related indicators
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)

# Directory for data storage
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(exist_ok=True)

# Define cache dependencies mapping
CACHE_DEPENDENCIES = {
    "forecasts": ["backtests"],  # forecasts update -> backtests need refresh
    "news_feed": ["brief_weekly", "brief_daily"],  # news update -> briefs need refresh
    "macro_series": ["forecasts", "backtests"],  # macro update -> affects forecasts/backtests
    "brief_weekly": ["alerts"],  # brief update -> alerts may need refresh
    "brief_daily": ["alerts"]  # brief update -> alerts may need refresh
}

class CacheInvalidationTracker:
    """
    Tracks cache dependencies and manages invalidation based on freshness.
    """
    
    def __init__(self, dependencies: Dict[str, List[str]] = None):
        self.dependencies = dependencies or CACHE_DEPENDENCIES
        self.state_file = DATA_DIR / "cache_invalidation_state.json"
        self.load_state()
    
    def load_state(self):
        """Load the current state from persistent storage."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache state: {e}")
                self.state = {"last_updates": {}, "invalidations": {}}
        else:
            self.state = {"last_updates": {}, "invalidations": {}}
    
    def save_state(self):
        """Save the current state to persistent storage."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache state: {e}")
    
    def update_timestamp(self, cache_key: str):
        """Update the timestamp for a cache key and trigger dependent invalidations."""
        now = datetime.utcnow().isoformat()
        self.state["last_updates"][cache_key] = now
        
        # Trigger dependent invalidations
        self._trigger_dependent_invalidations(cache_key)
        
        # Save state
        self.save_state()
        
        logger.info(f"Updated timestamp for cache '{cache_key}' and triggered dependent invalidations")
        return True
    
    def _trigger_dependent_invalidations(self, updated_key: str):
        """Trigger invalidation of dependent caches when a cache is updated."""
        if updated_key not in self.dependencies:
            return
        
        dependent_caches = self.dependencies[updated_key]
        for dep_cache in dependent_caches:
            self._mark_for_refresh(dep_cache, f"Dependent on {updated_key}")
    
    def _mark_for_refresh(self, cache_key: str, reason: str):
        """Mark a cache as needing refresh."""
        now = datetime.utcnow().isoformat()
        if "invalidations" not in self.state:
            self.state["invalidations"] = {}
        
        self.state["invalidations"][cache_key] = {
            "marked_at": now,
            "reason": reason
        }
        
        logger.info(f"Marked cache '{cache_key}' for refresh: {reason}")
    
    def mark_cache_invalidated(self, cache_key: str):
        """Remove the invalidation mark when cache has been refreshed."""
        if "invalidations" in self.state and cache_key in self.state["invalidations"]:
            del self.state["invalidations"][cache_key]
            self.save_state()
            logger.info(f"Cache '{cache_key}' marked as refreshed")
    
    def should_refresh_cache(self, cache_key: str, max_age_seconds: int = 3600) -> Tuple[bool, str]:
        """
        Determine if a cache needs to be refreshed based on dependencies or age.
        
        Args:
            cache_key: The cache key to check
            max_age_seconds: Maximum age before cache is considered stale
        
        Returns:
            Tuple of (should_refresh, reason)
        """
        # Check if this cache is marked for refresh due to dependency
        if "invalidations" in self.state and cache_key in self.state["invalidations"]:
            return True, self.state["invalidations"][cache_key]["reason"]
        
        # Check cache age
        if cache_key in self.state["last_updates"]:
            last_update_str = self.state["last_updates"][cache_key]
            try:
                last_update = datetime.fromisoformat(last_update_str)
                age = (datetime.utcnow() - last_update).total_seconds()
                if age > max_age_seconds:
                    return True, f"Cache older than {max_age_seconds} seconds ({age:.0f}s)"
            except ValueError:
                # If timestamp is invalid, treat as very old
                return True, "Invalid timestamp format"
        
        return False, "Cache is fresh"
    
    def get_cache_freshness_info(self) -> Dict[str, Dict[str, str]]:
        """Get freshness information for all tracked caches."""
        freshness_info = {}
        
        for cache_key, timestamp in self.state["last_updates"].items():
            try:
                last_update = datetime.fromisoformat(timestamp)
                age_seconds = (datetime.utcnow() - last_update).total_seconds()
                
                freshness_info[cache_key] = {
                    "last_update": timestamp,
                    "age_seconds": age_seconds,
                    "is_stale": age_seconds > 3600,  # More than 1 hour is stale
                    "marked_for_refresh": cache_key in self.state.get("invalidations", {})
                }
            except ValueError:
                freshness_info[cache_key] = {
                    "last_update": timestamp,
                    "age_seconds": -1,
                    "is_stale": True,
                    "marked_for_refresh": cache_key in self.state.get("invalidations", {})
                }
        
        return freshness_info


def run_cache_manager_job():
    """
    Main cache management job that:
    1. Checks freshness of all caches
    2. Identifies caches that need invalidation
    3. Updates cache dependency tracking
    """
    print("[INFO] Starting cache management job...")
    
    try:
        tracker = CacheInvalidationTracker()
        
        # Get current freshness information
        freshness_info = tracker.get_cache_freshness_info()
        
        print(f"[INFO] Tracked caches: {list(freshness_info.keys())}")
        
        # Print summary
        stale_caches = [k for k, v in freshness_info.items() if v.get("is_stale", False)]
        refresh_marked = [k for k, v in freshness_info.items() if v.get("marked_for_refresh", False)]
        
        print(f"[INFO] Stale caches: {stale_caches}")
        print(f"[INFO] Marked for refresh: {refresh_marked}")
        
        # Return freshness summary
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "tracked_caches": len(freshness_info),
            "stale_caches": stale_caches,
            "marked_for_refresh": refresh_marked,
            "freshness_info": freshness_info
        }
        
        print(f"[SUCCESS] Cache management job completed. Tracked {result['tracked_caches']} caches.")
        return result
        
    except Exception as e:
        print(f"[ERROR] Cache management job failed: {str(e)}")
        logger.error(f"Cache management job error: {str(e)}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "tracked_caches": 0,
            "stale_caches": [],
            "marked_for_refresh": []
        }


def invalidate_cache_if_needed(cache_key: str, max_age_seconds: int = 3600) -> Tuple[bool, str]:
    """
    Check if cache needs to be invalidated and return reason.
    
    Args:
        cache_key: The cache key to check
        max_age_seconds: Maximum age in seconds before considered stale
    
    Returns:
        Tuple of (should_invalidate, reason)
    """
    tracker = CacheInvalidationTracker()
    should_refresh, reason = tracker.should_refresh_cache(cache_key, max_age_seconds)
    
    if should_refresh:
        logger.info(f"Cache invalidation needed for '{cache_key}': {reason}")
    
    return should_refresh, reason


def mark_cache_as_updated(cache_key: str):
    """
    Mark a cache as updated (i.e., its source data has changed).
    
    This will trigger dependent cache invalidations.
    """
    tracker = CacheInvalidationTracker()
    return tracker.update_timestamp(cache_key)


def mark_cache_as_invalidated(cache_key: str):
    """
    Mark a cache as having been invalidated/refreshed.
    """
    tracker = CacheInvalidationTracker()
    return tracker.mark_cache_invalidated(cache_key)


if __name__ == "__main__":
    # Run standalone for testing
    result = run_cache_manager_job()
    print(f"Job completed. Tracked caches: {result['tracked_caches']}")
    print(f"Stale: {result['stale_caches']}")
    print(f"Marked for refresh: {result['marked_for_refresh']}")