# src/backend/services/__init__.py
# This module re-exports the cache_service functionality from the backend directory
# to make it accessible from the src directory

import sys
from pathlib import Path
import asyncio

# Add the backend root directory to the path to import from backend directories
backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

try:
    from services.cache_service import load_or_compute
except ImportError:
    # Fallback in case the import doesn't work
    async def load_or_compute(key, compute_fn, sources=None):
        # Simple fallback that just runs compute_fn
        return await compute_fn() if asyncio.iscoroutinefunction(compute_fn) else compute_fn()