from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def _parse_ts(raw: str) -> datetime | None:
    token = str(raw or "").strip()
    if not token:
        return None
    try:
        if token.endswith("Z"):
            token = token[:-1] + "+00:00"
        dt = datetime.fromisoformat(token)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def build_dependency_map(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    blocked_by = defaultdict(int)
    oldest_blocked_minutes = defaultdict(int)
    now = datetime.now(timezone.utc)

    task_index: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or task.get("id") or "").strip()
        if not task_id:
            continue
        task_index[task_id] = task
        nodes.append(
            {
                "id": task_id,
                "state": str(task.get("state") or "UNKNOWN").upper(),
                "owner": str(task.get("owner") or task.get("role") or "unknown").strip(),
                "batch_id": str(task.get("batch_id") or "").strip(),
            }
        )

    for task_id, task in task_index.items():
        deps = task.get("depends_on", [])
        if not isinstance(deps, list):
            deps = []
        state = str(task.get("state") or "").upper()
        updated_at = _parse_ts(str(task.get("updated_at") or ""))
        age_min = int((now - updated_at).total_seconds() // 60) if updated_at is not None else -1
        for dep in deps:
            dep_id = str(dep or "").strip()
            if not dep_id:
                continue
            edges.append({"from": task_id, "to": dep_id, "type": "depends_on"})
            if state in {"WAITING_DEP", "BLOCKED"}:
                blocked_by[dep_id] += 1
                if age_min >= 0:
                    oldest_blocked_minutes[dep_id] = max(oldest_blocked_minutes[dep_id], age_min)

    bottlenecks = []
    for dep_id, count in sorted(blocked_by.items(), key=lambda item: item[1], reverse=True)[:5]:
        bottlenecks.append(
            {
                "task_id": dep_id,
                "blocked_count": count,
                "oldest_blocked_minutes": oldest_blocked_minutes.get(dep_id, -1),
                "blocked_by": [edge["from"] for edge in edges if edge["to"] == dep_id][:12],
            }
        )

    summary = {
        "nodes": len(nodes),
        "edges": len(edges),
        "waiting_dep_tasks": sum(1 for node in nodes if node.get("state") == "WAITING_DEP"),
        "bottleneck_count": len(bottlenecks),
    }

    explanations = []
    for item in bottlenecks:
        explanations.append(
            f"{item['task_id']} blocks {item['blocked_count']} task(s)"
            + (
                f" (oldest wait {item['oldest_blocked_minutes']} min)"
                if int(item.get("oldest_blocked_minutes", -1)) >= 0
                else ""
            )
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "bottlenecks": bottlenecks,
        "summary": summary,
        "explanations": explanations,
    }
