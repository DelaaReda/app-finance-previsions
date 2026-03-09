#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import resolve_orchestrator_read_path


ACTIVE_STATUSES = {"spawned", "running"}
SUCCESS_STATUSES = {"completed", "merged", "done", "pass", "ok", "success"}
BLOCKED_STATUSES = {"blocked"}
DONE_STATES = {"done", "closed"}
FALLBACK_MARKERS = ("falling back to embedded", "failovererror", "gateway agent failed")
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


def _recent_sort_key(item: dict[str, Any]) -> float:
    for key in ("last_update_at", "merged_at", "finished_at", "created_at"):
        dt = _parse_iso(item.get(key))
        if dt is not None:
            return dt.timestamp()
    return 0.0


def _is_fallback_like(root: Path, subagent_id: str) -> bool:
    raw_path = root / "docs" / "operations" / "orchestrator" / "planner-subagents-results" / f"{subagent_id}.raw.txt"
    raw_text = _read_text(raw_path).lower()
    return any(marker in raw_text for marker in FALLBACK_MARKERS)


def _failure_mode(item: dict[str, Any]) -> str:
    token = " | ".join(
        [
            str(item.get("blocking_issue", "")),
            str(item.get("summary", "")),
        ]
    ).strip().lower()
    if any(marker in token for marker in INVALID_RESULT_MARKERS):
        return "invalid_result"
    if any(marker in token for marker in TIMEOUT_LIKE_MARKERS):
        return "timeout"
    return "other" if token else "unknown"


def _delivery_delta(item: dict[str, Any]) -> str:
    artifact = str(item.get("artifact", "")).strip().lower()
    if artifact and artifact not in {"none", "n/a", "na"}:
        return "artifact_delta"
    files_touched = str(item.get("files_touched", "")).strip().lower()
    if files_touched and files_touched not in {"none", "n/a", "na"}:
        return "code_delta"
    tests_run = str(item.get("tests_run", "")).strip().lower()
    if tests_run and tests_run not in {"none", "n/a", "na", "skip(no_tests)", "skip(no_code_runtime_fix)"}:
        return "test_delta"
    verify = str(item.get("verify", "")).strip().lower()
    if verify and verify not in {"none", "n/a", "na"}:
        return "verify_delta"
    summary = str(item.get("summary", "")).strip().lower()
    if "contract_snapshot" in summary:
        return "contract_snapshot"
    return "none"


def build_planner_dispatch_metrics(root: Path, *, recent_limit: int = 12) -> dict[str, Any]:
    registry_path = resolve_orchestrator_read_path(root, "planner-subagents-registry.json")
    payload = _read_json(registry_path) if registry_path.exists() else {}
    rows = payload.get("subagents", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []

    active: list[dict[str, Any]] = []
    recent_rows: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        normalized = {
            "subagent_id": str(item.get("subagent_id", "")),
            "target_role": str(item.get("target_role", "")),
            "parent_role": str(item.get("parent_role", "")),
            "owner_task_id": str(item.get("owner_task_id", "")),
            "status": str(item.get("status", "")),
            "summary": str(item.get("summary", "")),
            "artifact": str(item.get("artifact", "")),
            "last_update_at": str(item.get("last_update_at", "")),
            "created_at": str(item.get("created_at", "")),
            "backend": str(item.get("backend", "")),
            "backend_ref": str(item.get("backend_ref", "")),
            "blocking_issue": str(item.get("blocking_issue", "")),
            "last_heartbeat": str(item.get("last_update_at", "") or item.get("created_at", "")),
            "last_delivery_delta": _delivery_delta(item),
        }
        status = normalized["status"].strip().lower()
        if status in ACTIVE_STATUSES:
            active.append(normalized)
        else:
            recent_rows.append(normalized)

    recent_rows = sorted(recent_rows, key=_recent_sort_key)[-max(1, int(recent_limit)) :]
    success_count = 0
    failed_count = 0
    blocked_count = 0
    fallback_like_count = 0
    invalid_result_count = 0
    timeout_like_count = 0
    by_role: dict[str, dict[str, int]] = {}
    for item in recent_rows:
        role = item["target_role"] or "unknown"
        bucket = by_role.setdefault(role, {"total": 0, "success": 0, "failed": 0, "blocked": 0, "fallback_like": 0, "invalid_result": 0, "timeout": 0})
        bucket["total"] += 1
        status = item["status"].strip().lower()
        if status in SUCCESS_STATUSES:
            success_count += 1
            bucket["success"] += 1
        elif status in BLOCKED_STATUSES:
            blocked_count += 1
            bucket["blocked"] += 1
        else:
            failed_count += 1
            bucket["failed"] += 1
        if _is_fallback_like(root, item["subagent_id"]):
            fallback_like_count += 1
            bucket["fallback_like"] += 1
        failure_mode = _failure_mode(item)
        if failure_mode == "invalid_result":
            invalid_result_count += 1
            bucket["invalid_result"] += 1
        elif failure_mode == "timeout":
            timeout_like_count += 1
            bucket["timeout"] += 1

    recent_total = len(recent_rows)
    success_rate = round(success_count / recent_total, 3) if recent_total else 1.0
    latest: dict[str, Any] = {}
    latest_status = ""
    latest_fallback_like = False
    latest_update_at = ""
    latest_owner_task_id = ""
    latest_failure_mode = "unknown"
    if recent_rows:
        latest = dict(recent_rows[-1])
        latest_status = str(latest.get("status", "")).strip().lower()
        latest_fallback_like = _is_fallback_like(root, str(latest.get("subagent_id", "")))
        latest_failure_mode = _failure_mode(latest)
        latest_update_at = str(
            latest.get("last_update_at")
            or latest.get("merged_at")
            or latest.get("finished_at")
            or latest.get("created_at")
            or ""
        ).strip()
        latest_owner_task_id = str(latest.get("owner_task_id", "")).strip()
    status = "ok"
    if active:
        status = "ok"
    elif recent_total and (
        latest_status not in SUCCESS_STATUSES
        or latest_fallback_like
    ):
        status = "degraded"
    workboard = _read_json(resolve_orchestrator_read_path(root, "parallel-workstreams.json"))
    stalled_capability_count = 0
    takeover_required_count = 0
    recovery_required_count = 0
    long_running_dev_count = 0
    dev_no_progress_count = 0
    dev_orphaned_count = 0
    dev_invalid_result_count = 0
    if isinstance(workboard, dict):
        for task in workboard.get("tasks", []):
            if not isinstance(task, dict):
                continue
            task_state = str(task.get("state", "")).strip().lower()
            if task_state in DONE_STATES:
                continue
            role = str(task.get("role", "")).strip().lower()
            execution_state = str(task.get("dev_execution_state", "")).strip().lower()
            if role == "dev":
                if execution_state == "long_running":
                    long_running_dev_count += 1
                if execution_state == "no_progress" or int(task.get("dev_no_progress_streak", 0) or 0) > 0:
                    dev_no_progress_count += 1
                if execution_state == "orphaned" or int(task.get("dev_orphaned_streak", 0) or 0) > 0:
                    dev_orphaned_count += 1
                if int(task.get("dev_invalid_result_streak", 0) or 0) > 0:
                    dev_invalid_result_count += 1
            if str(task.get("stalled_capability_reason", "")).strip():
                stalled_capability_count += 1
            if bool(task.get("planner_takeover_required")):
                takeover_required_count += 1
            if bool(task.get("admin_recovery_required") or task.get("dev_recovery_required")):
                recovery_required_count += 1
    recovering = bool(active) and (
        failed_count > 0
        or fallback_like_count > 0
        or invalid_result_count > 0
        or timeout_like_count > 0
        or dev_no_progress_count > 0
        or dev_orphaned_count > 0
        or stalled_capability_count > 0
        or takeover_required_count > 0
        or recovery_required_count > 0
    )
    return {
        "registry_path": str(registry_path),
        "active_count": len(active),
        "active": active[:8],
        "recent": recent_rows[-8:],
        "recent_total": recent_total,
        "recent_success_count": success_count,
        "recent_failed_count": failed_count,
        "recent_blocked_count": blocked_count,
        "recent_fallback_like_count": fallback_like_count,
        "recent_invalid_result_count": invalid_result_count,
        "recent_timeout_like_count": timeout_like_count,
        "recent_success_rate": success_rate,
        "recent_by_role": by_role,
        "latest_status": latest_status,
        "latest_fallback_like": latest_fallback_like,
        "latest_failure_mode": latest_failure_mode,
        "latest_owner_task_id": latest_owner_task_id,
        "latest_update_at": latest_update_at,
        "recovering": recovering,
        "stalled_capability_count": stalled_capability_count,
        "takeover_required_count": takeover_required_count,
        "recovery_required_count": recovery_required_count,
        "long_running_dev_count": long_running_dev_count,
        "dev_no_progress_count": dev_no_progress_count,
        "dev_orphaned_count": dev_orphaned_count,
        "dev_invalid_result_count": dev_invalid_result_count,
        "status": status,
    }
