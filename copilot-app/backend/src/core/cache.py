# src/core/cache.py
from __future__ import annotations
import time
from functools import wraps
from typing import Any, Callable, Dict, Tuple

class TTLCache:
    def __init__(self, ttl_seconds: int = 300, maxsize: int = 256):
        self.ttl = ttl_seconds
        self.maxsize = maxsize
        self._store: Dict[Tuple, Tuple[float, Any]] = {}

    def get(self, key: Tuple):
        now = time.time()
        val = self._store.get(key)
        if not val:
            return None
        ts, obj = val
        if now - ts > self.ttl:
            self._store.pop(key, None)
            return None
        return obj

    def set(self, key: Tuple, value: Any):
        if len(self._store) >= self.maxsize:
            # drop oldest naïvement
            self._store.pop(next(iter(self._store)))
        self._store[key] = (time.time(), value)

def ttl_cache(ttl_seconds: int = 300, maxsize: int = 256):
    cache = TTLCache(ttl_seconds, maxsize)
    def deco(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (fn.__name__, args, tuple(sorted(kwargs.items())))
            hit = cache.get(key)
            if hit is not None:
                return hit
            res = fn(*args, **kwargs)
            cache.set(key, res)
            return res
        return wrapper
    return deco