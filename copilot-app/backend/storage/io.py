from pathlib import Path
import json, time, datetime as dt
from typing import Dict, Any, Optional, List

BASE = Path("data")  # gitignored
BASE.mkdir(exist_ok=True)

def save_json(key: str, payload: Dict[str, Any], source: Optional[List[str]] = None, version: str = "v1") -> None:
    """
    Save payload to JSON file with metadata (matching task specs).
    """
    final_payload = dict(payload)
    final_payload["freshness"] = dt.datetime.utcnow().isoformat()+"Z"
    final_payload["source"] = source or []
    final_payload["version"] = version
    (BASE / f"{key}.json").write_text(json.dumps(final_payload, ensure_ascii=False))

def load_json(key: str) -> Optional[Dict[str, Any]]:
    """
    Load JSON from file, return None if not found (matching task specs).
    """
    p = BASE / f"{key}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())