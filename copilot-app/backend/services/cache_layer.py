from typing import Callable, Dict, Any, Optional
from storage.io import load_json, save_json

def load_or_compute(key: str, compute_fn: Callable[[], Dict[Any, Any]], source: Optional[list[str]] = None):
    """
    Load cached data or compute fresh if not available (matching task specs).
    """
    snapshot = load_json(key)
    if snapshot: 
        return snapshot  # never-empty
    data = compute_fn()  # <- vrai calcul
    save_json(key, data, source=["compute:"+key] if source is None else source)
    return load_json(key)