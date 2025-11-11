"""
Advanced Cache Service for Finance Copilot
Task: BE-007 - Memory cache for frequent endpoints
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
Extends LRUCache with API-specific features like response wrapping and freshness tracking.
"""
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union, Callable
from datetime import datetime
import hashlib
import json

# Add backend root to sys.path for proper imports
backend_root = Path(__file__).resolve().parents[2]  
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from backend.src.core.memory_cache import memory_cache, cache_get, cache_set, cache_invalidate
from backend.src.core.response import ok


class CacheService:
    """
    Advanced caching service for API responses with metadata tracking.
    """
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.default_ttl = default_ttl
        self.data_dir = Path("data")
    
    def get_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """
        Generate consistent cache key for an endpoint with parameters.
        
        Args:
            endpoint: API endpoint path (e.g., "/api/forecasts")
            params: Query parameters dict
            
        Returns:
            String cache key
        """
        key_base = f"api:{endpoint}"
        
        if params:
            # Sort params for consistent hashing
            sorted_params = sorted(params.items())
            params_str = json.dumps(sorted_params, sort_keys=True, default=str)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]  # Short hash
            return f"{key_base}:{params_hash}"
        else:
            return key_base
    
    def get_file_tracking_paths(self, endpoint: str) -> Optional[Tuple[str, ...]]:
        """
        Determine relevant files to track for cache invalidation based on endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Tuple of file paths to track (or None if no tracking needed)
        """
        file_mappings = {
            "/api/forecasts": ("data/forecasts.json", "data/forecast"),
            "/api/news/feed": ("data/news_feed.json", "data/news"),
            "/api/macro/series": ("data/macro", "data/economic"),
            "/api/brief/daily": ("data/brief_daily.json", "data/brief_weekly.json"),
            "/api/dashboard/kpis": ("data/forecasts.json", "data/news_feed.json", "data/brief_weekly.json", "data/backtests.json"),
            "/api/stocks/prices": ("data/stocks", "data/stock_prices.json"),
        }
        
        return file_mappings.get(endpoint)
    
    def get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Retrieve cached response for endpoint with parameters.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters dict
            
        Returns:
            Cached response dict or None if not cached/expired
        """
        cache_key = self.get_cache_key(endpoint, params)
        file_paths = self.get_file_tracking_paths(endpoint)
        
        result = cache_get(cache_key, file_paths)
        return result
    
    def set(self, endpoint: str, response_data: Dict, params: Dict = None, ttl_seconds: Optional[int] = None):
        """
        Store response in cache with metadata.
        
        Args:
            endpoint: API endpoint path
            response_data: Response data to cache
            params: Query parameters dict
            ttl_seconds: Override default TTL if provided
        """
        cache_key = self.get_cache_key(endpoint, params)
        file_paths = self.get_file_tracking_paths(endpoint)
        actual_ttl = ttl_seconds or self.default_ttl
        
        # Add metadata to response for freshness tracking
        enhanced_response = {
            **response_data,
            "cached_at": datetime.utcnow().isoformat() + "Z",
            "ttl_seconds": actual_ttl,
            "cache_key": cache_key
        }
        
        cache_set(cache_key, enhanced_response, file_paths)
    
    def invalidate(self, endpoint: str, params: Dict = None):
        """Invalidate cache entry for endpoint with parameters."""
        cache_key = self.get_cache_key(endpoint, params)
        cache_invalidate(cache_key)
    
    def invalidate_prefix(self, prefix: str):
        """Invalidate all cache entries with given prefix."""
        from backend.src.core.memory_cache import invalidate_cache_prefix
        invalidate_cache_prefix(prefix)
    
    def wrap_with_cache(self, func: Callable, endpoint: str, params: Dict = None, ttl_seconds: Optional[int] = None):
        """
        Wrap a function call with cache logic.
        
        Args:
            func: Function to wrap with cache
            endpoint: API endpoint identifier
            params: Parameters for cache key generation
            ttl_seconds: TTL override for this particular call
            
        Returns:
            Cached response if available, otherwise computed response with caching
        """
        # First try to get from cache
        cached_response = self.get(endpoint, params)
        if cached_response is not None:
            # Return cached response with cache metadata
            return {
                **cached_response,
                "freshness": "cached",
                "cache_hit": True
            }
        
        # Function not cached, execute it
        try:
            result = func()
            
            # Cache the result
            self.set(endpoint, result, params, ttl_seconds)
            
            # Return result with cache metadata
            return {
                **result,
                "freshness": "fresh",
                "cache_hit": False,
                "cache_miss": True
            }
        except Exception as e:
            print(f"Error in cached function execution: {str(e)}")
            # On error, return cache if available, otherwise re-raise
            raise e
    
    def get_freshness_info(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """
        Get information about cache freshness for a specific endpoint.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters dict
            
        Returns:
            Freshness info including age, source, etc.
        """
        cache_key = self.get_cache_key(endpoint, params)
        file_paths = self.get_file_tracking_paths(endpoint)
        
        cached = cache_get(cache_key, file_paths)
        if cached and "cached_at" in cached:
            cached_at = datetime.fromisoformat(cached["cached_at"].replace("Z", "+00:00"))
            age_seconds = (datetime.utcnow() - cached_at.replace(tzinfo=None)).total_seconds()
            
            return {
                "cached": True,
                "age_seconds": age_seconds,
                "cached_at": cached["cached_at"],
                "ttl_seconds": cached.get("ttl_seconds", self.default_ttl),
                "cache_key": cache_key,
                "expires_in": max(0, cached.get("ttl_seconds", self.default_ttl) - age_seconds),
                "freshness": "cached" if age_seconds < (cached.get("ttl_seconds", self.default_ttl) / 2) else "stale"
            }
        else:
            return {
                "cached": False,
                "age_seconds": None,
                "cached_at": None,
                "ttl_seconds": self.default_ttl,
                "cache_key": cache_key,
                "expires_in": None,
                "freshness": "missing"
            }
    
    def invalidate_all(self):
        """Clear entire cache."""
        from backend.src.core.memory_cache import cache_clear
        cache_clear()


# Global instance of the cache service
cache_service = CacheService(default_ttl=300)  # 5-minute default TTL for API responses


# Async-compatible cache service for use with FastAPI
class AsyncCacheService(CacheService):
    """
    Async-compatible version of CacheService with asyncio support.
    """
    
    async def awrap_with_cache(self, func: Callable, endpoint: str, params: Dict = None, ttl_seconds: Optional[int] = None):
        """
        Async version of wrap_with_cache using run_in_executor for CPU-intensive operations.
        """
        # First try to get from cache
        cached_response = self.get(endpoint, params)
        if cached_response is not None:
            return {
                **cached_response,
                "freshness": "cached",
                "cache_hit": True
            }
        
        # Function not cached, execute it
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func()
            else:
                result = await asyncio.get_event_loop().run_in_executor(None, func)
            
            # Cache the result
            self.set(endpoint, result, params, ttl_seconds)
            
            # Return result with cache metadata
            return {
                **result,
                "freshness": "fresh", 
                "cache_hit": False,
                "cache_miss": True
            }
        except Exception as e:
            print(f"Error in async cached function execution: {str(e)}")
            raise e


# Async global instance
async_cache_service = AsyncCacheService(default_ttl=300)