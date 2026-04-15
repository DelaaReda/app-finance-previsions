from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator_paths import resolve_orchestrator_read_path

from .event_store import event_store_path, latest_graph_states, recent_events

LEGACY_BRIDGE_FILES = (
    "planner-subagents-registry.json",
    "planner-subagents-events.jsonl",
    "dynamic-workers-registry.json",
    "dynamic-workers-events.jsonl",
    "agent-message-bus.jsonl",
    "intent-registry.json",
)
READY_OWNER_TASK_STATES = {"ready", "ready_dev", "ready_planner", "ready_admin", "done", "closed"}
RETRYABLE_RESIDUE_STATUSES = {"retryable", "failed", "blocked"}
INVALID_RESULT_MARKERS = ("invalid_subagent_result", "start_banner_only")


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


def _sort_ts(item: dict[str, Any]) -> float:
    for key in ("updated_at", "ts", "finished_at", "created_at"):
        dt = _parse_iso(item.get(key))
        if dt is not None:
            return dt.timestamp()
    return 0.0


def _truth_value_present(value: Any) -> bool:
    token = str(value or "").strip()
    if not token:
        return False
    token_lower = token.lower()
    if token_lower in {"none", "n/a", "na", "null", "unknown"}:
        return False
    if token_lower in {"...", "…", "before=...; after=...; test=..."}:
        return False
    if token_lower == "...." or token_lower == "...".lstrip():
        return False
    return True


def _task_has_delivery_evidence(item: dict[str, Any]) -> bool:
    proof = item.get("delivery_proof", {}) if isinstance(item.get("delivery_proof"), dict) else {}
    result = item.get("capability_result", {}) if isinstance(item.get("capability_result"), dict) else {}
    for key in ("artifact", "verify", "tests_run", "commit_sha", "proof_manifest"):
        if _truth_value_present(item.get(key, "")):
            return True
        if _truth_value_present(result.get(key, "")) or _truth_value_present(proof.get(key, "")):
            return True
    return False


def _proof_field(*parts: Any) -> str:
    for part in parts:
        if _truth_value_present(part):
            return str(part).strip()
    return "none"


def _normalize_state(item: dict[str, Any]) -> dict[str, Any]:
    request = item.get("capability_request", {}) if isinstance(item.get("capability_request"), dict) else {}
    result = item.get("capability_result", {}) if isinstance(item.get("capability_result"), dict) else {}
    proof = item.get("delivery_proof", {}) if isinstance(item.get("delivery_proof"), dict) else {}
    metadata = request.get("metadata", {}) if isinstance(request.get("metadata"), dict) else {}
    return {
        "task_id": str(item.get("task_id", "") or request.get("task_id", "")).strip(),
        "batch_id": str(item.get("batch_id", "") or request.get("batch_id", "")).strip(),
        "owner_role": str(item.get("owner_role", "") or request.get("owner_role", "")).strip(),
        "target_role": str(item.get("target_role", "") or request.get("target_role", "")).strip(),
        "task_kind": str(item.get("task_kind", "") or request.get("task_kind", "")).strip(),
        "status": str(item.get("status", "") or result.get("status", "")).strip().lower() or "unknown",
        "current_node": str(item.get("current_node", "")).strip(),
        "next_action": str(item.get("next_action", "")).strip(),
        "blocking_issue": str(item.get("blocking_issue", "") or result.get("blocking_issue", "") or "none").strip(),
        "backend": str(result.get("backend", "") or request.get("backend", "")).strip(),
        "artifact": _proof_field(result.get("artifact", ""), proof.get("artifact", "")),
        "verify": _proof_field(result.get("verify", ""), proof.get("verify", "")),
        "commit_sha": _proof_field(result.get("commit_sha", ""), proof.get("commit_sha", "")),
        "updated_at": str(item.get("updated_at", "")).strip(),
        "subagent_id": str(metadata.get("subagent_id", "")).strip(),
        "checkpoint_id": str(item.get("checkpoint_id", "")).strip(),
        "tests_run": _proof_field(result.get("tests_run", ""), proof.get("tests_run", "")),
        "engine": str(item.get("engine", "")).strip(),
    }


def _load_workboard_task_index(root: Path) -> dict[str, dict[str, Any]]:
    path = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
    if not isinstance(tasks, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for row in tasks:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("id", "") or row.get("task_id", "")).strip()
        if task_id:
            index[task_id] = row
    return index


def _task_operational_state(task: dict[str, Any]) -> str:
    status = str(task.get("status", "") or "").strip().lower()
    state = str(task.get("state", "") or "").strip().lower()
    if status in READY_OWNER_TASK_STATES:
        return status
    return state or status


def _quarantine_retryable_residue(
    item: dict[str, Any], task_index: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    task_id = str(item.get("task_id", "")).strip()
    if not task_id:
        return None
    task = task_index.get(task_id)
    if not isinstance(task, dict):
        return None

    task_state = _task_operational_state(task)
    if task_state not in READY_OWNER_TASK_STATES:
        return None

    status = str(item.get("status", "")).strip().lower()
    if status not in RETRYABLE_RESIDUE_STATUSES:
        return None

    issue_bits = " | ".join(
        [
            str(item.get("blocking_issue", "")),
            str(item.get("next_action", "")),
        ]
    ).strip().lower()
    if not any(marker in issue_bits for marker in INVALID_RESULT_MARKERS):
        return None
    if _task_has_delivery_evidence(item):
        return None

    quarantined = dict(item)
    quarantined["status"] = "quarantined"
    quarantined["blocking_issue"] = f"quarantined_retryable_residue:{task_state}"
    quarantined["next_action"] = "secondary_compat_only"
    quarantined["decision_capable"] = False
    quarantined["secondary_compat_only"] = True
    quarantined["quarantine_reason"] = "owner_task_ready_runtime_residue"
    quarantined["original_status"] = status
    return quarantined


def _legacy_bridge_snapshot(root: Path, *, hide_paths: bool = False) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    existing = 0
    for name in LEGACY_BRIDGE_FILES:
        path = resolve_orchestrator_read_path(root, name)
        exists = path.exists()
        if exists:
            existing += 1
        files[name] = {
            "path": "secondary_compat_only" if hide_paths else str(path),
            "exists": exists,
        }
    return {
        "kind": "legacy_compat",
        "secondary_only": True,
        "decision_capable": False,
        "existing_count": existing,
        "files": files,
    }


def build_runtime_truth_snapshot(root: Path, *, state_limit: int = 12, event_limit: int = 50) -> dict[str, Any]:
    root = Path(root)
    sqlite_path = event_store_path(root)
    graph_states = latest_graph_states(root, limit=max(50, state_limit * 4))
    workboard_task_index = _load_workboard_task_index(root)
    all_states = [_normalize_state(row) for row in graph_states if isinstance(row, dict)]
    all_states.sort(key=_sort_ts, reverse=True)
    quarantined_retryable_residue: list[dict[str, Any]] = []
    normalized_states: list[dict[str, Any]] = []
    for item in all_states:
      quarantined = _quarantine_retryable_residue(item, workboard_task_index)
      if quarantined is not None:
          quarantined_retryable_residue.append(quarantined)
      else:
          normalized_states.append(item)
    shown_states = normalized_states[: max(1, state_limit)]

    state_counts = Counter(str(row.get("status", "")).strip().lower() or "unknown" for row in normalized_states)
    recent_event_rows = [row for row in recent_events(root, hours=6, limit=max(20, event_limit)) if isinstance(row, dict)]
    recent_event_rows.sort(key=_sort_ts, reverse=True)
    recent_event_types = Counter(str(row.get("event_type", "")).strip() or "unknown" for row in recent_event_rows)

    queue_projection = resolve_orchestrator_read_path(root, "priority-queue.json")
    workboard_projection = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
    event_store_primary = sqlite_path.exists() and bool(normalized_states or recent_event_rows)
    runtime_truth_source = "sqlite" if event_store_primary else "fallback"
    legacy_bridges = _legacy_bridge_snapshot(root, hide_paths=event_store_primary)
    if event_store_primary:
        agentic_runtime_status = "ok"
    elif sqlite_path.exists():
        agentic_runtime_status = "degraded"
    else:
        agentic_runtime_status = "unknown"

    return {
        "event_store_primary": bool(event_store_primary),
        "runtime_truth_source": runtime_truth_source,
        "source": "event_store" if event_store_primary else "projection_fallback",
        "projection_secondary_only": bool(event_store_primary),
        "legacy_registry_secondary_only": True,
        "sqlite_path": str(sqlite_path),
        "graph_state_count": len(normalized_states),
        "graph_state_count_total": len(all_states),
        "recent_event_count": len(recent_event_rows),
        "status_counts": dict(state_counts),
        "recent_event_types": dict(recent_event_types),
        "latest_states": shown_states,
        "quarantined_retryable_residue_count": len(quarantined_retryable_residue),
        "quarantined_retryable_residue": quarantined_retryable_residue[: max(1, state_limit)],
        "agentic_runtime": {
            "status": agentic_runtime_status,
            "primary_source": "sqlite_event_store" if event_store_primary else "projection_fallback",
            "planner_scheduler": "planner",
            "graph_state_count": len(normalized_states),
            "recent_event_count": len(recent_event_rows),
        },
        "legacy_bridges": legacy_bridges,
        "projection_paths": {
            "queue": str(queue_projection),
            "workboard": str(workboard_projection),
        },
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
