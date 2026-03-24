from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import resolve_orchestrator_read_path

from .event_store import latest_graph_states, recent_events
from .runtime_truth_reader import build_runtime_truth_snapshot


ACTIVE_GRAPH_STATUSES = {"running", "pending"}
SUCCESS_STATUSES = {"completed", "merged", "done", "pass", "ok", "success"}
BLOCKED_STATUSES = {"blocked"}
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
)
TIMEOUT_LIKE_MARKERS = ("timeout", "timed out", "stale_no_result", "deadline", "no result")
QUEUE_READY_ALIASES = {"ready", "ready_dev", "ready_planner"}
LONG_RUNNING_DEV_SECONDS = 30 * 60
NO_PROGRESS_DEV_SECONDS = 20 * 60
STALE_ACTIVE_QUARANTINE_SECONDS = 45 * 60
NON_ACTIVE_WORKBOARD_STATES = {
    "done",
    "closed",
    "ready",
    "ready_dev",
    "ready_planner",
    "waiting_dep",
    "blocked",
    "cancelled",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


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
    for key in ("last_update_at", "updated_at", "finished_at", "created_at"):
        dt = _parse_iso(item.get(key))
        if dt is not None:
            return dt.timestamp()
    return 0.0


def _canonical_role(value: Any) -> str:
    token = str(value or "").strip().replace("-", "_").lower()
    if token in {"po_scrum_master", "scrum"}:
        return "scrum_master"
    return token


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


def _quarantine_stale_active(row: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    status = str(row.get("status", "")).strip().lower()
    if status not in ACTIVE_GRAPH_STATUSES:
        return None
    updated_at = _parse_iso(row.get("last_update_at")) or _parse_iso(row.get("updated_at"))
    if updated_at is None:
        return None
    age_s = max(0.0, (now - updated_at).total_seconds())
    if age_s < STALE_ACTIVE_QUARANTINE_SECONDS:
        return None
    if str(row.get("last_meaningful_delta", "none") or "none").strip().lower() != "none":
        return None
    graph_state = row.get("planner_graph_state", {}) if isinstance(row.get("planner_graph_state"), dict) else {}
    current_node = str(graph_state.get("current_node", "") or "").strip().lower()
    next_action = str(graph_state.get("next_action", "") or "").strip().lower()
    if current_node != "wait_or_collect_result" and next_action != "wait_or_collect_result":
        return None
    quarantined = dict(row)
    quarantined["status"] = "failed"
    quarantined["blocking_issue"] = f"quarantined_stale_active:{int(age_s)}s"
    quarantined["quarantined_stale_active"] = True
    quarantined["quarantine_reason"] = "stale_wait_or_collect_without_meaningful_delta"
    return quarantined


def _workboard_task_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("id", "") or row.get("task_id", "")).strip()
        if task_id:
            index[task_id] = row
    return index


def _quarantine_runtime_inconsistent_active(
    row: dict[str, Any], task_index: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    owner_task_id = str(row.get("owner_task_id", "")).strip()
    if not owner_task_id:
        return None
    task = task_index.get(owner_task_id)
    if not isinstance(task, dict):
        return None

    task_state = str(task.get("state", task.get("status", "")) or "").strip().lower()
    task_role = _canonical_role(task.get("role") or task.get("owner") or task.get("lane"))
    row_role = _canonical_role(row.get("role"))
    reasons: list[str] = []

    if task_role and row_role and task_role != row_role:
        reasons.append(f"owner_task_role_mismatch:{task_role}!={row_role}")
    if task_state in NON_ACTIVE_WORKBOARD_STATES:
        reasons.append(f"owner_task_not_in_progress:{task_state}")
    if not reasons:
        return None

    quarantined = dict(row)
    quarantined["status"] = "failed"
    quarantined["blocking_issue"] = ";".join(reasons)
    quarantined["quarantined_runtime_inconsistent_active"] = True
    quarantined["quarantine_reason"] = "runtime_truth_owner_task_conflict"
    return quarantined


def _load_queue_snapshot(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = resolve_orchestrator_read_path(root, "priority-queue.json")
    payload = _read_json(path)
    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        items = []
    return payload, [row for row in items if isinstance(row, dict)]


def _load_workboard_snapshot(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
    payload = _read_json(path)
    tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
    if not isinstance(tasks, list):
        tasks = []
    return payload, [row for row in tasks if isinstance(row, dict)]


def _queue_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row.get("status", row.get("state", "")) or "").strip().upper() for row in rows)
    ready_dev = 0
    ready_planner = 0
    ready_total = 0
    for row in rows:
        status = str(row.get("status", row.get("state", "")) or "").strip().lower()
        role = _canonical_role(row.get("owner") or row.get("role") or row.get("lane"))
        if status in QUEUE_READY_ALIASES:
            ready_total += 1
            if role == "dev" or status == "ready_dev":
                ready_dev += 1
            if role == "planner" or status == "ready_planner":
                ready_planner += 1
    return {
        "ready_total": ready_total,
        "ready_dev_count": ready_dev,
        "ready_planner_count": ready_planner,
        "counts": dict(counts),
    }


def _workboard_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row.get("state", row.get("status", "")) or "").strip().upper() for row in rows)
    ready_total = 0
    ready_dev = 0
    ready_planner = 0
    in_progress = 0
    waiting_dep = 0
    for row in rows:
        state = str(row.get("state", row.get("status", "")) or "").strip().lower()
        role = _canonical_role(row.get("owner") or row.get("role") or row.get("lane"))
        if state in {"ready", "ready_dev", "ready_planner"}:
            ready_total += 1
            if role == "dev" or state == "ready_dev":
                ready_dev += 1
            if role == "planner" or state == "ready_planner":
                ready_planner += 1
        if state == "in_progress":
            in_progress += 1
        if state == "waiting_dep":
            waiting_dep += 1
    return {
        "ready_total": ready_total,
        "ready_dev_count": ready_dev,
        "ready_planner_count": ready_planner,
        "in_progress": in_progress,
        "waiting_dep": waiting_dep,
        "counts": dict(counts),
    }


def _graph_result_status(state: dict[str, Any]) -> str:
    result = state.get("capability_result", {}) if isinstance(state.get("capability_result"), dict) else {}
    token = str(result.get("status", "") or state.get("status", "")).strip().lower()
    if token == "ready_to_merge":
        return "completed"
    return token or "unknown"


def _normalize_graph_state(state: dict[str, Any]) -> dict[str, Any]:
    request = state.get("capability_request", {}) if isinstance(state.get("capability_request"), dict) else {}
    result = state.get("capability_result", {}) if isinstance(state.get("capability_result"), dict) else {}
    proof = state.get("delivery_proof", {}) if isinstance(state.get("delivery_proof"), dict) else {}
    metadata = request.get("metadata", {}) if isinstance(request.get("metadata"), dict) else {}
    task_id = str(state.get("task_id", "") or result.get("task_id", "") or request.get("task_id", "")).strip()
    backend = str(result.get("backend", "") or request.get("backend", "")).strip().lower()
    status = _graph_result_status(state)
    return {
        "subagent_id": str(metadata.get("subagent_id", "") or f"graph-{task_id}").strip(),
        "role": _canonical_role(state.get("target_role", "") or result.get("target_role", "") or request.get("target_role", "")),
        "owner_task_id": task_id,
        "parent_role": _canonical_role(state.get("owner_role", "") or result.get("owner_role", "") or request.get("owner_role", "") or "planner"),
        "task_kind": str(state.get("task_kind", "") or request.get("task_kind", "")).strip().lower(),
        "purpose": str(state.get("task_kind", "") or request.get("task_kind", "") or "delivery").strip().lower(),
        "status": status,
        "created_at": "",
        "expires_at": "",
        "ttl_min": int(metadata.get("ttl_min", 0) or 0),
        "backend": backend,
        "backend_ref": str(result.get("backend_ref", "")).strip(),
        "last_update_at": str(state.get("updated_at", "")).strip(),
        "summary": str(result.get("summary", "") or proof.get("summary", "")).strip(),
        "root_cause": str(result.get("root_cause", "")).strip(),
        "fix_applied": str(result.get("fix_applied", "")).strip(),
        "artifact": str(result.get("artifact", "") or proof.get("artifact", "") or "none").strip(),
        "verify": str(result.get("verify", "") or proof.get("verify", "") or "none").strip(),
        "files_touched": str(result.get("files_touched", "") or "none").strip(),
        "tests_run": str(result.get("tests_run", "") or proof.get("tests_run", "") or "none").strip(),
        "commit_sha": str(result.get("commit_sha", "") or proof.get("commit_sha", "") or "none").strip(),
        "blocking_issue": str(result.get("blocking_issue", "") or state.get("blocking_issue", "") or "none").strip(),
        "last_meaningful_delta": "none",
        "metadata": metadata,
        "planner_graph_state": state,
    }


def build_stable_planner_dispatch_snapshot(root: Path, *, recent_limit: int = 12) -> dict[str, Any]:
    root = Path(root)
    now = datetime.now(timezone.utc)
    queue_payload, queue_rows = _load_queue_snapshot(root)
    workboard_payload, workboard_rows = _load_workboard_snapshot(root)
    workboard_task_index = _workboard_task_index(workboard_rows)
    queue = _queue_counts(queue_rows)
    workboard = _workboard_counts(workboard_rows)
    runtime_truth = build_runtime_truth_snapshot(root, state_limit=max(24, recent_limit * 2), event_limit=max(50, recent_limit * 4))
    event_store_primary = bool(runtime_truth.get("event_store_primary", False))
    runtime_truth_source = str(runtime_truth.get("runtime_truth_source", "sqlite" if event_store_primary else "fallback"))
    effective_ready_total = queue["ready_total"]
    effective_ready_dev_count = queue["ready_dev_count"]
    effective_ready_planner_count = queue["ready_planner_count"]
    if event_store_primary:
        effective_ready_total = max(effective_ready_total, workboard["ready_total"])
        effective_ready_dev_count = max(effective_ready_dev_count, workboard["ready_dev_count"])
        effective_ready_planner_count = max(effective_ready_planner_count, workboard["ready_planner_count"])

    graph_states = latest_graph_states(root, limit=max(50, recent_limit * 4))
    graph_states = [row for row in graph_states if isinstance(row, dict)]
    graph_states.sort(key=_recent_sort_key, reverse=True)

    if graph_states:
        normalized = [_normalize_graph_state(row) for row in graph_states]
        source = "event_store"
    elif event_store_primary:
        normalized = []
        source = "event_store_primary_no_graph_state"
    else:
        normalized = []
        source = "projection_fallback_no_runtime_truth"

    normalized = [row for row in normalized if isinstance(row, dict)]
    normalized.sort(key=_recent_sort_key, reverse=True)
    for row in normalized:
        row["last_meaningful_delta"] = _delivery_delta(row)

    active: list[dict[str, Any]] = []
    quarantined_active: list[dict[str, Any]] = []
    runtime_inconsistent_active_count = 0
    non_active: list[dict[str, Any]] = []
    for row in normalized:
        status = str(row.get("status", "")).strip().lower()
        if status in ACTIVE_GRAPH_STATUSES:
            quarantined = _quarantine_runtime_inconsistent_active(row, workboard_task_index) if event_store_primary else None
            if quarantined is None:
                quarantined = _quarantine_stale_active(row, now) if event_store_primary else None
            if quarantined is not None:
                quarantined_active.append(quarantined)
                if bool(quarantined.get("quarantined_runtime_inconsistent_active")):
                    runtime_inconsistent_active_count += 1
            else:
                active.append(row)
        else:
            non_active.append(row)
    recent = (quarantined_active + non_active)[: max(1, recent_limit)]

    recent_success_count = sum(1 for row in recent if str(row.get("status", "")).strip().lower() in SUCCESS_STATUSES)
    recent_failed_count = sum(1 for row in recent if str(row.get("status", "")).strip().lower() == "failed")
    recent_blocked_count = sum(1 for row in recent if str(row.get("status", "")).strip().lower() in BLOCKED_STATUSES)
    recent_fallback_like_count = sum(1 for row in recent if str(row.get("backend", "")).strip().lower() == "qwen")
    success_denominator = recent_success_count + recent_failed_count + recent_blocked_count

    latest = (active or recent or [{}])[0]
    latest_status = str(latest.get("status", "")).strip().lower()
    latest_backend = str(latest.get("backend", "")).strip().lower()
    latest_failure_mode = _failure_mode(latest)
    latest_update_at = str(latest.get("last_update_at", "")).strip()

    recent_event_rows = recent_events(root, hours=24, limit=200)
    one_hour_cutoff = now - timedelta(hours=1)
    progressed_task_ids: set[str] = set()
    for event in recent_event_rows:
        if not isinstance(event, dict):
            continue
        ts = _parse_iso(event.get("ts"))
        if ts is None or ts < one_hour_cutoff:
            continue
        event_type = str(event.get("event_type", "")).strip().lower()
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        status = str(payload.get("status", "") or payload.get("result_status", "")).strip().lower()
        task_id = str(event.get("task_id", "") or payload.get("task_id", "")).strip()
        if not task_id:
            continue
        if event_type in {"graph.close_or_requeue", "model.collect", "graph.validate_contract_and_proof"} or status in SUCCESS_STATUSES:
            progressed_task_ids.add(task_id)

    active_dev = [row for row in active if _canonical_role(row.get("role")) == "dev"]
    long_running_dev_count = 0
    dev_no_progress_count = 0
    for row in active_dev:
        updated_at = _parse_iso(row.get("last_update_at"))
        if updated_at is None:
            continue
        age_s = max(0.0, (now - updated_at).total_seconds())
        if age_s >= LONG_RUNNING_DEV_SECONDS:
            long_running_dev_count += 1
        if age_s >= NO_PROGRESS_DEV_SECONDS:
            dev_no_progress_count += 1

    recent_invalid_result_count = sum(1 for row in recent if _failure_mode(row) == "invalid_result")
    recent_timeout_like_count = sum(1 for row in recent if _failure_mode(row) == "timeout")
    recovering = bool(active) and (recent_failed_count > 0 or recent_blocked_count > 0)

    if workboard["waiting_dep"] > 0:
        current_bottleneck = "waiting_dependencies"
    elif effective_ready_total > 0 and not active:
        current_bottleneck = "dispatch_idle"
    elif recent_failed_count > 0 or recent_blocked_count > 0:
        current_bottleneck = "capability_failures"
    else:
        current_bottleneck = "none"

    if active:
        status = "ok"
        planner_state = "waiting_on_agents"
    elif effective_ready_total > 0:
        status = "dispatch_needed"
        planner_state = "idle"
    elif event_store_primary:
        status = "ok"
        planner_state = "idle"
    elif recent_failed_count > 0 or recent_blocked_count > 0:
        status = "degraded"
        planner_state = "blocked"
    else:
        status = "ok"
        planner_state = "idle"

    ready_total = effective_ready_total
    ready_dev_count = effective_ready_dev_count
    ready_planner_count = effective_ready_planner_count
    tasks_progressed_last_1h = len(progressed_task_ids)
    needs_dispatch = ready_total > 0 and not active
    stalled_ready_dev = ready_dev_count > 0 and not active and tasks_progressed_last_1h == 0
    compat_registry_path = resolve_orchestrator_read_path(root, "planner-subagents-registry.json")
    registry_path = "secondary_compat_only" if event_store_primary else str(compat_registry_path)

    return {
        "ok": True,
        "enabled": True,
        "cron_planner_only": False,
        "role": "planner",
        "runtime_truth_source": runtime_truth_source,
        "source": source,
        "event_store_primary": event_store_primary,
        "primary_source": str(runtime_truth.get("source", "event_store" if event_store_primary else "projection_fallback")),
        "status": status,
        "planner_state": planner_state,
        "active_count": len(active),
        "active": active[:8],
        "recent": recent,
        "recent_total": len(recent),
        "recent_success_count": recent_success_count,
        "recent_failed_count": recent_failed_count,
        "recent_blocked_count": recent_blocked_count,
        "recent_fallback_like_count": recent_fallback_like_count,
        "recent_success_rate": (recent_success_count / success_denominator) if success_denominator else 1.0,
        "recent_by_role": dict(Counter(_canonical_role(row.get("role")) for row in recent if _canonical_role(row.get("role")))),
        "latest_status": latest_status,
        "latest_backend": latest_backend,
        "latest_owner_task_id": str(latest.get("owner_task_id", "")).strip(),
        "latest_update_at": latest_update_at,
        "latest_last_meaningful_delta": str(latest.get("last_meaningful_delta", "none") or "none").strip() or "none",
        "latest_monitor_agent_id": str(latest.get("monitor_agent_id", "")).strip(),
        "latest_purpose": str(latest.get("purpose", "")).strip(),
        "latest_fallback_like": latest_backend == "qwen",
        "latest_failure_mode": latest_failure_mode,
        "monitor_active_count": 0,
        "monitoring_count": 0,
        "monitor_without_target_count": 0,
        "degraded_backend": False,
        "backend_route_reason": "none",
        "backend_cooldown_until": "",
        "last_meaningful_delta": str(latest.get("last_meaningful_delta", "none") or "none").strip() or "none",
        "collect_timeout_without_agents": False,
        "stalled_capability_count": recent_timeout_like_count,
        "takeover_required_count": 0,
        "recovery_required_count": 0,
        "long_running_dev_count": long_running_dev_count,
        "dev_no_progress_count": dev_no_progress_count,
        "dev_orphaned_count": 0,
        "dev_invalid_result_count": sum(
            1
            for row in recent
            if _canonical_role(row.get("role")) == "dev" and _failure_mode(row) == "invalid_result"
        ),
        "recent_invalid_result_count": recent_invalid_result_count,
        "recent_timeout_like_count": recent_timeout_like_count,
        "quarantined_stale_active_count": len(quarantined_active),
        "runtime_inconsistent_active_count": runtime_inconsistent_active_count,
        "recovering": recovering,
        "events_path": str(resolve_orchestrator_read_path(root, "planner-graph-events.jsonl")),
        "registry_path": registry_path,
        "secondary_registry_path": registry_path,
        "compat_registry_present": False if event_store_primary else compat_registry_path.exists(),
        "queue_state_counts": queue["counts"],
        "workboard_state_counts": workboard["counts"],
        "queue_updated_at": str(queue_payload.get("updated_at", "") or "").strip(),
        "workboard_updated_at": str(workboard_payload.get("updated_at", "") or "").strip(),
        "ready_total": ready_total,
        "ready_dev_count": ready_dev_count,
        "ready_planner_count": ready_planner_count,
        "in_progress_count": workboard["in_progress"],
        "waiting_dep_count": workboard["waiting_dep"],
        "tasks_progressed_last_1h": tasks_progressed_last_1h,
        "artifacts_generated_last_1h": sum(
            1
            for row in recent
            if _parse_iso(row.get("last_update_at")) is not None
            and _parse_iso(row.get("last_update_at")) >= one_hour_cutoff
            and str(row.get("artifact", "")).strip().lower() not in {"", "none", "n/a", "na"}
        ),
        "current_bottleneck": current_bottleneck,
        "recommended_next_action": "dispatch" if needs_dispatch else "monitor",
        "needs_dispatch": needs_dispatch,
        "stalled_ready_dev": stalled_ready_dev,
        "active_subagents": len(active),
        "lifecycle": "running",
        "planner_graph_engine": str((graph_states[0].get("engine") if graph_states else "none") or "none"),
        "planner_graph_state_count": len(graph_states),
        "legacy_registry_secondary_only": True,
        "projection_secondary_only": bool(event_store_primary),
        "registry_compat_only": True,
        "planner_graph_ready_to_merge_count": sum(1 for row in graph_states if str(row.get("status", "")).strip().lower() == "ready_to_merge"),
        "planner_graph_retryable_count": sum(1 for row in graph_states if str(row.get("status", "")).strip().lower() == "retryable"),
        "planner_graph_blocked_count": sum(1 for row in graph_states if str(row.get("status", "")).strip().lower() == "blocked"),
        "planner_graph_active": graph_states[:8],
    }
