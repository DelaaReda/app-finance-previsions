from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any


STATE_BASE_PROGRESS = {
    "WAITING_DEP": 5,
    "PLANNED": 10,
    "READY": 15,
    "READY_DEV": 15,
    "READY_PLANNER": 15,
    "IN_PROGRESS": 35,
    "REVIEW": 75,
    "DONE": 100,
    "CLOSED": 100,
    "PASS": 100,
}


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


def _event_index_by_task(timeline: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    idx: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in timeline:
        if not isinstance(event, dict):
            continue
        task_id = str(event.get("task_id") or "").strip()
        if not task_id:
            continue
        idx[task_id].append(event)
    for task_id, events in idx.items():
        events.sort(key=lambda row: str(row.get("ts") or ""), reverse=True)
    return idx


def _current_step(events: list[dict[str, Any]], default_state: str) -> str:
    if not events:
        return f"state:{default_state.lower()}"
    top = events[0]
    action = str(top.get("action") or "NOOP").upper()
    reason = str(top.get("reason_code") or "").strip().lower()
    if reason:
        return f"{action.lower()}:{reason[:42]}"
    return action.lower()


def _artifact_output(events: list[dict[str, Any]]) -> str:
    for event in events:
        refs = event.get("artifact_refs")
        if isinstance(refs, list):
            for ref in refs:
                token = str(ref or "").strip()
                if token:
                    return token
    return ""


def _progress_score(state: str, events: list[dict[str, Any]]) -> int:
    base = STATE_BASE_PROGRESS.get(state, 10)
    transitions = 0
    evidence = 0
    artifacts = 0
    for event in events[:20]:
        action = str(event.get("action") or "").upper()
        if action in {"PROGRESS", "PATCH", "TEST", "COMPLETE", "RECOVER"}:
            transitions += 1
        if action in {"PATCH", "TEST", "COMPLETE"}:
            evidence += 1
        refs = event.get("artifact_refs")
        if isinstance(refs, list) and any(str(v).strip() for v in refs):
            artifacts += 1
    score = base
    score += min(40, transitions * 8)
    score += min(30, evidence * 10)
    score += min(30, artifacts * 10)
    return max(0, min(100, score))


def _stalled_reason(state: str, events: list[dict[str, Any]]) -> tuple[bool, str]:
    if state == "WAITING_DEP":
        return True, "dependency_gate"
    if not events:
        return True, "no_evidence_delta"
    now = datetime.now(timezone.utc)
    cutoff_90m = now - timedelta(minutes=90)
    claims = 0
    progress = 0
    for event in events[:25]:
        ts = _parse_ts(str(event.get("ts") or ""))
        if ts is None or ts < cutoff_90m:
            continue
        action = str(event.get("action") or "").upper()
        if action == "CLAIM":
            claims += 1
        if action in {"PROGRESS", "PATCH", "TEST", "COMPLETE", "RECOVER"}:
            progress += 1
    if claims >= 2 and progress == 0:
        return True, "claim_loop"
    return False, ""


def build_active_tasks(
    *,
    tasks: list[dict[str, Any]],
    timeline: list[dict[str, Any]],
    limit: int = 80,
) -> list[dict[str, Any]]:
    events_by_task = _event_index_by_task(timeline)
    active_states = {
        "PLANNED",
        "READY",
        "READY_DEV",
        "READY_PLANNER",
        "IN_PROGRESS",
        "WAITING_DEP",
        "REVIEW",
        "BLOCKED",
    }
    rows: list[dict[str, Any]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        state = str(task.get("state") or "").upper()
        if state not in active_states:
            continue
        task_id = str(task.get("task_id") or task.get("id") or "").strip()
        if not task_id:
            continue
        events = events_by_task.get(task_id, [])
        current_step = _current_step(events, state)
        artifact_output = _artifact_output(events)
        progress_pct = _progress_score(state, events)
        stalled, stalled_reason = _stalled_reason(state, events)
        if not stalled_reason:
            stalled_reason = str(task.get("stalled_reason") or task.get("blocked_reason") or "").strip()
            if stalled_reason:
                stalled = True
        rows.append(
            {
                "task_id": task_id,
                "batch_id": str(task.get("batch_id") or "").strip(),
                "owner": str(task.get("owner") or task.get("role") or "unknown").strip(),
                "state": state,
                "started_at": str(task.get("started_at") or "").strip(),
                "last_update": str(task.get("updated_at") or "").strip(),
                "progress_pct": progress_pct,
                "current_step": current_step,
                "artifact_output": artifact_output,
                "stalled": bool(stalled),
                "stalled_reason": stalled_reason,
                "title": str(task.get("title") or "").strip(),
            }
        )

    rows.sort(
        key=lambda item: (
            0 if str(item.get("state") or "") == "IN_PROGRESS" else 1,
            -int(item.get("progress_pct") or 0),
            str(item.get("task_id") or ""),
        )
    )
    return rows[: max(10, min(int(limit), 300))]
