"""
Cache service with load_or_compute functionality.

Implements the load_or_compute pattern as required by FC-P0-004:
- loads cached data if available
- computes fresh data if not cached or stale
- persists the computed data for future requests
"""
from typing import Any, Callable, Optional, List
from ..storage.json_storage import load_json, save_json
import logging

logger = logging.getLogger(__name__)

async def load_or_compute(
    key: str, 
    compute_fn: Callable[[], Any], 
    force_refresh: bool = False,
    sources: Optional[List[str]] = None
) -> Any:
    """
    Load data from cache or compute it if not available.
    
    Args:
        key: The cache key to use
        compute_fn: Async function to compute the data if not in cache
        force_refresh: If True, always compute fresh data
        sources: List of sources used to generate the data
    
    Returns:
        Cached or freshly computed data
    """
    # Try to load from cache first
    if not force_refresh:
        cached_data = load_json(key)
        if cached_data is not None:
            logger.info(f"Cache hit for key: {key}")
            return cached_data
        else:
            logger.info(f"Cache miss for key: {key}, computing fresh data")
    else:
        logger.info(f"Force refresh requested for key: {key}, computing fresh data")
    
    # Compute fresh data
    try:
        fresh_data = await compute_fn() if callable(getattr(compute_fn, '__await__', None)) else compute_fn()
        
        # Save the fresh data to cache
        save_success = save_json(key, fresh_data, sources or [f"compute_fn_{key}"])
        
        if save_success:
            logger.info(f"Successfully cached fresh data for key: {key}")
            # Return the data in the same format as cached data (with metadata)
            return {
                "data": fresh_data,
                "last_update": load_json(key)["last_update"] if load_json(key) else None,
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