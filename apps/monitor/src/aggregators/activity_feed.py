from __future__ import annotations

from collections import defaultdict
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


def build_activity_summary(timeline: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff_1h = now - timedelta(hours=1)
    cutoff_6h = now - timedelta(hours=6)
    events_last_1h = 0
    events_last_6h = 0
    tasks_progressed: set[str] = set()
    last_action_by_role: dict[str, dict[str, str]] = {}
    blockers = defaultdict(int)

    for event in timeline:
        if not isinstance(event, dict):
            continue
        ts = _parse_ts(str(event.get("ts") or ""))
        if ts is not None:
            if ts >= cutoff_1h:
                events_last_1h += 1
                action = str(event.get("action") or "").upper()
                if action in {"PROGRESS", "PATCH", "TEST", "COMPLETE"}:
                    task_id = str(event.get("task_id") or "").strip()
                    if task_id:
                        tasks_progressed.add(task_id)
            if ts >= cutoff_6h:
                events_last_6h += 1
        role = str(event.get("role") or "").strip().lower()
        if role and role not in last_action_by_role:
            last_action_by_role[role] = {
                "action": str(event.get("action") or "NOOP"),
                "task_id": str(event.get("task_id") or ""),
                "ts": str(event.get("ts") or ""),
                "reason_code": str(event.get("reason_code") or ""),
            }
        if str(event.get("action") or "").upper() == "BLOCKED":
            key = str(event.get("task_id") or event.get("batch_id") or "unknown")
            blockers[key] += 1

    current_bottleneck = "none"
    if blockers:
        current_bottleneck = max(blockers.items(), key=lambda item: item[1])[0]

    return {
        "events_last_1h": events_last_1h,
        "events_last_6h": events_last_6h,
        "tasks_progressed_last_1h": len(tasks_progressed),
        "last_action_by_role": last_action_by_role,
        "current_bottleneck": current_bottleneck,
    }


def build_throughput(timeline: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff_1h = now - timedelta(hours=1)
    completed = 0
    artifacts = 0

    for event in timeline:
        if not isinstance(event, dict):
            continue
        ts = _parse_ts(str(event.get("ts") or ""))
        if ts is None or ts < cutoff_1h:
            continue
        action = str(event.get("action") or "").upper()
        if action == "COMPLETE":
            completed += 1
        refs = event.get("artifact_refs")
        if isinstance(refs, list) and any(str(v).strip() for v in refs):
            artifacts += 1

    delivery_rate = round(float(completed), 2)
    return {
        "tasks_completed_last_hour": completed,
        "artifacts_generated_last_hour": artifacts,
        "delivery_rate": delivery_rate,
    }
