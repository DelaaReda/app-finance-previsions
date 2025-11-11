"""
Memory Cache Module for Finance Copilot
Task: BE-007 - Memory cache for frequent endpoints
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import time
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import json
from functools import wraps


class LRUCache:
    """
    Simple LRU Cache implementation for API responses with file modification tracking.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):  # 5 min TTL by default
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float, Optional[float]]] = {}  # (value, timestamp, file_mod_time)
        self.access_times: Dict[str, float] = {}
        self.lock = threading.RLock()  # Thread-safe operations
    
    def _get_file_mod_time(self, *file_paths) -> Optional[float]:
        """Get the latest modification time among provided file paths."""
        mod_time = None
        for path_str in file_paths:
            try:
                path = Path(path_str)
                if path.exists():
                    current_mod = path.stat().st_mtime
                    if mod_time is None or current_mod > mod_time:
                        mod_time = current_mod
            except:
                continue  # Skip if file doesn't exist or error occurs
        return mod_time
    
    def get(self, key: str, file_paths: Optional[Tuple[str, ...]] = None) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
            file_paths: Optional file paths whose modification time affects cache validity
        """
        with self.lock:
            if key not in self.cache:
                return None
            
            value, timestamp, file_mod_time = self.cache[key]
            
            # Check TTL expiration
            if time.time() - timestamp > self.ttl_seconds:
                del self.cache[key]
                del self.access_times[key]
                return None
            
            # Check if related files have been updated since caching
            if file_paths:
                current_file_mod_time = self._get_file_mod_time(*file_paths)
                if current_file_mod_time and file_mod_time and current_file_mod_time > file_mod_time:
                    # File has been modified since cache was created, invalidate cache
                    del self.cache[key]
                    del self.access_times[key]
                    return None
            
            # Update access time for LRU tracking
            self.access_times[key] = time.time()
            return value
    
    def set(self, key: str, value: Any, file_paths: Optional[Tuple[str, ...]] = None):
        """
        Set value in cache with optional file modification tracking.
        
        Args:
            key: Cache key
            value: Value to cache
            file_paths: Optional file paths to track for cache invalidation
        """
        with self.lock:
            # Get current file modification time if paths provided
            file_mod_time = self._get_file_mod_time(*file_paths) if file_paths else None
            
            # Check if cache is at max capacity
            if len(self.cache) >= self.max_size:
                # Remove least recently used item (based on access time)
                lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
                del self.cache[lru_key]
                del self.access_times[lru_key]
            
            # Store value with current timestamp and file modification time
            self.cache[key] = (value, time.time(), file_mod_time)
            self.access_times[key] = time.time()
    
    def invalidate(self, key: str):
        """Remove specific key from cache."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
    
    def clear(self):
        """Clear entire cache."""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()


# Global instance of LRU cache
memory_cache = LRUCache(max_size=100, ttl_seconds=300)  # 100 items, 5 min TTL


def cache_with_ttl(ttl_seconds: int = 300, cache_key_prefix: str = "", track_files: Optional[Tuple[str, ...]] = None):
    """
    Decorator for caching function results in memory with TTL and file modification tracking.
    
    Args:
        ttl_seconds: Time to live for cache entries (seconds)
        cache_key_prefix: Prefix to add to cache keys for namespace separation
        track_files: File paths to check for changes (cache invalidates if any file changes)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{cache_key_prefix}:{func.__module__}:{func.__name__}:"
            
            # Hash the arguments to create a unique key part
            args_key = hashlib.md5(str((args, kwargs)).encode()).hexdigest()
            cache_key += args_key
            
            # Check cache first
            cached_result = memory_cache.get(cache_key, track_files)
            if cached_result is not None:
                return cached_result
            
            # Execute function if not in cache
            result = func(*args, **kwargs)
            
            # Store result in cache
            memory_cache.set(cache_key, result, track_files)
            
            return result
        return wrapper
    return decorator


def cache_key_from_params(func_name: str, **params) -> str:
    """
    Generate a cache key from function name and parameters.
    
    Args:
        func_name: Name of the function
        **params: Parameters to include in the key
        
    Returns:
        String cache key
    """
    # Sort params to ensure consistent ordering
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    params_str = str(sorted_params)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()
    
    return f"{func_name}:{params_hash}"


def invalidate_cache_prefix(prefix: str):
    """
    Invalidate all cache entries with the given prefix.
    
    Args:
        prefix: Prefix of keys to invalidate
    """
    with memory_cache.lock:
        keys_to_remove = [key for key in memory_cache.cache.keys() if key.startswith(prefix)]
        for key in keys_to_remove:
            memory_cache.invalidate(key)


# Context manager for bulk cache operations
class CacheManager:
    """Context manager for cache operations that may need to be paused during updates."""
    
    def __init__(self):
        self.cache = memory_cache
    
    def __enter__(self):
        return self.cache
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # No special cleanup needed
        pass


# Shortcut functions for common cache operations
def cache_get(key: str, files: Optional[Tuple[str, ...]] = None) -> Optional[Any]:
    """Shortcut to get value from cache."""
    return memory_cache.get(key, files)

def cache_set(key: str, value: Any, files: Optional[Tuple[str, ...]] = None):
    """Shortcut to set value in cache."""
    memory_cache.set(key, value, files)

def cache_invalidate(key: str):
    """Shortcut to invalidate specific cache key."""
    memory_cache.invalidate(key)

def cache_clear():
    """Shortcut to clear entire cache."""
    memory_cache.clear()