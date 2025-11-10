"""
Cache Layer Service with Enhanced Error Handling
Task: FC-QM-CODACY-004 - File-Specific Quality Analysis
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21

Quality improvements:
- Better error handling with fallbacks
- Improved never-empty contract implementation
- Enhanced logging and monitoring
- More robust cache key validation
- Proper exception isolation
"""
import json
import os
import sys
from typing import Callable, Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
import logging

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from storage.io import load_json, save_json


class CacheLayerService:
    """
    Enhanced cache layer service with comprehensive error handling and fallback mechanisms
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "computed": 0
        }
    
    def load_or_compute(self, 
                       key: str, 
                       compute_fn: Callable[[], Dict[str, Any]], 
                       source: Optional[List[str]] = None,
                       ttl_minutes: Optional[int] = None) -> Dict[str, Any]:
        """
        Load cached data or compute fresh if not available/stale.
        
        Args:
            key: Cache key identifier
            compute_fn: Function to compute fresh data if cache miss or stale
            source: Source information for metadata
            ttl_minutes: Time-to-live in minutes (if None, cache never expires)
        
        Returns:
            Cached or computed data with never-empty contract
        """
        try:
            # Validate inputs
            if not key or not isinstance(key, str) or len(key) == 0:
                self.logger.warning("Invalid cache key provided, using fallback key")
                key = "default_fallback_key"
            
            # Clean key to prevent path traversal attacks
            sanitized_key = self._sanitize_key(key)
            
            # Try to load from cache first
            try:
                cached_data = load_json(sanitized_key)
                
                if cached_data:
                    # Check TTL if specified
                    if ttl_minutes is not None and isinstance(cached_data, dict):
                        stored_at = cached_data.get("generated_at", cached_data.get("timestamp", cached_data.get("created_at")))
                        if stored_at:
                            try:
                                # Parse the stored timestamp
                                if "Z" in stored_at:
                                    stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                                else:
                                    stored_datetime = datetime.fromisoformat(stored_at)
                                
                                current_time = datetime.utcnow()
                                elapsed_minutes = (current_time - stored_datetime).total_seconds() / 60
                                
                                if elapsed_minutes > ttl_minutes:
                                    self.logger.info(f"Cache expired for key: {sanitized_key}, TTL: {ttl_minutes} min, elapsed: {elapsed_minutes:.1f} min")
                                    cached_data = None  # Force recomputation
                                else:
                                    self.cache_stats["hits"] += 1
                                    return cached_data
                            except Exception as parse_error:
                                self.logger.warning(f"Could not parse cache timestamp for key {sanitized_key}: {str(parse_error)}")
                                # If we can't parse the timestamp, use the cached data anyway (never-empty)
                                self.cache_stats["hits"] += 1
                                return cached_data
                        else:
                            # No timestamp found, assume cache is valid (never-empty)
                            self.cache_stats["hits"] += 1
                            return cached_data
                    elif ttl_minutes is None:
                        # No TTL specified, cache is valid forever
                        self.cache_stats["hits"] += 1
                        return cached_data
                else:
                    self.logger.debug(f"No data found in cache for key: {sanitized_key}")
                    self.cache_stats["misses"] += 1
            
            except Exception as load_error:
                self.logger.warning(f"Load from cache failed for key {sanitized_key}: {str(load_error)}")
                self.cache_stats["errors"] += 1
                # Continue to compute fresh data if load fails
                cached_data = None
            
            # Cache miss or error, compute fresh data
            try:
                self.logger.info(f"Computing fresh data for cache key: {sanitized_key}")
                fresh_data = compute_fn()
                self.cache_stats["computed"] += 1
                
                # Add metadata to the computed data
                if isinstance(fresh_data, dict):
                    enhanced_data = dict(fresh_data)
                    enhanced_data["generated_at"] = datetime.utcnow().isoformat() + "Z"
                    enhanced_data["source"] = source or ["cache_layer", "computed_fresh", "fc-qm-codacy-004"]
                    enhanced_data["cache_key"] = sanitized_key
                    enhanced_data["ttl_minutes"] = ttl_minutes
                else:
                    # If compute_fn doesn't return a dict, wrap in a structured response
                    enhanced_data = {
                        "data": fresh_data,
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": source or ["cache_layer", "computed_wrapper", "fc-qm-codacy-004"],
                        "cache_key": sanitized_key,
                        "ttl_minutes": ttl_minutes,
                        "wrapped_original_type": type(fresh_data).__name__,
                        "message": "Data computed from function wrapped to maintain never-empty structure"
                    }
                
                # Save to cache
                try:
                    save_json(sanitized_key, enhanced_data, source=source or ["cache_layer", "computed_fresh", "fc-qm-codacy-004"])
                except Exception as save_error:
                    self.logger.error(f"Failed to save to cache for key {sanitized_key}: {str(save_error)}")
                    # Don't fail the whole operation just because saving to cache failed
                    # Still return the computed data to maintain never-empty contract
                
                return enhanced_data
                
            except Exception as compute_error:
                self.logger.error(f"Compute function failed for key {sanitized_key}: {str(compute_error)}")
                self.cache_stats["errors"] += 1
                
                # Return fallback data to maintain never-empty contract
                fallback = {
                    "data": None,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": source or ["cache_layer", "compute_error_fallback", "fc-qm-codacy-004"],
                    "cache_key": sanitized_key,
                    "error": str(compute_error),
                    "message": "Cache compute function failed but fallback data returned to maintain never-empty contract",
                    "fallback_strategy": "empty_structure_with_error_details"
                }
                
                return fallback
        
        except Exception as e:
            self.logger.error(f"Critical error in cache layer for key {key}: {str(e)}")
            self.cache_stats["errors"] += 1
            
            # Ultimate fallback to maintain never-empty contract
            return {
                "data": {},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": source or ["cache_layer", "critical_error_fallback", "fc-qm-codacy-004"],
                "cache_key": str(key),
                "error": str(e),
                "message": "Cache layer encountered critical error but fallback data returned to maintain never-empty contract",
                "fallback_strategy": "ultimate_empty_contract"
            }
    
    def _sanitize_key(self, key: str) -> str:
        """
        Sanitize cache key to prevent path traversal and other security issues
        
        Args:
            key: Original cache key
            
        Returns:
            Sanitized cache key
        """
        if not key or not isinstance(key, str):
            return "default_cache_key"
        
        # Remove potentially dangerous characters
        sanitized = key.replace("..", "_").replace("/", "_").replace("\\", "_")
        
        # Only allow alphanumeric, underscore, hyphen, dot, colon
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_\-\.:/]', '_', sanitized)
        
        # Limit length to prevent very long filenames
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        
        return sanitized
    
    def invalidate_cache(self, key: str) -> bool:
        """
        Invalidate a specific cache key (remove from cache)
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            Boolean indicating success
        """
        try:
            from storage.io import delete_json
            sanitized_key = self._sanitize_key(key)
            success = delete_json(sanitized_key)
            if success:
                self.logger.info(f"Cache invalidated for key: {sanitized_key}")
            else:
                self.logger.warning(f"Cache invalidation attempted for non-existent key: {sanitized_key}")
            return success
        except Exception as e:
            self.logger.error(f"Error invalidating cache for key {key}: {str(e)}")
            return False
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache performance statistics
        """
        return dict(self.cache_stats)
    
    def invalidate_all_cache(self) -> bool:
        """
        Invalidate entire cache (use with caution)
        """
        try:
            from storage.io import clear_cache_directory
            result = clear_cache_directory()
            self.logger.info("Entire cache invalidated")
            # Reset stats
            self.cache_stats = {"hits": 0, "misses": 0, "errors": 0, "computed": 0}
            return result
        except Exception as e:
            self.logger.error(f"Error invalidating entire cache: {str(e)}")
            return False


# Global instance
cache_service = CacheLayerService()


# Enhanced convenience function with the same signature as original for backward compatibility
def load_or_compute(key: str, 
                   compute_fn: Callable[[], Dict[str, Any]], 
                   source: Optional[List[str]] = None,
                   ttl_minutes: Optional[int] = None) -> Dict[str, Any]:
    """
    Enhanced cache layer function with additional quality features.
    
    Backward compatible with original function signature but adds:
    - TTL support
    - Better error handling
    - Enhanced fallback mechanisms
    - Security improvements
    - Logging and monitoring
    """
    return cache_service.load_or_compute(key, compute_fn, source, ttl_minutes)


# Additional utility functions
def invalidate_cache_key(key: str) -> bool:
    """Invalidate a specific cache key"""
    return cache_service.invalidate_cache(key)


def get_cache_statistics() -> Dict[str, int]:
    """Get cache performance statistics"""
    return cache_service.get_cache_stats()


def invalidate_all_cache() -> bool:
    """Invalidate entire cache (use with caution)"""
    return cache_service.invalidate_all_cache()


def warm_cache(key: str, data: Dict[str, Any], source: Optional[List[str]] = None) -> bool:
    """
    Pre-warm cache with specific data
    
    Args:
        key: Cache key to set
        data: Data to cache
        source: Source information for metadata
    
    Returns:
        Boolean indicating success
    """
    try:
        # Add metadata to the warm data
        enhanced_data = dict(data)
        enhanced_data["generated_at"] = datetime.utcnow().isoformat() + "Z"
        enhanced_data["source"] = source or ["cache_layer", "warm_cache", "fc-qm-codacy-004"]
        enhanced_data["cache_key"] = key
        enhanced_data["warmed_at"] = datetime.utcnow().isoformat() + "Z"
        
        save_json(key, enhanced_data, source=source or ["cache_layer", "warmed_data", "fc-qm-codacy-004"])
        cache_service.logger.info(f"Cache warmed for key: {key}")
        return True
    except Exception as e:
        cache_service.logger.error(f"Error warming cache for key {key}: {str(e)}")
        return False