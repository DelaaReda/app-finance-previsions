from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


def build_system_summary(
    *,
    timeline: list[dict[str, Any]],
    intentions: dict[str, Any],
    dependency_map: dict[str, Any],
    active_tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=15)
    changes: list[str] = []
    by_role: dict[str, int] = {}
    for event in timeline:
        if not isinstance(event, dict):
            continue
        ts = _parse_ts(str(event.get("ts") or ""))
        if ts is None or ts < cutoff:
            continue
        role = str(event.get("role") or "unknown")
        by_role[role] = by_role.get(role, 0) + 1
        action = str(event.get("action") or "NOOP")
        task_id = str(event.get("task_id") or event.get("batch_id") or "")
        changes.append(f"{role}: {action} {task_id}".strip())

    bottlenecks = dependency_map.get("bottlenecks", []) if isinstance(dependency_map, dict) else []
    current_bottleneck = "none"
    if isinstance(bottlenecks, list) and bottlenecks:
        top = bottlenecks[0]
        current_bottleneck = f"{top.get('task_id', 'unknown')} ({top.get('blocked_count', 0)} blocked)"

    recommended = "monitor"
    if isinstance(bottlenecks, list) and bottlenecks:
        top = bottlenecks[0]
        recommended = f"unblock {top.get('task_id', 'unknown')}"
    else:
        next_dev = next((row for row in active_tasks if str(row.get("owner")) == "dev" and str(row.get("state")) in {"READY", "READY_DEV"}), None)
        if next_dev:
            recommended = f"dev claim {next_dev.get('task_id', 'unknown')}"

    return {
        "what_changed_last_15m": changes[:12],
        "events_by_role_last_15m": by_role,
        "current_bottleneck": current_bottleneck,
        "recommended_next_action": recommended,
        "intentions": intentions.get("intentions", {}) if isinstance(intentions, dict) else {},
        "decision_trace_quality": intentions.get("decision_trace_quality", {}) if isinstance(intentions, dict) else {},
    }
