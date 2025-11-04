from pathlib import Path
import json
import time
from typing import Dict, Any, Optional, List

DATA_DIR = Path(__file__).resolve().parents[1] / "data"  # backend/data/
DATA_DIR.mkdir(exist_ok=True)

def _path(key: str) -> Path:
    return DATA_DIR / f"{key}.json"

def save_json(key: str, payload: Dict[str, Any], source: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Save payload to JSON file with metadata.
    """
    now = int(time.time())
    doc = {
        "last_update": now,
        "source": source or [],
        "version": 1,
        "payload": payload
    }
    _path(key).write_text(json.dumps(doc, ensure_ascii=False, indent=2))
    return doc

def load_json(key: str) -> Optional[Dict[str, Any]]:
    """
    Load JSON from file, return None if not found.
    """
    p = _path(key)
    if not p.exists():
        return None
    return json.loads(p.read_text())

def last_updates_info() -> Dict[str, Any]:
    """
    Get info about last updates for key data files.
    """
    info = {}
    for name in ["news_feed", "forecasts", "brief_weekly", "backtests"]:
        d = load_json(name)
        if d:
            info[name] = d.get("last_update")
    return info