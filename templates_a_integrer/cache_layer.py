"""
Cache layer: serve last valid snapshot immediately; compute in background elsewhere.
If no snapshot exists yet, return structured payload with explicit status.
"""
from __future__ import annotations
from typing import Callable, Dict, Any, Optional
from backend.storage.base import load_json, save_json

def load_or_compute(key: str, compute_fn: Callable[[], Dict[str, Any]], *, source: str = "pipeline") -> Dict[str, Any]:
    snap = load_json(f"{key}.json")
    if snap and isinstance(snap, dict) and "data" in snap:
        return snap
    # No prior snapshot → compute once synchronously to create the first baseline
    result = compute_fn() or {}
    # Expect compute_fn to return the *final* data payload (not wrapped)
    save_json(result, f"{key}.json", source=source, status="OK" if result else "NO_DATA_YET")
    snap = load_json(f"{key}.json")
    return snap or {"status": "ERROR", "data": {}}
