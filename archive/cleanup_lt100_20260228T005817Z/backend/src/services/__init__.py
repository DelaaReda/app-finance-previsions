"""
Services module that provides access to the backend services functionality.
This file exists in src/services to make it importable from other modules in src.
"""
import sys
import os
from pathlib import Path
import asyncio

# Add the parent backend directory to the Python path so we can access backend-level modules
backend_dir = Path(__file__).resolve().parent.parent  # This is the 'src' parent (backend/)
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Now import from the actual backend services module
try:
    from services.cache_service import load_or_compute
except ImportError as e:
    print(f"Warning: Could not import from backend cache_service: {e}")
    # Provide fallback implementation
    async def load_or_compute(key, compute_fn, sources=None):
        """Fallback implementation"""
        if asyncio.iscoroutinefunction(compute_fn):
            return await compute_fn()
        else:
            return compute_fn()