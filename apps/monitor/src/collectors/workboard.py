from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _canonical_role(raw: str) -> str:
    token = str(raw or "").strip().lower()
    if not token:
        return "unknown"
    alias = {
        "analyst": "planner",
        "architect": "planner",
        "po": "planner",
        "backend_engineer": "dev",
        "frontend_engineer": "dev",
        "data_analyst": "dev",
        "qa": "dev",
        "tester": "dev",
        "po_scrum_master": "scrum_master",
    }
    return alias.get(token, token)


def _batch_prefix(task_id: str) -> str:
    token = str(task_id or "").strip().upper()
    if token.startswith("BATCH-"):
        chunks = token.split("-")
        if len(chunks) >= 2:
            return f"{chunks[0]}-{chunks[1]}"
    return ""


def load_workboard_snapshot(root: Path) -> dict[str, Any]:
    workboard_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    queue_path = root / "docs" / "operations" / "orchestrator" / "priority-queue.json"
    wb = _read_json(workboard_path)
    q = _read_json(queue_path)
    tasks_in = wb.get("tasks", []) if isinstance(wb.get("tasks"), list) else []

    tasks: list[dict[str, Any]] = []
    for item in tasks_in:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("id") or "").strip()
        if not task_id:
            continue
        deps = item.get("deps") or item.get("depends_on") or item.get("dependencies") or []
        if not isinstance(deps, list):
            deps = [str(deps)] if str(deps).strip() else []
        state = str(item.get("state") or "").strip().upper() or "UNKNOWN"
        role = _canonical_role(str(item.get("assignee") or item.get("role") or ""))
        stream_id = str(item.get("stream_id") or _batch_prefix(task_id)).strip()
        batch_id = _batch_prefix(task_id) or stream_id
        tasks.append(
            {
                "task_id": task_id,
                "batch_id": batch_id,
                "stream_id": stream_id,
                "state": state,
                "owner": role,
                "title": str(item.get("title") or "").strip(),
                "priority": str(item.get("priority") or "").strip(),
                "depends_on": [str(dep).strip() for dep in deps if str(dep).strip()],
                "created_at": str(item.get("created_at") or "").strip(),
                "started_at": str(item.get("started_at") or "").strip(),
                "updated_at": str(item.get("updated_at") or "").strip(),
                "completed_at": str(item.get("completed_at") or "").strip(),
            }
        )

    queue_items = q.get("items", []) if isinstance(q.get("items"), list) else []
    return {
        "tasks": tasks,
        "queue_items": queue_items,
        "paths": {
            "workboard": str(workboard_path),
            "queue": str(queue_path),
        },
    }
