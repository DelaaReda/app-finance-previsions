# src/backend/storage/__init__.py
# This module re-exports the json_storage functionality from the backend directory
# to make it accessible from the src directory

import sys
from pathlib import Path

# Add the backend root directory to the path to import from backend directories
backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

try:
    from storage.json_storage import load_json, save_json
except ImportError:
    # Fallback in case the import doesn't work
    def load_json(key):
        return None
    
    def save_json(key, data, sources=None):
        return False