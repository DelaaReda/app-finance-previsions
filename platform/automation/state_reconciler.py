#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from orchestrator_paths import resolve_orchestrator_read_path
from compat.projections.parallel_workstream import append_event, board_lock, load_board, now_iso, recompute_states, reconcile_state, save_board
from runtime.planner.planner_board_runtime import CAPABILITY_ROLES
from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot

RUNTIME_BLOCKERS = {
    "API_UNREACHABLE",
    "BACKEND_API_UNREACHABLE",
    "BACKEND_API_HEALTHCHECK_FAIL",
    "MONITOR_API_UNREACHABLE",
    "BACKEND_AND_MONITOR_UNREACHABLE",
    "RUNTIME_DOWN",
    "RUNTIME_DOWN_BLOCKS_READY_QUEUE",
    "RUNTIME_DEGRADED",
    "RUNTIME_RECOVERED_SOFT",
}
READY_STATES = {"READY", "READY_PLANNER", "READY_DEV"}
ACTIVE_IN_PROGRESS_STATES = {"IN_PROGRESS", "REVIEW"}
BLOCKING_STATES = {"BLOCKED"}
CORE_ROLES = ("planner", "dev", "admin", "scrum_master")
DONE_STATES = {"DONE", "CLOSED"}
NOVELTY_TARGET_OVERDUE_SECONDS = max(300, int(os.environ.get("FC_RECONCILE_NOVELTY_TARGET_OVERDUE_SECONDS", "1800")))
EMPTY_VALUE_TOKENS = {"", "none", "n/a", "na", "null", "unknown"}
INVALID_SUBAGENT_RESULT_PREFIXES = (
    "invalid_subagent_result:start_banner_only",
    "invalid_subagent_result:structured_output_missing",
    "invalid_subagent_result:output_schema_missing",
    "invalid_subagent_result:empty_payload",
    "invalid_subagent_result:missing_result_payload",
    "invalid_subagent_result:blocked_without_signal",
)
CODEX_STARTUP_NOISE_MARKERS = (
    "openai codex v",
    "research preview",
    "approval: never",
    "sandbox: danger-full-access",
    "sandbox: workspace-write",
    "reasoning effort:",
    "session id:",
    "provider: openai",
    "provider: azure",
    "provider: anthropic",
    "provider: google",
    "failed to refresh available models",
    "missing bearer or basic authentication",
    "401 unauthorized",
    "unexpected status 401 unauthorized",
    "transport channel",
    "worker quit with fatal",
    "reconnecting...",
)
DEFAULT_PUBLIC_APP_BASE_URL = "http://3.98.20.77"
DEFAULT_PUBLIC_MONITOR_BASE_URL = "http://3.98.20.77:8080"


@dataclass
class ReconcileConfig:
    root: Path
    role: str
    queue_path: Path
    board_path: Path
    state_dir: Path
    report_path: Path
    lock_dir: Path
    stale_lock_seconds: int = 1800
    stale_in_progress_seconds: int = 14400
    ready_starvation_seconds: int = 1800


def _canonical_role(role: str) -> str:
    token = (role or "").strip().lower()
    if token in {"backend_engineer", "frontend_engineer", "data_analyst", "integrator"}:
        return "dev"
    if token in {"qa", "tester", "infra_engineer", "clawsentinel"}:
        return "admin"
    if token in {"analyst", "architect", "po", "vision-architect-tasks-planner", "vision_architect_tasks_planner"}:
        return "planner"
    return token


def _load_json(path: Path, default: dict | list) -> dict | list:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return default


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _parse_iso_epoch(value: str) -> int:
    raw = (value or "").strip()
    if not raw:
        return 0
    try:
        if raw.endswith("Z"):
            from datetime import datetime, timezone

            return int(datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
        from datetime import datetime, timezone

        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    except Exception:
        return 0


def _preferred_ready_state_for_role(role: str) -> str:
    return "READY_DEV" if _canonical_role(role) == "dev" else "READY"


def _looks_like_placeholder_only_value(value: str) -> bool:
    token = " ".join(str(value or "").strip().split()).lower()
    if not token:
        return True
    if token in {"...", "..", ".", "…", "?", "??", "tbd"}:
        return True
    if re.fullmatch(r"(?:[a-z_]+=\.\.\.)(?:\s*;\s*[a-z_]+=\.\.\.)*", token):
        return True
    return False


def _looks_like_startup_noise(value: str) -> bool:
    token = " ".join(str(value or "").strip().lower().split())
    if not token:
        return True
    return any(marker in token for marker in CODEX_STARTUP_NOISE_MARKERS)


def _runtime_blocking_issue_is_noneish(value: str) -> bool:
    token = str(value or "").strip().lower()
    if not token:
        return True
    if token in EMPTY_VALUE_TOKENS:
        return True
    if _looks_like_startup_noise(token):
        return True
    return False


def _runtime_blocking_issue_allows_semantic_success(value: str) -> bool:
    token = str(value or "").strip().lower()
    if _runtime_blocking_issue_is_noneish(token):
        return True
    if any(token.startswith(prefix) for prefix in INVALID_SUBAGENT_RESULT_PREFIXES):
        return True
    return False


def _value_present(value: str) -> bool:
    token = str(value or "").strip().lower()
    if token in EMPTY_VALUE_TOKENS:
        return False
    if _looks_like_placeholder_only_value(token):
        return False
    return True


def _board_active_batch_ids(board: dict) -> set[str]:
    active_cycle = board.get("active_cycle")
    if not isinstance(active_cycle, dict):
        return set()
    raw_ids = active_cycle.get("active_batch_ids")
    if not isinstance(raw_ids, list):
        return set()
    cycle_ids = {str(item).strip().upper() for item in raw_ids if str(item).strip()}
    if not cycle_ids:
        return set()

    closed_states = {"DONE", "CLOSED", "CANCELLED", "ARCHIVED"}
    open_ids: set[str] = set()
    saw_runtime_rows = False

    for stream in board.get("streams", []):
        if not isinstance(stream, dict):
            continue
        saw_runtime_rows = True
        state = str(stream.get("state", "")).strip().upper()
        if state in closed_states:
            continue
        stream_id = str(stream.get("stream_id") or stream.get("batch_id") or stream.get("id") or "").strip().upper()
        if stream_id:
            open_ids.add(stream_id)

    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        saw_runtime_rows = True
        state = str(task.get("state", "")).strip().upper()
        if state in closed_states:
            continue
        stream_id = str(task.get("stream_id") or task.get("batch_id") or "").strip().upper()
        if stream_id:
            open_ids.add(stream_id)

    if saw_runtime_rows:
        return cycle_ids & open_ids
    return cycle_ids


def _task_stream_id(task: dict | None) -> str:
    if not isinstance(task, dict):
        return ""
    for key in ("stream_id", "batch_id"):
        token = str(task.get(key, "")).strip().upper()
        if token:
            return token
    task_id_value = str(task.get("id", "")).strip().upper()
    if task_id_value.startswith("BATCH-"):
        parts = task_id_value.split("-")
        if len(parts) >= 2:
            return "-".join(parts[:2])
    return ""


def _task_in_active_cycle(task: dict | None, board: dict | None) -> bool:
    if not isinstance(board, dict):
        return True
    active_batch_ids = _board_active_batch_ids(board)
    if not active_batch_ids:
        return True
    stream_id = _task_stream_id(task)
    return bool(stream_id) and stream_id in active_batch_ids


def _preferred_ready_state_for_stream(board: dict, stream_id: str, fallback_role: str = "") -> str:
    task_roles = []
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        if str(task.get("stream_id", "")).strip().upper() != stream_id.upper():
            continue
        state = str(task.get("state", "")).strip().upper()
        if state in {"DONE", "CLOSED"}:
            continue
        task_roles.append(_canonical_role(str(task.get("role") or task.get("assignee") or "").strip()))
    if "dev" in task_roles:
        return "READY_DEV"
    if task_roles:
        return "READY"
    return _preferred_ready_state_for_role(fallback_role)


def _extract_meta_field(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    m = re.search(rf"\b{re.escape(key)}=(\S+)", text)
    return m.group(1) if m else ""


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _fetch_local_json(url: str, timeout: float = 1.5) -> dict | None:
    try:
        import urllib.request

        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            if not (200 <= status < 300):
                return None
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
            return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _http_status_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        import urllib.request

        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            return 200 <= status < 300
    except Exception:
        return False


def _public_api_base_url() -> str:
    return str(
        os.environ.get("FC_API_BASE_URL")
        or os.environ.get("FC_PUBLIC_APP_BASE_URL")
        or DEFAULT_PUBLIC_APP_BASE_URL
    ).strip() or DEFAULT_PUBLIC_APP_BASE_URL


def _public_monitor_base_url() -> str:
    return str(
        os.environ.get("FC_MONITOR_BASE_URL")
        or os.environ.get("FC_PUBLIC_MONITOR_BASE_URL")
        or DEFAULT_PUBLIC_MONITOR_BASE_URL
    ).strip() or DEFAULT_PUBLIC_MONITOR_BASE_URL


def _runtime_probes_ok() -> bool:
    try:
        import urllib.request

        for url in (
            f"{_public_api_base_url().rstrip('/')}/api/health",
            f"{_public_monitor_base_url().rstrip('/')}/api/status",
        ):
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                status = int(getattr(resp, "status", 0) or 0)
                if not (200 <= status < 300):
                    return False
        return True
    except Exception:
        return False


def _delivery_backend_ready() -> tuple[bool, str]:
    monitor_base = _public_monitor_base_url().rstrip("/")
    api_base = _public_api_base_url().rstrip("/")
    payload = _fetch_local_json(f"{monitor_base}/api/status?lite=1", timeout=1.5)
    if isinstance(payload, dict):
        primary_status = str(payload.get("primary_status", "") or payload.get("status", "")).strip().lower()
        if primary_status in {"ok", "paused"}:
            doctor_payload = payload.get("doctor", {})
            if not isinstance(doctor_payload, dict):
                doctor_payload = {}
            app_runtime = doctor_payload.get("app_runtime", payload.get("app_runtime", {}))
            if not isinstance(app_runtime, dict):
                app_runtime = {}
            backend_api = app_runtime.get("backend_api", {})
            if not isinstance(backend_api, dict):
                backend_api = {}
            backend_status = str(backend_api.get("status", "")).strip().lower()
            if backend_status == "ok":
                return True, "ok"
            if _http_status_ok(f"{api_base}/api/health", timeout=1.5):
                return True, "backend_health_fallback"
            return False, f"backend_api:{backend_status or 'unknown'}"
        return False, f"primary_status:{primary_status or 'unknown'}"
    if _http_status_ok(f"{api_base}/api/health", timeout=1.5):
        return True, "backend_health_fallback"
    return False, "status_lite_unavailable"


def _active_planner_subagent_owner_tasks(root: Path, board: dict | None = None) -> set[str]:
    runtime_truth = build_runtime_truth_snapshot(root, state_limit=64, event_limit=64)
    if bool(runtime_truth.get("event_store_primary", False)):
        owners: set[str] = set()
        task_lookup: dict[str, dict] = {}
        if isinstance(board, dict):
            for task in board.get("tasks", []):
                if not isinstance(task, dict):
                    continue
                task_id_value = str(task.get("id", "")).strip()
                if task_id_value:
                    task_lookup[task_id_value] = task
        active_statuses = {"running", "pending", "review", "in_progress", "blocked", "ready_to_merge", "retryable"}
        for item in (runtime_truth.get("latest_states") if isinstance(runtime_truth.get("latest_states"), list) else []):
            if not isinstance(item, dict):
                continue
            status = str(item.get("status", "")).strip().lower()
            blocking_issue = str(item.get("blocking_issue", "")).strip().lower()
            owner_role = _canonical_role(str(item.get("owner_role", "")).strip())
            target_role = _canonical_role(str(item.get("target_role", "")).strip())
            owner_task_id = str(item.get("task_id", "")).strip()
            owner_task = task_lookup.get(owner_task_id)
            owner_task_role = _canonical_role(str(owner_task.get("role") or owner_task.get("assignee") or "").strip()) if isinstance(owner_task, dict) else ""
            owner_task_state = _task_operational_state(owner_task) if isinstance(owner_task, dict) else ""
            if owner_role == "planner" and target_role in CAPABILITY_ROLES and status in active_statuses and owner_task_id:
                if isinstance(owner_task, dict) and not _task_in_active_cycle(owner_task, board):
                    continue
                if owner_task_role and owner_task_role != target_role:
                    continue
                if (
                    status == "retryable"
                    and blocking_issue == "invalid_subagent_result:start_banner_only"
                    and owner_task_state in READY_STATES
                ):
                    continue
                owners.add(owner_task_id)
        return owners
    return set()


def _task_has_delivery_evidence(task: dict) -> bool:
    for key in ("artifact", "runtime_artifact", "verify", "commit_sha", "files_touched", "summary", "last_meaningful_progress_at"):
        token = str(task.get(key, "") or "").strip().lower()
        if token and token not in {"none", "n/a", "na"}:
            return True
    for key in ("artifacts", "proof_manifests"):
        raw = task.get(key)
        if isinstance(raw, list) and any(str(item or "").strip() for item in raw):
            return True
    proof_count = str(task.get("proof_count", "") or "").strip()
    if proof_count.isdigit() and int(proof_count) > 0:
        return True
    return False


def _normalize_task_placeholder_delivery_fields(task: dict) -> bool:
    changed = False
    placeholder_scalar_keys = (
        "artifact",
        "runtime_artifact",
        "verify",
        "commit_sha",
        "files_touched",
        "tests_run",
    )
    meaningful_proof_keys = (
        "artifact",
        "runtime_artifact",
        "verify",
        "commit_sha",
        "files_touched",
        "tests_run",
    )
    meaningful_proof_count = 0

    for key in placeholder_scalar_keys:
        raw_value = str(task.get(key, "") or "").strip()
        if _value_present(raw_value):
            meaningful_proof_count += 1
            continue
        if raw_value and raw_value.lower() not in {"none", "n/a", "na"}:
            task[key] = ""
            changed = True

    for key in ("artifacts", "proof_manifests"):
        raw = task.get(key)
        if isinstance(raw, list):
            present = [str(item).strip() for item in raw if _value_present(item)]
            if present:
                meaningful_proof_count += len(present)
            if len(present) != len(raw):
                task[key] = present
                changed = True

    raw_proof_count = str(task.get("proof_count", "") or "").strip()
    if raw_proof_count == "":
        return changed
    normalized_proof_count = meaningful_proof_count
    if raw_proof_count.isdigit() and int(raw_proof_count) == normalized_proof_count:
        return changed
    task["proof_count"] = normalized_proof_count
    return True


def _active_cycle_ids(queue_obj: dict, board: dict) -> set[str]:
    cycle_ids = _board_active_batch_ids(board)
    if cycle_ids:
        return cycle_ids
    active_cycle = queue_obj.get("active_cycle") if isinstance(queue_obj, dict) else {}
    if isinstance(active_cycle, dict):
        raw_ids = active_cycle.get("active_batch_ids")
        if isinstance(raw_ids, list):
            return {str(item).strip().upper() for item in raw_ids if str(item).strip()}
    return set()


def _task_role(task: dict) -> str:
    return _canonical_role(str(task.get("role") or task.get("assignee") or task.get("owner") or ""))


def _queue_item_role(item: dict) -> str:
    return _canonical_role(str(item.get("owner_role") or item.get("role") or item.get("owner") or ""))


def _queue_item_stream_id(item: dict) -> str:
    return str(item.get("id") or item.get("stream_id") or item.get("batch_id") or "").strip().upper()


def _mark_row_blocked(row: dict, reason: str, now: str) -> bool:
    changed = False
    if str(row.get("state", "")).strip().upper() != "BLOCKED":
        row["state"] = "BLOCKED"
        changed = True
    if str(row.get("status", "")).strip().upper() != "BLOCKED":
        row["status"] = "BLOCKED"
        changed = True
    if str(row.get("blocked_reason", "")).strip() != reason:
        row["blocked_reason"] = reason
        changed = True
    if str(row.get("stalled_reason", "")).strip() != reason:
        row["stalled_reason"] = reason
        changed = True
    if changed:
        row["reconciled_at"] = now
        row["updated_at"] = now
    return changed


def _apply_policy_gate(row: dict, policy_reason: str, next_action: str, workflow: dict, now: str) -> bool:
    changed = False
    current_state = str(row.get("state", "")).strip().upper()
    current_status = str(row.get("status", "")).strip().upper()
    if str(row.get("policy_blocker", "")).strip() != policy_reason:
        row["policy_blocker"] = policy_reason
        changed = True
    if "policy_previous_state" not in row:
        row["policy_previous_state"] = current_state or "none"
        changed = True
    if "policy_previous_status" not in row:
        row["policy_previous_status"] = current_status or "none"
        changed = True
    if "policy_previous_blocked_reason" not in row:
        row["policy_previous_blocked_reason"] = str(row.get("blocked_reason", "")).strip()
        changed = True
    if "policy_previous_stalled_reason" not in row:
        row["policy_previous_stalled_reason"] = str(row.get("stalled_reason", "")).strip()
        changed = True
    if "policy_previous_next_action" not in row:
        row["policy_previous_next_action"] = str(row.get("next_action", "")).strip()
        changed = True
    if str(row.get("novelty_target_required", "")).lower() not in {"true", "1"}:
        row["novelty_target_required"] = True
        changed = True
    if row.get("novelty_target_workflow") != workflow:
        row["novelty_target_workflow"] = workflow
        changed = True
    if str(row.get("planner_hard_guard_reason", "")).strip() != "stagnation_requires_novelty_target":
        row["planner_hard_guard_reason"] = "stagnation_requires_novelty_target"
        changed = True
    if str(row.get("next_action", "")).strip() != next_action:
        row["next_action"] = next_action
        changed = True
    if current_state != "BLOCKED":
        row["state"] = "BLOCKED"
        changed = True
    if current_status != "BLOCKED":
        row["status"] = "BLOCKED"
        changed = True
    if not str(row.get("blocked_reason", "")).strip():
        row["blocked_reason"] = policy_reason
        changed = True
    if not str(row.get("stalled_reason", "")).strip():
        row["stalled_reason"] = policy_reason
        changed = True
    if changed:
        row["reconciled_at"] = now
        row["updated_at"] = now
    return changed


def _clear_policy_gate(row: dict, policy_reason: str, now: str) -> bool:
    if str(row.get("policy_blocker", "")).strip() != policy_reason:
        return False
    changed = False
    prev_state = str(row.get("policy_previous_state", "")).strip().upper()
    prev_status = str(row.get("policy_previous_status", "")).strip().upper()
    prev_blocked_reason = str(row.get("policy_previous_blocked_reason", "")).strip()
    prev_stalled_reason = str(row.get("policy_previous_stalled_reason", "")).strip()
    prev_next_action = str(row.get("policy_previous_next_action", "")).strip()

    if row.get("state") != prev_state and prev_state:
        row["state"] = prev_state
        changed = True
    if row.get("status") != prev_status and prev_status:
        row["status"] = prev_status
        changed = True
    if str(row.get("blocked_reason", "")).strip() != prev_blocked_reason:
        row["blocked_reason"] = prev_blocked_reason
        changed = True
    if str(row.get("stalled_reason", "")).strip() != prev_stalled_reason:
        row["stalled_reason"] = prev_stalled_reason
        changed = True
    if str(row.get("next_action", "")).strip() != prev_next_action:
        row["next_action"] = prev_next_action
        changed = True

    for key in (
        "policy_blocker",
        "policy_previous_state",
        "policy_previous_status",
        "policy_previous_blocked_reason",
        "policy_previous_stalled_reason",
        "policy_previous_next_action",
        "planner_hard_guard_reason",
        "novelty_target_workflow",
        "novelty_target_required",
    ):
        if key in row:
            row.pop(key, None)
            changed = True
    if changed:
        row["reconciled_at"] = now
        row["updated_at"] = now
    return changed


def _apply_delivery_runtime_gate(row: dict, policy_reason: str, next_action: str, gate_reason: str, now: str) -> bool:
    existing_policy = str(row.get("policy_blocker", "")).strip()
    if existing_policy and existing_policy != policy_reason:
        return False
    changed = False
    current_state = str(row.get("state", "")).strip().upper()
    current_status = str(row.get("status", "")).strip().upper()
    if existing_policy != policy_reason:
        row["policy_blocker"] = policy_reason
        changed = True
    if "delivery_gate_previous_state" not in row:
        row["delivery_gate_previous_state"] = current_state or "none"
        changed = True
    if "delivery_gate_previous_status" not in row:
        row["delivery_gate_previous_status"] = current_status or "none"
        changed = True
    if "delivery_gate_previous_blocked_reason" not in row:
        row["delivery_gate_previous_blocked_reason"] = str(row.get("blocked_reason", "")).strip()
        changed = True
    if "delivery_gate_previous_stalled_reason" not in row:
        row["delivery_gate_previous_stalled_reason"] = str(row.get("stalled_reason", "")).strip()
        changed = True
    if "delivery_gate_previous_next_action" not in row:
        row["delivery_gate_previous_next_action"] = str(row.get("next_action", "")).strip()
        changed = True
    gate_payload = {
        "active": True,
        "reason": policy_reason,
        "delivery_backend_reason": gate_reason,
        "next_action": next_action,
        "updated_at": now,
    }
    if row.get("delivery_runtime_gate") != gate_payload:
        row["delivery_runtime_gate"] = gate_payload
        changed = True
    if str(row.get("next_action", "")).strip() != next_action:
        row["next_action"] = next_action
        changed = True
    if current_state != "BLOCKED":
        row["state"] = "BLOCKED"
        changed = True
    if current_status != "BLOCKED":
        row["status"] = "BLOCKED"
        changed = True
    if str(row.get("blocked_reason", "")).strip() != policy_reason:
        row["blocked_reason"] = policy_reason
        changed = True
    if str(row.get("stalled_reason", "")).strip() != gate_reason:
        row["stalled_reason"] = gate_reason
        changed = True
    if changed:
        row["reconciled_at"] = now
        row["updated_at"] = now
    return changed


def _clear_delivery_runtime_gate(row: dict, policy_reason: str, now: str) -> bool:
    if str(row.get("policy_blocker", "")).strip() != policy_reason:
        return False
    changed = False
    prev_state = str(row.get("delivery_gate_previous_state", "")).strip().upper()
    prev_status = str(row.get("delivery_gate_previous_status", "")).strip().upper()
    prev_blocked_reason = str(row.get("delivery_gate_previous_blocked_reason", "")).strip()
    prev_stalled_reason = str(row.get("delivery_gate_previous_stalled_reason", "")).strip()
    prev_next_action = str(row.get("delivery_gate_previous_next_action", "")).strip()
    if prev_state and row.get("state") != prev_state:
        row["state"] = prev_state
        changed = True
    if prev_status and row.get("status") != prev_status:
        row["status"] = prev_status
        changed = True
    if str(row.get("blocked_reason", "")).strip() != prev_blocked_reason:
        row["blocked_reason"] = prev_blocked_reason
        changed = True
    if str(row.get("stalled_reason", "")).strip() != prev_stalled_reason:
        row["stalled_reason"] = prev_stalled_reason
        changed = True
    if str(row.get("next_action", "")).strip() != prev_next_action:
        row["next_action"] = prev_next_action
        changed = True
    for key in (
        "policy_blocker",
        "delivery_runtime_gate",
        "delivery_gate_previous_state",
        "delivery_gate_previous_status",
        "delivery_gate_previous_blocked_reason",
        "delivery_gate_previous_stalled_reason",
        "delivery_gate_previous_next_action",
    ):
        if key in row:
            row.pop(key, None)
            changed = True
    if changed:
        row["reconciled_at"] = now
        row["updated_at"] = now
    return changed


def _workboard_projection_missing_fields(board: dict, active_cycle_ids: set[str]) -> int:
    missing = 0
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        if active_cycle_ids and _task_stream_id(task) not in active_cycle_ids:
            continue
        if str(task.get("state", "")).strip().upper() in DONE_STATES:
            continue
        if not str(task.get("state") or task.get("status") or "").strip():
            missing += 1
        if not str(task.get("role") or task.get("owner") or task.get("assignee") or "").strip():
            missing += 1
        if not str(task.get("next_action") or task.get("next") or "").strip():
            missing += 1
        if str(task.get("proof_count", "") or "").strip() == "":
            missing += 1
    return missing


def _runtime_item_proof_fields(item: dict) -> dict[str, str]:
    proof = item.get("delivery_proof")
    proof = proof if isinstance(proof, dict) else {}
    result = item.get("result")
    result = result if isinstance(result, dict) else {}
    merged: dict[str, str] = {}
    for key in ("artifact", "verify", "commit_sha", "tests_run", "summary", "proof_manifest"):
        value = str(result.get(key, "") or proof.get(key, "") or item.get(key, "") or "").strip()
        if _value_present(value):
            merged[key] = value
    return merged


def _runtime_item_proof_count(item: dict) -> int:
    return len(_runtime_item_proof_fields(item))


def _runtime_item_next_action(item: dict) -> str:
    for key in ("recommended_next", "next_action", "next"):
        token = str(item.get(key, "") or "").strip()
        if token and token.lower() not in {"none", "n/a", "na"}:
            return token
    blocking_issue = str(item.get("blocking_issue", "") or "").strip()
    if blocking_issue and not _runtime_blocking_issue_allows_semantic_success(blocking_issue):
        return f"resolve_{blocking_issue}"
    return ""


def _runtime_item_progress_at(item: dict) -> str:
    for key in ("updated_at", "completed_at", "ts_utc", "timestamp"):
        token = str(item.get(key, "") or "").strip()
        if token:
            return token
    return ""


def _runtime_item_is_success(item: dict) -> bool:
    status = str(item.get("status", "") or "").strip().lower()
    result_status = str(((item.get("capability_result") or {}).get("status") or "")).strip().lower()
    next_action = str(item.get("next_action", "") or "").strip().lower()
    proof_count = _runtime_item_proof_count(item)
    blocking_issue = str(item.get("blocking_issue", "") or "").strip()
    if status in {"completed", "done", "pass", "passed", "ok", "success", "merged"}:
        return True
    if status in {"failed", "retryable"}:
        if proof_count > 0 and _runtime_blocking_issue_allows_semantic_success(blocking_issue):
            return True
    if status == "running" and next_action == "wait_or_collect_result" and proof_count > 0 and _runtime_blocking_issue_is_noneish(blocking_issue):
        if result_status in {"completed", "done", "pass", "passed", "ok", "success", "merged", "failed", "retryable"}:
            return True
    return False


def _sync_runtime_truth_projection(root: Path, board: dict, active_cycle_ids: set[str], now: str) -> dict[str, int]:
    runtime_truth = build_runtime_truth_snapshot(root, state_limit=256, event_limit=128)
    latest_states = runtime_truth.get("latest_states")
    quarantined_retryable_residue = runtime_truth.get("quarantined_retryable_residue")
    if not isinstance(latest_states, list):
        return {"runtime_projection_synced": 0, "runtime_completion_consumed": 0}
    if not isinstance(quarantined_retryable_residue, list):
        quarantined_retryable_residue = []

    by_task_id: dict[str, dict] = {}
    for item in latest_states:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("task_id", "") or "").strip()
        if not task_id:
            continue
        stream_id = str(item.get("stream_id", "") or item.get("batch_id", "") or "").strip().upper()
        if active_cycle_ids and stream_id and stream_id not in active_cycle_ids:
            continue
        by_task_id[task_id] = item
    for item in quarantined_retryable_residue:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("task_id", "") or "").strip()
        if not task_id:
            continue
        stream_id = str(item.get("stream_id", "") or item.get("batch_id", "") or "").strip().upper()
        if active_cycle_ids and stream_id and stream_id not in active_cycle_ids:
            continue
        by_task_id[task_id] = item

    synced = 0
    completed = 0
    quarantined = 0
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id", "") or "").strip()
        if not task_id:
            continue
        if active_cycle_ids and _task_stream_id(task) not in active_cycle_ids:
            continue
        item = by_task_id.get(task_id)
        if not isinstance(item, dict):
            continue
        proof_count = _runtime_item_proof_count(item)
        runtime_status = str(item.get("status", "") or "").strip().lower()
        blocking_issue = str(item.get("blocking_issue", "") or "").strip().lower()
        task_state = _task_operational_state(task)
        quarantined_ready_residue = (
            runtime_status == "quarantined"
            and blocking_issue.startswith("quarantined_retryable_residue:")
        )
        retryable_banner_residue = (
            runtime_status == "retryable"
            and blocking_issue == "invalid_subagent_result:start_banner_only"
            and task_state in (READY_STATES | ACTIVE_IN_PROGRESS_STATES)
            and proof_count == 0
        )
        if quarantined_ready_residue:
            if _quarantine_retryable_runtime_residue(task, item, now):
                quarantined += 1
            continue
        if retryable_banner_residue:
            if _quarantine_retryable_runtime_residue(task, item, now):
                quarantined += 1
            continue
        changed = _clear_runtime_truth_quarantine(task, now)
        role = _task_role(task)
        if not str(task.get("owner", "") or "").strip() and role:
            task["owner"] = role
            changed = True
        if not str(task.get("status", "") or "").strip() and str(task.get("state", "") or "").strip():
            task["status"] = str(task.get("state", "")).strip()
            changed = True
        if proof_count > 0 and task.get("proof_count") != proof_count:
            task["proof_count"] = proof_count
            changed = True
        next_action = _runtime_item_next_action(item)
        if next_action and str(task.get("next_action", "") or "").strip() != next_action:
            task["next_action"] = next_action
            changed = True
        progress_at = _runtime_item_progress_at(item)
        if progress_at and str(task.get("last_meaningful_progress_at", "") or "").strip() != progress_at:
            task["last_meaningful_progress_at"] = progress_at
            changed = True
        for key, value in _runtime_item_proof_fields(item).items():
            if str(task.get(key, "") or "").strip() != value:
                task[key] = value
                changed = True
        if _runtime_item_is_success(item) and proof_count > 0 and str(task.get("state", "")).strip().upper() not in DONE_STATES:
            task["state"] = "DONE"
            task["status"] = "DONE"
            if progress_at and not str(task.get("completed_at", "") or "").strip():
                task["completed_at"] = progress_at
            _clear_terminal_execution_flags(task, now)
            changed = True
            completed += 1
        if changed:
            task["runtime_truth_synced_at"] = now
            task["updated_at"] = now
            synced += 1
    return {
        "runtime_projection_synced": synced,
        "runtime_completion_consumed": completed,
        "runtime_retryable_quarantined": quarantined,
    }


def _default_next_action_for_state(state: str) -> str:
    token = str(state or "").strip().upper()
    if token in {"WAITING_DEP"}:
        return "wait_for_dependencies"
    if token in {"BLOCKED"}:
        return "resolve_blocker"
    if token in READY_STATES:
        return "claim_now"
    if token in ACTIVE_IN_PROGRESS_STATES:
        return "continue_in_progress"
    return ""


def _task_operational_state(task: dict) -> str:
    status = str(task.get("status", "") or "").strip().upper()
    state = str(task.get("state", "") or "").strip().upper()
    if status in READY_STATES or status in DONE_STATES or status in {"BLOCKED", "WAITING_DEP"}:
        return status
    if state:
        return state
    return status


def _clear_runtime_truth_quarantine(task: dict, now: str) -> bool:
    marker_present = bool(task.get("runtime_truth_quarantined")) or any(
        str(task.get(key, "") or "").strip()
        for key in ("runtime_truth_quarantine_reason", "runtime_truth_quarantine_issue", "runtime_truth_quarantine_at")
    )
    if not marker_present:
        return False
    changed = False
    resets = {
        "runtime_truth_quarantined": False,
        "runtime_truth_quarantine_reason": "",
        "runtime_truth_quarantine_issue": "",
        "runtime_truth_quarantine_at": "",
    }
    for key, value in resets.items():
        if task.get(key) != value:
            task[key] = value
            changed = True
    if changed:
        task["reconciled_at"] = now
        task["updated_at"] = now
    return changed


def _quarantine_retryable_runtime_residue(task: dict, item: dict, now: str) -> bool:
    changed = False
    issue = str(item.get("blocking_issue", "") or "").strip() or "invalid_subagent_result:start_banner_only"
    desired_state = ""
    issue_token = issue.lower()
    if issue_token.startswith("quarantined_retryable_residue:"):
        desired_state = issue.split(":", 1)[1].strip().upper()
    if desired_state not in READY_STATES | DONE_STATES | {"BLOCKED", "WAITING_DEP"}:
        current_state = _task_operational_state(task)
        if current_state in READY_STATES | DONE_STATES | {"BLOCKED", "WAITING_DEP"}:
            desired_state = current_state
        else:
            desired_state = _preferred_ready_state_for_role(_task_role(task))
    updates = {
        "runtime_truth_quarantined": True,
        "runtime_truth_quarantine_reason": "stale_retryable_after_ready",
        "runtime_truth_quarantine_issue": issue,
        "runtime_truth_quarantine_at": now,
    }
    for key, value in updates.items():
        if task.get(key) != value:
            task[key] = value
            changed = True
    if desired_state and str(task.get("status", "") or "").strip().upper() != desired_state:
        task["status"] = desired_state
        changed = True
    if desired_state and str(task.get("state", "") or "").strip().upper() != desired_state:
        task["state"] = desired_state
        changed = True
    desired_next_action = _default_next_action_for_state(desired_state)
    if desired_next_action and str(task.get("next_action", "") or "").strip() != desired_next_action:
        task["next_action"] = desired_next_action
        changed = True
    for key in (
        "blocked_reason",
        "stalled_reason",
        "planner_takeover_reason",
        "admin_recovery_reason",
        "dev_recovery_reason",
        "last_capability_failure_mode",
        "dev_execution_state",
    ):
        if str(task.get(key, "") or "").strip():
            task[key] = ""
            changed = True
    for key in ("planner_takeover_required", "admin_recovery_required", "dev_recovery_required"):
        if bool(task.get(key)):
            task[key] = False
            changed = True
    for key in ("dev_no_progress_streak", "dev_orphaned_streak", "dev_invalid_result_streak"):
        if int(task.get(key) or 0) != 0:
            task[key] = 0
            changed = True
    if changed:
        task["reconciled_at"] = now
        task["updated_at"] = now
    return changed


def _normalize_projection_operational_fields(board: dict, active_cycle_ids: set[str], now: str) -> int:
    changed = 0
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        if active_cycle_ids and _task_stream_id(task) not in active_cycle_ids:
            continue
        row_changed = False
        state = str(task.get("state", "") or "").strip()
        role = _task_role(task)
        status = str(task.get("status", "") or "").strip()
        status_upper = status.upper()
        state_upper = state.upper()
        if status_upper in READY_STATES or status_upper in DONE_STATES or status_upper in {"BLOCKED", "WAITING_DEP"}:
            if state_upper != status_upper:
                task["state"] = status_upper
                state = status_upper
                row_changed = True
        elif state and (not status or status_upper != state_upper):
            task["status"] = state
            row_changed = True
        if role and not str(task.get("owner", "") or "").strip():
            task["owner"] = role
            row_changed = True
        if str(task.get("proof_count", "") or "").strip() == "":
            task["proof_count"] = 0
            row_changed = True
        if _normalize_task_placeholder_delivery_fields(task):
            row_changed = True
        if not str(task.get("next_action", "") or "").strip():
            next_action = _default_next_action_for_state(state)
            if next_action:
                task["next_action"] = next_action
                row_changed = True
        if row_changed:
            task["projection_normalized_at"] = now
            task["updated_at"] = now
            changed += 1
    return changed


def _task_effectively_done(task: dict) -> bool:
    state = str(task.get("state", "")).strip().upper()
    if state in DONE_STATES:
        return True
    return bool(str(task.get("completed_at", "")).strip())


def _clear_terminal_execution_flags(task: dict, now: str) -> bool:
    changed = False
    terminal_resets = {
        "blocked_reason": "",
        "stalled_reason": "",
        "planner_takeover_required": False,
        "planner_takeover_reason": "",
        "admin_recovery_required": False,
        "admin_recovery_reason": "",
        "dev_recovery_required": False,
        "dev_recovery_reason": "",
        "dev_execution_state": "",
        "dev_no_progress_streak": 0,
        "dev_orphaned_streak": 0,
        "dev_invalid_result_streak": 0,
    }
    for key, value in terminal_resets.items():
        if task.get(key) != value:
            task[key] = value
            changed = True
    if str(task.get("last_capability_failure_mode", "")).strip():
        task["last_capability_failure_mode"] = ""
        changed = True
    if changed:
        task["reconciled_at"] = now
        task["updated_at"] = now
    return changed


def _parse_contract(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().upper()
        if key and key not in values:
            values[key] = value.strip()
    return values


def _render_contract(values: dict[str, str]) -> str:
    ordered = ["STATUS", "DELTA", "EVIDENCE", "RISKS", "NEXT", "VERDICT", "BLOCKER_ID", "NEXT_ACTION_UNIQUE"]
    return "\n".join(f"{key}: {values.get(key, ).strip()}" for key in ordered) + "\n"


def _evidence_pairs(raw: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for frag in str(raw or "").split(";"):
        item = frag.strip()
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if key and key not in pairs:
            pairs[key] = value.strip()
    return pairs


def _upsert_evidence(raw: str, key: str, value: str) -> str:
    pairs = _evidence_pairs(raw)
    pairs[key.strip().lower()] = value
    preferred = [
        "task_update",
        "lock_check",
        "run_note",
        "issues",
        "issue_count",
        "issue_severity",
    ]
    parts: list[str] = []
    seen: set[str] = set()
    for item in preferred:
        if item in pairs:
            parts.append(f"{item}={pairs[item]}")
            seen.add(item)
    for item in sorted(pairs.keys()):
        if item in seen:
            continue
        parts.append(f"{item}={pairs[item]}")
    return "; ".join(parts)


def _contract_has_runtime_blocker(values: dict[str, str]) -> bool:
    blocker = str(values.get("BLOCKER_ID", "") or "").strip().upper()
    return blocker in RUNTIME_BLOCKERS or blocker.startswith("RUNTIME_")


def _clear_runtime_blocker_in_contract(path: Path, role: str, now: str) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    values = _parse_contract(text)
    if not _contract_has_runtime_blocker(values):
        return False
    if values.get("STATUS", "").strip().upper() not in {"BLOCKED", "WAIT", "FAIL"}:
        return False
    values["STATUS"] = "WAIT"
    values["DELTA"] = "RUNTIME_RECOVERED_SOFT"
    values["VERDICT"] = "PASS"
    values["BLOCKER_ID"] = "NONE"
    values["RISKS"] = "runtime blocker stale auto-cleared after healthy probes"
    values["NEXT"] = f"owner={role}; action=resume normal execution after runtime recovery"
    values["NEXT_ACTION_UNIQUE"] = f"RUNTIME_RECOVERED_SOFT_{role.upper()}_{int(time.time())}"
    evidence = values.get("EVIDENCE", "")
    evidence = _upsert_evidence(evidence, "runtime_recovered_live_probe", "1")
    evidence = _upsert_evidence(evidence, "runtime_recovered_at", now)
    values["EVIDENCE"] = evidence
    path.write_text(_render_contract(values), encoding="utf-8")
    return True


def run_reconciler(config: ReconcileConfig, probe_runtime_ok: Callable[[], bool] | None = None, now_epoch: int | None = None) -> dict[str, int | str]:
    probe_runtime_ok = probe_runtime_ok or _runtime_probes_ok
    now_epoch = int(now_epoch or time.time())
    now = now_iso()
    queue_obj = _load_json(config.queue_path, {"items": []})
    if not isinstance(queue_obj, dict):
        queue_obj = {"items": []}

    report: dict[str, int | str] = {
        "at": now,
        "fixes_applied": 0,
        "parked_inprogress_fixed": 0,
        "runtime_blockers_cleared": 0,
        "stale_locks_removed": 0,
        "stale_inprogress_marked": 0,
        "proof_transition_stalled": 0,
        "ready_starvation_detected": 0,
        "dependency_starvation_detected": 0,
        "completed_state_repaired": 0,
        "stagnation_hard_guarded": 0,
        "downstream_novelty_blocked": 0,
        "projection_decision_disabled": 0,
        "runtime_projection_synced": 0,
        "runtime_completion_consumed": 0,
        "runtime_retryable_quarantined": 0,
        "novelty_target_overdue": 0,
        "delivery_runtime_blocked": 0,
        "delivery_runtime_gate_cleared": 0,
    }
    capability_stall_seconds = max(60, int(os.environ.get("FC_RECONCILE_CAPABILITY_STALL_SECONDS", "300")))
    proof_transition_stale_seconds = max(300, int(os.environ.get("FC_RECONCILE_PROOF_TRANSITION_STALE_SECONDS", "1800")))

    with board_lock(config.board_path):
        board = load_board(config.board_path)
        if not isinstance(board, dict):
            board = {"tasks": [], "streams": [], "events": []}
        active_subagent_owner_tasks = _active_planner_subagent_owner_tasks(config.root, board)
        active_cycle_ids = _active_cycle_ids(queue_obj, board)
        active_cycle = queue_obj.get("active_cycle")
        if not isinstance(active_cycle, dict):
            active_cycle = {}
        queue_meta = queue_obj.get("meta")
        if not isinstance(queue_meta, dict):
            queue_meta = {}
            queue_obj["meta"] = queue_meta

        stagnation_alert = queue_meta.get("stagnation_alert")
        recent_classes: list[str] = []
        if isinstance(stagnation_alert, dict):
            raw_classes = stagnation_alert.get("recent_classes")
            if isinstance(raw_classes, list):
                recent_classes = [str(item).strip().lower() for item in raw_classes if str(item).strip()]
        novelty_target = str(active_cycle.get("novelty_target", "") or "").strip()
        user_visible_delta = str(active_cycle.get("user_visible_delta", "") or "").strip()
        if not novelty_target and isinstance(stagnation_alert, dict):
            novelty_target = str(stagnation_alert.get("novelty_target", "") or "").strip()
        if not novelty_target:
            novelty_target = str(queue_meta.get("novelty_target", "") or "").strip()
        if not user_visible_delta and isinstance(stagnation_alert, dict):
            user_visible_delta = str(stagnation_alert.get("user_visible_delta", "") or "").strip()
        if not user_visible_delta:
            user_visible_delta = str(queue_meta.get("user_visible_delta", "") or "").strip()
        missing_fields: list[str] = []
        if not novelty_target:
            missing_fields.append("novelty_target")
        if not user_visible_delta:
            missing_fields.append("user_visible_delta")
        stagnation_active = (
            bool(stagnation_alert)
            and len(recent_classes) >= 2
            and all(item in {"validation", "reuse_only"} for item in recent_classes[:2])
            and bool(missing_fields)
        )
        if stagnation_active:
            scope_key = str(stagnation_alert.get("scope_key", "")).strip() if isinstance(stagnation_alert, dict) else ""
            existing_audit = queue_meta.get("novelty_target_audit")
            first_required_at = str(existing_audit.get("first_required_at", "")).strip() if isinstance(existing_audit, dict) else ""
            if not first_required_at:
                hard_guard = queue_meta.get("planner_hard_guard")
                if isinstance(hard_guard, dict):
                    first_required_at = str(hard_guard.get("first_required_at", "")).strip()
            if not first_required_at:
                first_required_at = now
            age_s = max(0, int(time.time()) - _parse_iso_epoch(first_required_at))
            audit_status = "overdue" if age_s >= NOVELTY_TARGET_OVERDUE_SECONDS else "required"
            next_action = "define_novelty_target" if "novelty_target" in missing_fields else "define_user_visible_delta"
            workflow = {
                "status": "required",
                "owner_role": "planner",
                "batch_id": sorted(active_cycle_ids)[0] if active_cycle_ids else "none",
                "scope_key": scope_key or "none",
                "reason": "stagnation_requires_novelty_target",
                "next_action": next_action,
                "policy": "no_new_downstream_work",
                "required_fields": [
                    "novelty_target",
                    "user_visible_delta",
                    "scope_delta",
                    "success_metric",
                ],
                "missing_fields": missing_fields[:],
                "clear_when": "novelty_target_present",
                "recent_classes": recent_classes[:3],
                "updated_at": now,
            }
            queue_meta["planner_hard_guard"] = {
                "active": True,
                "reason": "stagnation_requires_novelty_target",
                "recent_classes": recent_classes[:3],
                "next_action": next_action,
                "first_required_at": first_required_at,
                "missing_fields": missing_fields[:],
                "updated_at": now,
            }
            queue_meta["novelty_target_workflow"] = workflow
            queue_meta["novelty_target_required"] = True
            queue_meta["novelty_target_missing_fields"] = missing_fields[:]
            queue_meta["novelty_target_audit"] = {
                "status": audit_status,
                "reason": "stagnation_requires_novelty_target",
                "owner_role": "planner",
                "batch_id": sorted(active_cycle_ids)[0] if active_cycle_ids else "none",
                "scope_key": scope_key or "none",
                "missing_fields": missing_fields[:],
                "next_action": next_action,
                "first_required_at": first_required_at,
                "age_s": age_s,
                "threshold_s": NOVELTY_TARGET_OVERDUE_SECONDS,
                "updated_at": now,
            }
            if audit_status == "overdue":
                report["novelty_target_overdue"] = 1
            for task in board.get("tasks", []):
                if not isinstance(task, dict):
                    continue
                if active_cycle_ids and _task_stream_id(task) not in active_cycle_ids:
                    continue
                state = str(task.get("state", "")).strip().upper()
                if state not in READY_STATES and state not in ACTIVE_IN_PROGRESS_STATES:
                    continue
                if _task_role(task) == "planner":
                    task["novelty_target_required"] = True
                    task["novelty_target_workflow"] = workflow
                    task["novelty_target_missing_fields"] = missing_fields[:]
                    task["next_action"] = next_action
                    if _mark_row_blocked(task, "stagnation_requires_novelty_target", now):
                        report["stagnation_hard_guarded"] = int(report["stagnation_hard_guarded"]) + 1
                    continue
                if _apply_policy_gate(
                    task,
                    "novelty_target_required_before_downstream",
                    "wait_for_planner_novelty_target",
                    workflow,
                    now,
                ):
                    report["downstream_novelty_blocked"] = int(report["downstream_novelty_blocked"]) + 1
            for stream in board.get("streams", []):
                if not isinstance(stream, dict):
                    continue
                stream_id = str(stream.get("id", "")).strip().upper()
                owner_role = _canonical_role(str(stream.get("owner_role") or stream.get("role") or ""))
                if active_cycle_ids and stream_id not in active_cycle_ids:
                    continue
                state = str(stream.get("state", "")).strip().upper()
                if state not in READY_STATES and state not in ACTIVE_IN_PROGRESS_STATES:
                    continue
                if owner_role == "planner":
                    stream["novelty_target_required"] = True
                    stream["novelty_target_workflow"] = workflow
                    stream["novelty_target_missing_fields"] = missing_fields[:]
                    stream["next_action"] = next_action
                    if _mark_row_blocked(stream, "stagnation_requires_novelty_target", now):
                        report["stagnation_hard_guarded"] = int(report["stagnation_hard_guarded"]) + 1
                    continue
                if _apply_policy_gate(
                    stream,
                    "novelty_target_required_before_downstream",
                    "wait_for_planner_novelty_target",
                    workflow,
                    now,
                ):
                    report["downstream_novelty_blocked"] = int(report["downstream_novelty_blocked"]) + 1
            for item in queue_obj.get("items", []):
                if not isinstance(item, dict):
                    continue
                if active_cycle_ids and _queue_item_stream_id(item) not in active_cycle_ids:
                    continue
                state = str(item.get("state", "")).strip().upper()
                if state not in READY_STATES and state not in ACTIVE_IN_PROGRESS_STATES:
                    continue
                item["novelty_target_required"] = True
                item["novelty_target_workflow"] = workflow
                item["novelty_target_missing_fields"] = missing_fields[:]
                if _queue_item_role(item) == "planner":
                    item["next_action"] = (
                        "planner: define novelty_target + user_visible_delta + scope_delta + success_metric before reopening downstream work"
                    )
                    if _mark_row_blocked(item, "stagnation_requires_novelty_target", now):
                        report["stagnation_hard_guarded"] = int(report["stagnation_hard_guarded"]) + 1
                    continue
                if _apply_policy_gate(
                    item,
                    "novelty_target_required_before_downstream",
                    "wait_for_planner_novelty_target",
                    workflow,
                    now,
                ):
                    report["downstream_novelty_blocked"] = int(report["downstream_novelty_blocked"]) + 1
        elif queue_meta.get("planner_hard_guard"):
            queue_meta["planner_hard_guard"] = {
                "active": False,
                "reason": "none",
                "updated_at": now,
            }
            queue_meta["novelty_target_workflow"] = {
                "status": "clear",
                "reason": "novelty_target_present",
                "updated_at": now,
            }
            queue_meta["novelty_target_required"] = False
            queue_meta["novelty_target_missing_fields"] = []
            queue_meta["novelty_target_audit"] = {
                "status": "clear",
                "reason": "novelty_target_present",
                "updated_at": now,
            }
            for task in board.get("tasks", []):
                if not isinstance(task, dict):
                    continue
                if active_cycle_ids and _task_stream_id(task) not in active_cycle_ids:
                    continue
                _clear_policy_gate(task, "novelty_target_required_before_downstream", now)
            for stream in board.get("streams", []):
                if not isinstance(stream, dict):
                    continue
                stream_id = str(stream.get("id", "")).strip().upper()
                if active_cycle_ids and stream_id not in active_cycle_ids:
                    continue
                _clear_policy_gate(stream, "novelty_target_required_before_downstream", now)
            for item in queue_obj.get("items", []):
                if not isinstance(item, dict):
                    continue
                if active_cycle_ids and _queue_item_stream_id(item) not in active_cycle_ids:
                    continue
                _clear_policy_gate(item, "novelty_target_required_before_downstream", now)

        projection_sync = _sync_runtime_truth_projection(config.root, board, active_cycle_ids, now)
        report["runtime_projection_synced"] = int(projection_sync.get("runtime_projection_synced", 0))
        report["runtime_completion_consumed"] = int(projection_sync.get("runtime_completion_consumed", 0))
        report["runtime_retryable_quarantined"] = int(projection_sync.get("runtime_retryable_quarantined", 0))
        report["runtime_projection_synced"] = int(report["runtime_projection_synced"]) + _normalize_projection_operational_fields(board, active_cycle_ids, now)

        # 1) operational status wins over stale in-progress state when the row
        # is still planner-dispatchable/ready in canonical meaning.
        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            raw_state = str(task.get("state", "")).strip().upper()
            operational_state = _task_operational_state(task)
            if raw_state not in ACTIVE_IN_PROGRESS_STATES:
                continue
            if operational_state not in READY_STATES and operational_state not in {"BLOCKED", "WAITING_DEP"}:
                continue
            changed = False
            if str(task.get("state", "")).strip().upper() != operational_state:
                task["state"] = operational_state
                changed = True
            if str(task.get("status", "")).strip().upper() != operational_state:
                task["status"] = operational_state
                changed = True
            desired_next_action = _default_next_action_for_state(operational_state)
            if desired_next_action and str(task.get("next_action", "")).strip() != desired_next_action:
                task["next_action"] = desired_next_action
                changed = True
            if changed:
                task["stalled_reason"] = "operational_status_overrode_stale_in_progress_state"
                task["reconciled_at"] = now
                task["updated_at"] = now
                report["operational_state_repaired"] = int(report.get("operational_state_repaired", 0)) + 1

        delivery_policy_reason = "backend_runtime_required_before_takeover"
        delivery_next_action = "wait_for_backend_recovery_then_retry_capability"
        delivery_backend_ok, delivery_backend_reason = _delivery_backend_ready()
        delivery_gate_stream_ids: set[str] = set()
        delivery_gate_task_ids: set[str] = set()
        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            stream_id = _task_stream_id(task)
            if active_cycle_ids and stream_id not in active_cycle_ids:
                continue
            task_id_value = str(task.get("id", "") or "").strip()
            role = _task_role(task)
            policy_blocker = str(task.get("policy_blocker", "")).strip()
            operational_state = _task_operational_state(task)
            next_action = str(task.get("next_action", "") or "").strip().lower()
            should_gate = (
                role in CAPABILITY_ROLES
                and (
                    policy_blocker == delivery_policy_reason
                    or (
                        operational_state in READY_STATES
                        and (bool(task.get("planner_takeover_required")) or "retry_capability" in next_action)
                    )
                )
            )
            if not should_gate:
                continue
            if task_id_value:
                delivery_gate_task_ids.add(task_id_value)
            if stream_id:
                delivery_gate_stream_ids.add(stream_id)
            if delivery_backend_ok:
                if _clear_delivery_runtime_gate(task, delivery_policy_reason, now):
                    report["delivery_runtime_gate_cleared"] = int(report["delivery_runtime_gate_cleared"]) + 1
            else:
                if _apply_delivery_runtime_gate(task, delivery_policy_reason, delivery_next_action, delivery_backend_reason, now):
                    report["delivery_runtime_blocked"] = int(report["delivery_runtime_blocked"]) + 1

        for stream in board.get("streams", []):
            if not isinstance(stream, dict):
                continue
            stream_id = str(stream.get("id", "") or "").strip().upper()
            policy_blocker = str(stream.get("policy_blocker", "")).strip()
            state = str(stream.get("state", "") or "").strip().upper()
            if stream_id not in delivery_gate_stream_ids and policy_blocker != delivery_policy_reason:
                continue
            if stream_id not in delivery_gate_stream_ids and policy_blocker == delivery_policy_reason and not delivery_backend_ok:
                continue
            if state not in READY_STATES and state not in ACTIVE_IN_PROGRESS_STATES and policy_blocker != delivery_policy_reason:
                continue
            if delivery_backend_ok:
                if _clear_delivery_runtime_gate(stream, delivery_policy_reason, now):
                    report["delivery_runtime_gate_cleared"] = int(report["delivery_runtime_gate_cleared"]) + 1
            else:
                if _apply_delivery_runtime_gate(stream, delivery_policy_reason, delivery_next_action, delivery_backend_reason, now):
                    report["delivery_runtime_blocked"] = int(report["delivery_runtime_blocked"]) + 1

        for item in queue_obj.get("items", []):
            if not isinstance(item, dict):
                continue
            stream_id = _queue_item_stream_id(item)
            policy_blocker = str(item.get("policy_blocker", "")).strip()
            state = str(item.get("state", "") or "").strip().upper()
            if stream_id not in delivery_gate_stream_ids and policy_blocker != delivery_policy_reason:
                continue
            if stream_id not in delivery_gate_stream_ids and policy_blocker == delivery_policy_reason and not delivery_backend_ok:
                continue
            if state not in READY_STATES and state not in ACTIVE_IN_PROGRESS_STATES and policy_blocker != delivery_policy_reason:
                continue
            if delivery_backend_ok:
                if _clear_delivery_runtime_gate(item, delivery_policy_reason, now):
                    report["delivery_runtime_gate_cleared"] = int(report["delivery_runtime_gate_cleared"]) + 1
            else:
                if _apply_delivery_runtime_gate(item, delivery_policy_reason, delivery_next_action, delivery_backend_reason, now):
                    report["delivery_runtime_blocked"] = int(report["delivery_runtime_blocked"]) + 1

        if delivery_gate_stream_ids and not delivery_backend_ok:
            queue_meta["delivery_runtime_gate"] = {
                "active": True,
                "reason": delivery_policy_reason,
                "delivery_backend_reason": delivery_backend_reason,
                "affected_stream_ids": sorted(delivery_gate_stream_ids),
                "affected_task_ids": sorted(delivery_gate_task_ids),
                "next_action": delivery_next_action,
                "updated_at": now,
            }
        elif queue_meta.get("delivery_runtime_gate"):
            queue_meta["delivery_runtime_gate"] = {
                "active": False,
                "reason": "backend_runtime_recovered",
                "affected_stream_ids": [],
                "affected_task_ids": [],
                "updated_at": now,
            }

        # 2) parked + in_progress contradictions
        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            if _task_effectively_done(task) and str(task.get("state", "")).strip().upper() not in DONE_STATES:
                task["state"] = "DONE"
                _clear_terminal_execution_flags(task, now)
                report["completed_state_repaired"] = int(report["completed_state_repaired"]) + 1
                continue
            if _task_effectively_done(task):
                if _clear_terminal_execution_flags(task, now):
                    report["completed_state_repaired"] = int(report["completed_state_repaired"]) + 1
                continue
            if not task.get("parked_by_rebuild"):
                continue
            state = str(task.get("state", "")).strip().upper()
            if state not in ACTIVE_IN_PROGRESS_STATES:
                continue
            task["state"] = _preferred_ready_state_for_role(str(task.get("role") or task.get("assignee") or ""))
            task["stalled_reason"] = "parked_by_rebuild_cannot_stay_in_progress"
            task["reconciled_at"] = now
            task["updated_at"] = now
            report["parked_inprogress_fixed"] = int(report["parked_inprogress_fixed"]) + 1

        for stream in board.get("streams", []):
            if not isinstance(stream, dict):
                continue
            if not stream.get("parked_by_rebuild"):
                continue
            state = str(stream.get("state", "")).strip().upper()
            if state not in ACTIVE_IN_PROGRESS_STATES:
                continue
            stream_id = str(stream.get("id", "")).strip()
            stream["state"] = _preferred_ready_state_for_stream(board, stream_id, str(stream.get("owner_role") or ""))
            stream["stalled_reason"] = "parked_by_rebuild_cannot_stay_in_progress"
            stream["reconciled_at"] = now
            stream["updated_at"] = now
            report["parked_inprogress_fixed"] = int(report["parked_inprogress_fixed"]) + 1

        for item in queue_obj.get("items", []):
            if not isinstance(item, dict):
                continue
            if not item.get("parked_by_rebuild"):
                continue
            state = str(item.get("state", "")).strip().upper()
            if state not in ACTIVE_IN_PROGRESS_STATES:
                continue
            stream_id = str(item.get("id", "")).strip()
            item["state"] = _preferred_ready_state_for_stream(board, stream_id, str(item.get("owner_role") or ""))
            item["stalled_reason"] = "parked_by_rebuild_cannot_stay_in_progress"
            item["reconciled_at"] = now
            item["updated_at"] = now
            report["parked_inprogress_fixed"] = int(report["parked_inprogress_fixed"]) + 1

        # 3) stale in-progress -> downgrade to READY/READY_DEV
        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            state = str(task.get("state", "")).strip().upper()
            if state not in ACTIVE_IN_PROGRESS_STATES:
                continue
            updated_epoch = _parse_iso_epoch(str(task.get("updated_at", "")))
            progress_epoch = (
                _parse_iso_epoch(str(task.get("last_meaningful_progress_at", "")))
                or _parse_iso_epoch(str(task.get("last_progress_at", "")))
                or updated_epoch
            )
            task_id_value = str(task.get("id", "")).strip()
            task_role = _canonical_role(str(task.get("role") or task.get("assignee") or ""))
            blocked_reason = str(task.get("blocked_reason", "") or "").strip()
            if (
                _task_has_delivery_evidence(task)
                and not blocked_reason
                and progress_epoch > 0
                and (now_epoch - progress_epoch) >= proof_transition_stale_seconds
            ):
                task["state"] = "BLOCKED"
                task["blocked_reason"] = "proof_transition_stalled"
                task["stalled_reason"] = f"proof_transition_stalled>{proof_transition_stale_seconds}s"
                task["proof_transition_stalled_at"] = now
                task["reconciled_at"] = now
                task["updated_at"] = now
                report["proof_transition_stalled"] = int(report["proof_transition_stalled"]) + 1
                continue
            if (
                task_role == "dev"
                and updated_epoch > 0
                and (now_epoch - updated_epoch) >= capability_stall_seconds
                and task_id_value not in active_subagent_owner_tasks
                and not _task_has_delivery_evidence(task)
            ):
                task["state"] = _preferred_ready_state_for_role(task_role)
                task["stalled_reason"] = "planner_capability_stall_no_active_subagent"
                task["last_progress_at"] = str(updated_epoch)
                task["reconciled_at"] = now
                task["updated_at"] = now
                report["stale_inprogress_marked"] = int(report["stale_inprogress_marked"]) + 1
                continue
            if updated_epoch <= 0 or (now_epoch - updated_epoch) < config.stale_in_progress_seconds:
                continue
            task["state"] = _preferred_ready_state_for_role(str(task.get("role") or task.get("assignee") or ""))
            task["stalled_reason"] = f"stale_in_progress>{config.stale_in_progress_seconds}s"
            task["last_progress_at"] = str(updated_epoch)
            task["reconciled_at"] = now
            task["updated_at"] = now
            report["stale_inprogress_marked"] = int(report["stale_inprogress_marked"]) + 1

        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            state = str(task.get("state", "")).strip().upper()
            updated_epoch = _parse_iso_epoch(str(task.get("updated_at", ""))) or _parse_iso_epoch(str(task.get("ready_at", "")))
            if state in READY_STATES and updated_epoch > 0 and (now_epoch - updated_epoch) >= config.ready_starvation_seconds:
                if not task.get("ready_starvation"):
                    task["ready_starvation"] = True
                    task["ready_starved_at"] = now
                    task["stalled_reason"] = task.get("stalled_reason") or f"ready_starvation>{config.ready_starvation_seconds}s"
                    task["reconciled_at"] = now
                    report["ready_starvation_detected"] = int(report["ready_starvation_detected"]) + 1
            if state == "WAITING_DEP" and updated_epoch > 0 and (now_epoch - updated_epoch) >= max(config.ready_starvation_seconds * 2, 600):
                if not task.get("dependency_starvation"):
                    task["dependency_starvation"] = True
                    task["dependency_starved_at"] = now
                    task["stalled_reason"] = task.get("stalled_reason") or "dependency_starvation"
                    task["reconciled_at"] = now
                    report["dependency_starvation_detected"] = int(report["dependency_starvation_detected"]) + 1

        for stream in board.get("streams", []):
            if not isinstance(stream, dict):
                continue
            state = str(stream.get("state", "")).strip().upper()
            updated_epoch = _parse_iso_epoch(str(stream.get("updated_at", ""))) or _parse_iso_epoch(str(stream.get("ready_at", "")))
            if state in READY_STATES and updated_epoch > 0 and (now_epoch - updated_epoch) >= config.ready_starvation_seconds:
                if not stream.get("ready_starvation"):
                    stream["ready_starvation"] = True
                    stream["ready_starved_at"] = now
                    stream["stalled_reason"] = stream.get("stalled_reason") or f"ready_starvation>{config.ready_starvation_seconds}s"
                    stream["reconciled_at"] = now

        board_meta = board.get("meta")
        if not isinstance(board_meta, dict):
            board_meta = {}
            board["meta"] = board_meta
        projection_missing = _workboard_projection_missing_fields(board, active_cycle_ids)
        board_meta["decision_capable"] = False if projection_missing > 0 else True
        board_meta["decision_capability_reason"] = "projection_missing_operational_fields" if projection_missing > 0 else "canonical_fields_complete"
        board_meta["decision_capability_checked_at"] = now
        board_meta["decision_capability_missing_fields"] = projection_missing
        queue_meta["workboard_decision_capable"] = False if projection_missing > 0 else True
        queue_meta["workboard_decision_capability_reason"] = "projection_missing_operational_fields" if projection_missing > 0 else "canonical_fields_complete"
        queue_meta["workboard_decision_capability_checked_at"] = now
        if projection_missing > 0:
            report["projection_decision_disabled"] = 1

        _write_json(config.queue_path, queue_obj)
        recompute_states(board)
        queue_sync = reconcile_state(board, config.queue_path)
        save_board(config.board_path, board)
        report["fixes_applied"] = int(report["fixes_applied"]) + int(queue_sync.get("queue_synced", 0))
        if (
            int(report["parked_inprogress_fixed"])
            or int(report["stale_inprogress_marked"])
            or int(report["proof_transition_stalled"])
            or int(report["ready_starvation_detected"])
            or int(report["dependency_starvation_detected"])
            or int(report["completed_state_repaired"])
            or int(report["stagnation_hard_guarded"])
            or int(report["projection_decision_disabled"])
            or int(report["runtime_projection_synced"])
            or int(report["runtime_completion_consumed"])
        ):
            append_event(
                board,
                "state_reconcile",
                {
                    "role": config.role,
                    "parked_inprogress_fixed": str(report["parked_inprogress_fixed"]),
                    "stale_inprogress_marked": str(report["stale_inprogress_marked"]),
                    "proof_transition_stalled": str(report["proof_transition_stalled"]),
                    "ready_starvation_detected": str(report["ready_starvation_detected"]),
                    "dependency_starvation_detected": str(report["dependency_starvation_detected"]),
                    "completed_state_repaired": str(report["completed_state_repaired"]),
                    "stagnation_hard_guarded": str(report["stagnation_hard_guarded"]),
                    "projection_decision_disabled": str(report["projection_decision_disabled"]),
                    "runtime_projection_synced": str(report["runtime_projection_synced"]),
                    "runtime_completion_consumed": str(report["runtime_completion_consumed"]),
                },
            )
            save_board(config.board_path, board)

    # Reload queue after reconcile_state persisted canonical truth.
    queue_obj = _load_json(config.queue_path, {"items": []})
    if not isinstance(queue_obj, dict):
        queue_obj = {"items": []}

    # 3) ready starvation markers
    for item in queue_obj.get("items", []):
        if not isinstance(item, dict):
            continue
        state = str(item.get("state", "")).strip().upper()
        if state not in READY_STATES:
            continue
        updated_epoch = _parse_iso_epoch(str(item.get("updated_at", ""))) or _parse_iso_epoch(str(item.get("ready_at", "")))
        if updated_epoch <= 0 or (now_epoch - updated_epoch) < config.ready_starvation_seconds:
            continue
        if not item.get("ready_starvation"):
            item["ready_starvation"] = True
            item["ready_starved_at"] = now
            item["reconciled_at"] = now
            report["ready_starvation_detected"] = int(report["ready_starvation_detected"]) + 1
    _write_json(config.queue_path, queue_obj)

    # 4) stale runtime blockers
    if probe_runtime_ok():
        for role in CORE_ROLES:
            contract_path = config.state_dir / f"{role}.last_contract"
            if _clear_runtime_blocker_in_contract(contract_path, role, now):
                report["runtime_blockers_cleared"] = int(report["runtime_blockers_cleared"]) + 1

    # 5) stale lock cleanup
    if config.lock_dir.exists():
        for lock_path in config.lock_dir.glob("*.lock"):
            meta_path = Path(str(lock_path) + ".meta")
            pid_raw = _extract_meta_field(meta_path, "pid")
            start_raw = _extract_meta_field(meta_path, "start_epoch")
            pid = int(pid_raw) if pid_raw.isdigit() else 0
            start_epoch = int(start_raw) if start_raw.isdigit() else 0
            age = now_epoch - start_epoch if start_epoch > 0 else config.stale_lock_seconds + 1
            if pid and _pid_alive(pid):
                continue
            if age < config.stale_lock_seconds:
                continue
            try:
                lock_path.unlink(missing_ok=True)
            except TypeError:
                if lock_path.exists():
                    lock_path.unlink()
            except Exception:
                pass
            try:
                meta_path.unlink(missing_ok=True)
            except TypeError:
                if meta_path.exists():
                    meta_path.unlink()
            except Exception:
                pass
            report["stale_locks_removed"] = int(report["stale_locks_removed"]) + 1

    report["fixes_applied"] = (
        int(report["parked_inprogress_fixed"])
        + int(report["runtime_blockers_cleared"])
        + int(report["stale_locks_removed"])
        + int(report["stale_inprogress_marked"])
        + int(report["proof_transition_stalled"])
        + int(report["ready_starvation_detected"])
        + int(report["dependency_starvation_detected"])
        + int(report["completed_state_repaired"])
        + int(report["stagnation_hard_guarded"])
        + int(report["projection_decision_disabled"])
        + int(report["runtime_projection_synced"])
        + int(report["runtime_completion_consumed"])
    )
    _write_json(config.report_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pre-tick runtime truth reconciler")
    parser.add_argument("--role", default="system")
    parser.add_argument("--root", default=str(Path.cwd()))
    parser.add_argument("--queue", default="logs-codex-runs/orchestrator-state/priority-queue.json")
    parser.add_argument("--board", default="logs-codex-runs/orchestrator-state/parallel-workstreams.json")
    parser.add_argument("--state-dir", default=str(Path.home() / ".openclaw" / "cron" / "role-state"))
    parser.add_argument("--report", default="logs-codex-runs/orchestrator-state/state-reconcile-report.json")
    parser.add_argument("--lock-dir", default="/tmp/fc-agent-locks")
    parser.add_argument("--stale-lock-seconds", type=int, default=int(os.environ.get("FC_RECONCILE_STALE_LOCK_SECONDS", "1800")))
    parser.add_argument("--stale-in-progress-seconds", type=int, default=int(os.environ.get("FC_RECONCILE_STALE_IN_PROGRESS_SECONDS", "14400")))
    parser.add_argument("--ready-starvation-seconds", type=int, default=int(os.environ.get("FC_RECONCILE_READY_STARVATION_SECONDS", "1800")))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    config = ReconcileConfig(
        root=root,
        role=_canonical_role(args.role),
        queue_path=(root / args.queue).resolve() if not str(args.queue).startswith("/") else Path(args.queue).resolve(),
        board_path=(root / args.board).resolve() if not str(args.board).startswith("/") else Path(args.board).resolve(),
        state_dir=Path(args.state_dir).expanduser().resolve(),
        report_path=(root / args.report).resolve() if not str(args.report).startswith("/") else Path(args.report).resolve(),
        lock_dir=Path(args.lock_dir).expanduser().resolve(),
        stale_lock_seconds=max(60, int(args.stale_lock_seconds)),
        stale_in_progress_seconds=max(300, int(args.stale_in_progress_seconds)),
        ready_starvation_seconds=max(300, int(args.ready_starvation_seconds)),
    )
    report = run_reconciler(config)
    print(json.dumps(report, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
