from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = REPO_ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from orchestrator_paths import resolve_orchestrator_read_path, runtime_state_root


def read_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_orchestrator_root(root: Path) -> Path:
    queue_file = resolve_orchestrator_read_path(root, "priority-queue.json")
    workboard_file = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
    if queue_file.exists():
        return queue_file.parent
    if workboard_file.exists():
        return workboard_file.parent
    return runtime_state_root(root)


def collect_queue_workboard(root: Path) -> dict[str, Any]:
    orch_root = resolve_orchestrator_root(root)
    queue_file = resolve_orchestrator_read_path(root, "priority-queue.json")
    workboard_file = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
    queue = read_json_file(queue_file)
    workboard = read_json_file(workboard_file)
    return {
        "source_root": str(orch_root),
        "queue_file": str(queue_file),
        "workboard_file": str(workboard_file),
        "queue": queue,
        "workboard": workboard,
    }
