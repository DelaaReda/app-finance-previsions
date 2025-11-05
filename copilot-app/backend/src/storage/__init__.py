"""
Storage module that provides access to the backend storage functionality.
This file exists in src/storage to make it importable from other modules in src.
"""
import sys
import os
from pathlib import Path

# Resolve backend root (two levels up from src/storage)
backend_root = Path(__file__).resolve().parents[2]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Now import from the actual backend storage module, avoiding name shadowing
try:
    import importlib.util as _iu
    backend_storage_path = backend_root / 'storage' / 'json_storage.py'
    spec = _iu.spec_from_file_location('backend_storage_json', str(backend_storage_path))
    if spec and spec.loader:
        _mod = _iu.module_from_spec(spec)
        spec.loader.exec_module(_mod)  # type: ignore[attr-defined]
        load_json = getattr(_mod, 'load_json')  # type: ignore[assignment]
        save_json = getattr(_mod, 'save_json')  # type: ignore[assignment]
    else:
        raise ImportError('cannot load backend storage json_storage')
except Exception as e:  # pragma: no cover
    print(f"Warning: Could not import from backend storage: {e}")
    def load_json(key):
        return None
    def save_json(key, data, sources=None):
        return False
