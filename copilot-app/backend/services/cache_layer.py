from typing import Callable, Dict, Any, Optional
from storage.io import load_json, save_json
import time


def load_or_compute(key: str, compute_fn: Callable[[], Dict[str, Any]], source: Optional[list] = None):
    """
    Load data from cache or compute and save it.
    """
    snap = load_json(key)
    if snap and snap.get("payload") is not None:
        return snap
    data = compute_fn()
    return save_json(key, data, source=source)