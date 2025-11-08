from pathlib import Path
import json, time, datetime as dt
from typing import Dict, Any, Optional, List

# Use absolute path from backend root to avoid CWD issues
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
BASE = _BACKEND_ROOT / "data"  # gitignored
BASE.mkdir(exist_ok=True, parents=True)

def save_json(key: str, payload: Dict[str, Any], source: Optional[List[str]] = None, version: str = "v1") -> None:
    """
    Save payload to JSON file with metadata (matching task specs).
    Supports nested paths like "dashboard/kpis" -> data/dashboard/kpis.json
    """
    final_payload = dict(payload)
    final_payload["freshness"] = dt.datetime.utcnow().isoformat()+"Z"
    final_payload["source"] = source or []
    final_payload["version"] = version
    
    # Handle nested paths (e.g., "dashboard/kpis" -> data/dashboard/kpis.json)
    filepath = BASE / f"{key}.json"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(final_payload, ensure_ascii=False))

def load_json(key: str) -> Optional[Dict[str, Any]]:
    """
    Load JSON from file, return None if not found (matching task specs).
    Supports nested paths like "dashboard/kpis" -> data/dashboard/kpis.json
    """
    p = BASE / f"{key}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, IOError) as e:
        # Log error but return None to avoid breaking the app
        import logging
        logging.getLogger(__name__).warning(f"Error loading {key}: {e}")
        return None