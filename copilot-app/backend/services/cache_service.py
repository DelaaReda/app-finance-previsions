"""
Advanced Cache Service with load_or_compute functionality and intelligent invalidation.

Implements the load_or_compute pattern as required by FC-P0-004 with advanced features:
- loads cached data if available
- computes fresh data if not cached or stale
- persists the computed data for future requests
- automatically invalidates dependent caches based on data freshness
- supports dependency tracking and cascade invalidation
"""
from typing import Any, Callable, Optional, List, Tuple
from datetime import datetime
import sys
import os
import asyncio

# Add backend path for proper imports
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

from storage.json_storage import load_json, save_json
from jobs.cache_manager import invalidate_cache_if_needed, mark_cache_as_updated, mark_cache_as_invalidated
import logging

logger = logging.getLogger(__name__)

async def load_or_compute(
    key: str, 
    compute_fn: Callable[[], Any], 
    force_refresh: bool = False,
    sources: Optional[List[str]] = None,
    max_age_seconds: int = 3600,  # Default: 1 hour
    invalidate_dependents: bool = True  # Whether to mark dependents for refresh when this cache is updated
) -> Any:
    """
    Load data from cache or compute it if not available.
    
    Args:
        key: The cache key to use
        compute_fn: Async function to compute the data if not in cache
        force_refresh: If True, always compute fresh data
        sources: List of sources used to generate the data
        max_age_seconds: Maximum age of cache before it's considered stale
        invalidate_dependents: Whether to mark dependent caches for refresh when this is updated
    
    Returns:
        Cached or freshly computed data
    """
    # Check if cache needs invalidation based on dependencies or age
    should_invalidate, invalidation_reason = invalidate_cache_if_needed(key, max_age_seconds)
    
    if should_invalidate:
        logger.info(f"Cache invalidation required for key: {key} - {invalidation_reason}")
        force_refresh = True
    
    # Try to load from cache first
    if not force_refresh:
        cached_data = load_json(key)
        if cached_data is not None:
            logger.info(f"Cache hit for key: {key}")
            return cached_data
        else:
            logger.info(f"Cache miss for key: {key}, computing fresh data")
    else:
        logger.info(f"Force refresh for key: {key}, computing fresh data (reason: {invalidation_reason if 'invalidation_reason' in locals() else 'force_refresh=True'})")
    
    # Compute fresh data
    try:
        # Check if compute_fn is a coroutine function to handle async properly
        if asyncio.iscoroutinefunction(compute_fn):
            fresh_data = await compute_fn()
        else:
            fresh_data = compute_fn()
        
        # Save the fresh data to cache
        save_success = save_json(key, fresh_data, sources or [f"compute_fn_{key}"])
        
        if save_success:
            logger.info(f"Successfully cached fresh data for key: {key}")
            
            # Mark this cache as updated (and potentially trigger dependent invalidations)
            if invalidate_dependents:
                try:
                    mark_cache_as_updated(key)
                    logger.info(f"Tracked cache update for '{key}' in dependency system")
                except Exception as e:
                    logger.error(f"Failed to track cache update for '{key}' in dependency system: {e}")
            
            # Load the just-saved data to get the full metadata including freshness
            cached_result = load_json(key)
            if cached_result:
                # Mark this cache as no longer requiring refresh
                try:
                    mark_cache_as_invalidated(key)
                except Exception as e:
                    logger.error(f"Failed to clear refresh mark for '{key}': {e}")
                return cached_result
            else:
                # Fallback if we can't load the data we just saved
                return {
                    "data": fresh_data,
                    "last_update": datetime.now().isoformat(),
                    "source": sources or [f"compute_fn_{key}"],
                    "freshness": "fresh"
                }
        else:
            logger.error(f"Failed to cache data for key: {key}")
            # Return the computed data without metadata if caching fails
            return fresh_data
            
    except Exception as e:
        logger.error(f"Error computing data for key {key}: {str(e)}")
        # If computation fails, try to return stale data
        cached_data = load_json(key)
        if cached_data is not None:
            logger.info(f"Returning stale data for key: {key} due to computation error")
            return cached_data
        else:
            logger.error(f"No cached data available for key: {key} and computation failed")
            return None


def get_advanced_cache_freshness_info():
    """
    Get comprehensive freshness information for all tracked caches.
    """
    try:
        from jobs.cache_manager import CacheInvalidationTracker
        tracker = CacheInvalidationTracker()
        return tracker.get_cache_freshness_info()
    except Exception as e:
        logger.error(f"Error getting cache freshness info: {e}")
        return {}


def force_invalidate_cache(cache_key: str, reason: str = "Manual invalidation"):
    """
    Force invalidation of a specific cache key.
    
    Args:
        cache_key: The key to invalidate
        reason: Reason for invalidation (for logging)
    """
    try:
        from jobs.cache_manager import CacheInvalidationTracker
        tracker = CacheInvalidationTracker()
        tracker._mark_for_refresh(cache_key, reason)
        logger.info(f"Force invalidated cache '{cache_key}' - {reason}")
        return True
    except Exception as e:
        logger.error(f"Error force invalidating cache '{cache_key}': {e}")
        return False