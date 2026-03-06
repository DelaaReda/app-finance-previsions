from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_orchestrator_root(root: Path) -> Path:
    primary = root / "docs" / "operations" / "orchestrator"
    if primary.exists():
        return primary
    legacy = root / "docs" / "orchestrator-ops"
    if legacy.exists():
        return legacy
    return primary


def collect_queue_workboard(root: Path) -> dict[str, Any]:
    orch_root = resolve_orchestrator_root(root)
    queue_file = orch_root / "priority-queue.json"
    workboard_file = orch_root / "parallel-workstreams.json"
    queue = read_json_file(queue_file)
    workboard = read_json_file(workboard_file)
    return {
        "source_root": str(orch_root),
        "queue_file": str(queue_file),
        "workboard_file": str(workboard_file),
        "queue": queue,
        "workboard": workboard,
    }
