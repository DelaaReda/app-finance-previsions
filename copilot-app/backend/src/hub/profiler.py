from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict


LOG_DIR = Path("logs/profiler")
LOG_FILE = LOG_DIR / "events.jsonl"


def _ensure_dir() -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def log_event(event_type: str, payload: Dict[str, Any]) -> None:
    """Append a JSONL event with utc timestamp.

    event_type: 'http' | 'callback' | 'subprocess' | 'info' | 'error'
    payload: any JSON-serializable dict
    """
    try:
        _ensure_dir()
        evt = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "type": str(event_type),
            "payload": payload,
        }
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    except Exception:
        # Never crash caller
        pass


def read_last(n: int = 200) -> list[dict]:
    try:
        if not LOG_FILE.exists():
            return []
        lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        out = []
        for line in lines[-max(0, n):]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out
    except Exception:
        return []


def clear() -> None:
    try:
        _ensure_dir()
        LOG_FILE.write_text("", encoding="utf-8")
    except Exception:
        pass

