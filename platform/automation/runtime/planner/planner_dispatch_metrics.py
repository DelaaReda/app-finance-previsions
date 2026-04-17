#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import resolve_orchestrator_read_path
from runtime.truth.dispatch_snapshot import build_stable_planner_dispatch_snapshot
from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot


FALLBACK_MARKERS = (
    "falling back to embedded",
    "failovererror",
    "gateway agent failed",
)
INVALID_RESULT_MARKERS = (
    "invalid_subagent_result",
    "subagent_invalid_result",
    "start_banner_only",
    "empty_payload",
    "delivery_evidence_incomplete",
    "missing bearer or basic authentication",
    "401 unauthorized",
    "unexpected status 401 unauthorized",
    "transport channel",
    "worker quit with fatal",
    "failed to refresh available models",
    "openai codex v0.",
    "research preview",
    "session id:",
)
TIMEOUT_LIKE_MARKERS = ("timeout", "timed out", "stale_no_result", "deadline", "no result")
DONE_STATES = {"done", "closed"}


def _parse_iso(raw: Any) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _recent_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("recent", [])
    return rows if isinstance(rows, list) else []


def _active_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("active", [])
    return rows if isinstance(rows, list) else []


def _row_status(row: dict[str, Any]) -> str:
    return str(row.get("status", "")).strip().lower()


def _is_fallback_like(root: Path, row: dict[str, Any]) -> bool:
    backend = str(row.get("backend", "")).strip().lower()
    if backend == "qwen":
        return True
    subagent_id = str(row.get("subagent_id", "") or row.get("target_agent_id", "")).strip()
    if not subagent_id:
        return False
    raw_path = resolve_orchestrator_read_path(root, f"planner-subagents-results/{subagent_id}.raw.txt")
    lowered = _read_text(raw_path).lower()
    return any(marker in lowered for marker in FALLBACK_MARKERS)


def _failure_mode(row: dict[str, Any]) -> str:
    token = " | ".join(
        [
            str(row.get("blocking_issue", "")),
            str(row.get("summary", "")),
        ]
    ).strip().lower()
    if any(marker in token for marker in INVALID_RESULT_MARKERS):
        return "invalid_result"
    if any(marker in token for marker in TIMEOUT_LIKE_MARKERS):
        return "timeout"
    return "other" if token else "unknown"


def _latest_row(payload: dict[str, Any]) -> dict[str, Any]:
    active = _active_rows(payload)
    if active:
        return active[0] if isinstance(active[0], dict) else {}
    recent = _recent_rows(payload)
    if recent:
        return recent[0] if isinstance(recent[0], dict) else {}
    return {}


def _load_workboard_tasks(root: Path) -> list[dict[str, Any]]:
    path = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
    payload = _read_json(path) if path.exists() else {}
    tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
    return tasks if isinstance(tasks, list) else []


def _registry_sort_key(item: dict[str, Any]) -> float:
    for key in ("last_update_at", "updated_at", "finished_at", "created_at"):
        dt = _parse_iso(item.get(key))
        if dt is not None:
            return dt.timestamp()
    return 0.0


def _compat_workboard_counters(root: Path) -> dict[str, int]:
    tasks = _load_workboard_tasks(root)
    long_running = 0
    no_progress = 0
    recovery_required = 0
    orphaned = 0
    for item in tasks:
        if not isinstance(item, dict):
            continue
        state = str(item.get("state", "")).strip().lower()
        if state in DONE_STATES:
            continue
        role = str(item.get("role", "")).strip().lower()
        if role != "dev":
            continue
        execution_state = str(item.get("dev_execution_state", "")).strip().lower()
        if execution_state == "long_running":
            long_running += 1
        if execution_state == "no_progress":
            no_progress += 1
        if execution_state == "orphaned":
            orphaned += 1
        if bool(item.get("dev_recovery_required")) or bool(item.get("recovery_required")):
            recovery_required += 1
    return {
        "long_running_dev_count": long_running,
        "dev_no_progress_count": no_progress,
        "dev_orphaned_count": orphaned,
        "recovery_required_count": recovery_required,
    }


def _registry_fallback_metrics(root: Path, *, recent_limit: int) -> dict[str, Any]:
    path = resolve_orchestrator_read_path(root, "planner-subagents-registry.json")
    payload = _read_json(path) if path.exists() else {}
    rows = payload.get("subagents", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []
    normalized = [row for row in rows if isinstance(row, dict)]
    normalized.sort(key=_registry_sort_key, reverse=True)
    active = [row for row in normalized if _row_status(row) in {"running", "pending", "spawned"}]
    recent = [row for row in normalized if _row_status(row) not in {"running", "pending", "spawned"}][: max(1, recent_limit)]
    recent_success_count = sum(1 for row in recent if _row_status(row) in {"completed", "merged", "done", "pass", "ok", "success"})
    recent_failed_count = sum(1 for row in recent if _row_status(row) == "failed")
    recent_blocked_count = sum(1 for row in recent if _row_status(row) in {"blocked"})
    recent_fallback_like_count = sum(1 for row in recent if _is_fallback_like(root, row))
    latest = _latest_row({"active": active, "recent": recent})
    latest_failure_row = next(
        (
            row
            for row in recent
            if isinstance(row, dict) and _row_status(row) in {"failed", "blocked", "merged", "done", "completed"}
        ),
        {},
    )
    success_denominator = recent_success_count + recent_failed_count + recent_blocked_count
    return {
        "source": "compat_registry_fallback",
        "planner_dispatch_source": "compat_registry_fallback",
        "decision_capable": False,
        "registry_secondary_only": True,
        "legacy_registry_secondary_only": True,
        "registry_path": "secondary_compat_only",
        "secondary_registry_path": "secondary_compat_only",
        "active": active[:8],
        "active_count": len(active),
        "recent": recent,
        "recent_total": len(recent),
        "recent_success_count": recent_success_count,
        "recent_failed_count": recent_failed_count,
        "recent_blocked_count": recent_blocked_count,
        "recent_fallback_like_count": recent_fallback_like_count,
        "recent_success_rate": (recent_success_count / success_denominator) if success_denominator else 1.0,
        "latest_status": _row_status(latest),
        "latest_owner_task_id": str(latest.get("owner_task_id", "")).strip(),
        "latest_fallback_like": bool(latest) and _is_fallback_like(root, latest),
        "latest_failure_mode": _failure_mode(latest_failure_row) if latest_failure_row else "unknown",
        "recent_invalid_result_count": sum(1 for row in recent if _failure_mode(row) == "invalid_result"),
        "recent_timeout_like_count": sum(1 for row in recent if _failure_mode(row) == "timeout"),
        "recovering": bool(active) and (recent_failed_count > 0 or recent_blocked_count > 0),
        "status": "ok" if active else ("degraded" if (recent_failed_count > 0 or recent_blocked_count > 0) else "ok"),
        "planner_state": "waiting_on_agents" if active else ("blocked" if (recent_failed_count > 0 or recent_blocked_count > 0) else "idle"),
        "compat_registry_present": path.exists(),
    }


def build_planner_dispatch_metrics(root: Path, *, recent_limit: int = 12) -> dict[str, Any]:
    root = Path(root)
    payload = build_stable_planner_dispatch_snapshot(root, recent_limit=recent_limit)
    if not isinstance(payload, dict):
        return {"ok": False, "enabled": False, "status": "error", "source": "dispatch_snapshot_invalid"}

    runtime_truth = build_runtime_truth_snapshot(root, state_limit=max(24, recent_limit * 2), event_limit=max(24, recent_limit * 2))
    metrics = dict(payload)
    metrics.setdefault("ok", True)
    metrics.setdefault("enabled", True)
    metrics.setdefault("source", str(metrics.get("source", "event_store") or "event_store"))
    metrics.setdefault("planner_dispatch_source", metrics.get("source", "event_store"))
    metrics.setdefault("decision_capable", False)
    metrics.setdefault("registry_secondary_only", True)
    metrics["event_store_primary"] = bool(runtime_truth.get("event_store_primary", False))
    metrics["runtime_truth_source"] = str(runtime_truth.get("runtime_truth_source", "fallback"))
    metrics["projection_secondary_only"] = not bool(runtime_truth.get("event_store_primary", False))
    metrics["legacy_registry_secondary_only"] = True
    if bool(metrics.get("event_store_primary", False)):
        metrics["compat_registry_present"] = False
        metrics["registry_path"] = "secondary_compat_only"
        metrics["secondary_registry_path"] = "secondary_compat_only"
        metrics["decision_capable"] = False

    recent = _recent_rows(metrics)
    active = _active_rows(metrics)
    if (not bool(metrics.get("event_store_primary", False))) and not active and not recent:
        metrics.update(_registry_fallback_metrics(root, recent_limit=recent_limit))
        recent = _recent_rows(metrics)
        active = _active_rows(metrics)
    compat_fallback_count = sum(1 for row in recent if isinstance(row, dict) and _is_fallback_like(root, row))
    metrics["recent_fallback_like_count"] = compat_fallback_count

    latest = _latest_row(metrics)
    metrics["latest_fallback_like"] = bool(latest) and _is_fallback_like(root, latest)

    latest_failure_row = next(
        (
            row
            for row in recent
            if isinstance(row, dict) and _row_status(row) in {"failed", "blocked", "merged", "done", "completed"}
        ),
        {},
    )
    if latest_failure_row:
        metrics["latest_failure_mode"] = _failure_mode(latest_failure_row)

    if bool(metrics.get("event_store_primary", False)):
        metrics.setdefault("long_running_dev_count", 0)
        metrics.setdefault("dev_no_progress_count", 0)
        metrics.setdefault("dev_orphaned_count", 0)
        metrics.setdefault("recovery_required_count", 0)
        if int(metrics.get("active_count", 0) or 0) == 0 and int(metrics.get("ready_total", 0) or 0) == 0:
            metrics["status"] = "ok"
            metrics["planner_state"] = "idle"
    else:
        compat_counters = _compat_workboard_counters(root)
        metrics.update(compat_counters)
        if any(int(metrics.get(key, 0) or 0) > 0 for key in ("long_running_dev_count", "dev_no_progress_count", "dev_orphaned_count", "recovery_required_count")):
            metrics["recovering"] = True

    return metrics
