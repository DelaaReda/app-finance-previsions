"""
Simple JSON storage with freshness metadata.
Never writes mock data. Only persists real pipeline outputs.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional, Dict

BASE_DIR = Path(__file__).resolve().parent.parent / "data"
BASE_DIR.mkdir(parents=True, exist_ok=True)

def _wrap(data: Any, source: Optional[str] = None, status: str = "OK") -> Dict[str, Any]:
    return {
        "last_update": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source": source or "unknown",
        "data": data,
    }

def save_json(data: Any, filename: str, source: Optional[str] = None, status: str = "OK") -> Path:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    fp = BASE_DIR / filename
    with fp.open("w", encoding="utf-8") as f:
        json.dump(_wrap(data, source, status), f, ensure_ascii=False)
    return fp

def load_json(filename: str) -> Optional[Dict[str, Any]]:
    fp = BASE_DIR / filename
    if not fp.exists():
        return None
    try:
        with fp.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
