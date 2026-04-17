from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable
import urllib.error
import urllib.request

from orchestrator_paths import (
    CANONICAL_VM_ROOT,
    SHARED_VM_ROOT,
    read_json_file,
    resolve_orchestrator_read_path,
    resolve_orchestrator_write_path,
    write_orchestrator_json,
)

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
MERGE_RESIDUE_STATUSES = {"ready_to_merge"}
INVALID_RESULT_MARKERS = ("invalid_subagent_result", "start_banner_only")
DELIVERY_ACTIVE_STATUSES = {"running", "pending", "review", "in_progress", "blocked", "ready_to_merge", "retryable"}
DELIVERY_ACTIVE_OWNER_STATES = {"in_progress", "ready", "ready_planner", "ready_dev", "review", "blocked", "waiting_dep"}
DELIVERY_TERMINAL_STATUSES = {"merged", "done", "closed", "completed", "pass", "success", "ok", "cancelled", "canceled", "quarantined"}
PUBLIC_PROOF_OK_MARKERS = (
    "http://3.98.20.77",
    "ec2-3-98-20-77",
    "public ec2",
    "public-status",
    "product_runtime=ok",
    "public api healthy",
    "monitor reports health=ok",
    "monitor health=ok",
    "api_health_ok",
)
PUBLIC_PROOF_ERROR_MARKERS = (
    "502 bad gateway",
    "bad gateway",
    "status=502",
    "returned 502",
    "public api unhealthy",
    "connection refused",
    "timed out",
    "timeout",
)
PRODUCT_DELIVERY_STATE_FILE = "product_delivery_state.json"


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
    normalized = token_lower.rstrip(" .!?:;")
    if normalized in {"none", "n/a", "na", "null", "unknown", "not yet", "pending"}:
        return False
    if normalized.startswith("skip("):
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
        "proof_manifest": _proof_field(result.get("proof_manifest", ""), proof.get("proof_manifest", "")),
        "engine": str(item.get("engine", "")).strip(),
        "summary": _proof_field(result.get("summary", ""), proof.get("summary", "")),
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


def _load_projection_payload(root: Path, filename: str) -> dict[str, Any]:
    path = resolve_orchestrator_read_path(root, filename)
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _default_public_app_base_url() -> str:
    return (
        str(os.environ.get("FC_PUBLIC_APP_BASE_URL") or os.environ.get("FC_API_BASE_URL") or "http://3.98.20.77").strip()
        or "http://3.98.20.77"
    )


def _probe_http_ok(url: str, timeout_s: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json,text/html"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            return 200 <= status < 300
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False
    except Exception:
        return False


def _is_vm_runtime_root(root: Path) -> bool:
    candidate = Path(root).expanduser()
    try:
        candidate = candidate.resolve()
    except Exception:
        pass
    candidate_token = str(candidate)
    for base in (CANONICAL_VM_ROOT, SHARED_VM_ROOT):
        base_token = str(base)
        if candidate_token == base_token or candidate_token.startswith(f"{base_token}/"):
            return True
    return False


def _persist_delivery_state_enabled(root: Path, override: bool | None) -> bool:
    if override is not None:
        return bool(override)
    token = str(os.environ.get("FC_PERSIST_PRODUCT_DELIVERY_STATE", "") or "").strip().lower()
    if token:
        return token not in {"0", "false", "no", "off"}
    return _is_vm_runtime_root(root)


def product_delivery_state_path(root: Path) -> Path:
    return resolve_orchestrator_write_path(root, PRODUCT_DELIVERY_STATE_FILE, create_parent=False)


def load_product_delivery_state(root: Path) -> dict[str, Any]:
    path = resolve_orchestrator_read_path(root, PRODUCT_DELIVERY_STATE_FILE)
    payload = read_json_file(path)
    return payload if isinstance(payload, dict) else {}


def persist_product_delivery_state(root: Path, payload: dict[str, Any]) -> Path:
    delivery_state = dict(payload) if isinstance(payload, dict) else {}
    delivery_state.setdefault("schema_version", "product_delivery_state.v1")
    return write_orchestrator_json(root, PRODUCT_DELIVERY_STATE_FILE, delivery_state, mirror_docs=False)


def _active_cycle_batch_ids(queue_payload: dict[str, Any], workboard_payload: dict[str, Any]) -> set[str]:
    ordered: list[str] = []
    for payload in (queue_payload, workboard_payload):
        active_cycle = payload.get("active_cycle")
        if not isinstance(active_cycle, dict):
            continue
        raw_ids = active_cycle.get("active_batch_ids")
        if not isinstance(raw_ids, list):
            continue
        for raw in raw_ids:
            token = str(raw or "").strip().upper()
            if token and token not in ordered:
                ordered.append(token)
    if ordered:
        return set(ordered)

    queue_items = queue_payload.get("items", []) if isinstance(queue_payload, dict) else []
    if isinstance(queue_items, list):
        for row in queue_items:
            if not isinstance(row, dict):
                continue
            state = str(row.get("state", "") or row.get("status", "")).strip().upper()
            if state in {"DONE", "CLOSED", "CANCELLED"}:
                continue
            token = _task_batch_id(row)
            if token and token not in ordered:
                ordered.append(token)

    workboard_tasks = workboard_payload.get("tasks", []) if isinstance(workboard_payload, dict) else []
    if isinstance(workboard_tasks, list):
        for row in workboard_tasks:
            if not isinstance(row, dict):
                continue
            state = str(row.get("state", "") or row.get("status", "")).strip().upper()
            if state in {"DONE", "CLOSED", "CANCELLED"}:
                continue
            token = _task_batch_id(row)
            if token and token not in ordered:
                ordered.append(token)
    return set(ordered)


def _active_cycle_batch_id_list(queue_payload: dict[str, Any], workboard_payload: dict[str, Any]) -> list[str]:
    ordered: list[str] = []
    for payload in (queue_payload, workboard_payload):
        active_cycle = payload.get("active_cycle")
        if not isinstance(active_cycle, dict):
            continue
        raw_ids = active_cycle.get("active_batch_ids")
        if not isinstance(raw_ids, list):
            continue
        for raw in raw_ids:
            token = str(raw or "").strip().upper()
            if token and token not in ordered:
                ordered.append(token)
    return ordered


def _task_batch_id(task: dict[str, Any] | None) -> str:
    if not isinstance(task, dict):
        return ""
    for key in ("stream_id", "batch_id"):
        token = str(task.get(key, "") or "").strip().upper()
        if token:
            return token
    task_id = str(task.get("id", "") or task.get("task_id", "")).strip().upper()
    if task_id.startswith("BATCH-"):
        parts = task_id.split("-")
        if len(parts) >= 2:
            return "-".join(parts[:2])
    return ""


def _state_batch_id(item: dict[str, Any], task_index: dict[str, dict[str, Any]]) -> str:
    batch_id = str(item.get("batch_id", "") or "").strip().upper()
    if batch_id:
        return batch_id
    task_id = str(item.get("task_id", "") or "").strip()
    if task_id:
        owner_task = task_index.get(task_id)
        batch_id = _task_batch_id(owner_task)
        if batch_id:
            return batch_id
    return ""


def _state_matches_active_cycle(
    item: dict[str, Any],
    active_cycle_batch_ids: set[str],
    task_index: dict[str, dict[str, Any]],
) -> bool:
    if not active_cycle_batch_ids:
        return False
    batch_id = _state_batch_id(item, task_index)
    return bool(batch_id) and batch_id in active_cycle_batch_ids


def _event_matches_active_cycle(
    event: dict[str, Any],
    active_cycle_batch_ids: set[str],
    task_index: dict[str, dict[str, Any]],
) -> bool:
    if not active_cycle_batch_ids:
        return False
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    batch_id = str(event.get("batch_id", "") or payload.get("batch_id", "")).strip().upper()
    if not batch_id:
        task_id = str(event.get("task_id", "") or payload.get("task_id", "")).strip()
        if task_id:
            batch_id = _task_batch_id(task_index.get(task_id))
    return bool(batch_id) and batch_id in active_cycle_batch_ids


def _task_operational_state(task: dict[str, Any]) -> str:
    status = str(task.get("status", "") or "").strip().lower()
    state = str(task.get("state", "") or "").strip().lower()
    if status in READY_OWNER_TASK_STATES:
        return status
    return state or status


def _proof_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key, "") or "")
        for key in ("artifact", "verify", "tests_run", "summary", "blocking_issue")
        if str(item.get(key, "") or "").strip()
    ).strip().lower()


def _state_has_public_proof_ok(item: dict[str, Any]) -> bool:
    blob = _proof_text(item)
    if not blob:
        return False
    if any(marker in blob for marker in PUBLIC_PROOF_ERROR_MARKERS):
        return False
    return any(marker in blob for marker in PUBLIC_PROOF_OK_MARKERS)


def _state_has_public_proof_error(item: dict[str, Any]) -> bool:
    blob = _proof_text(item)
    if not blob:
        return False
    return any(marker in blob for marker in PUBLIC_PROOF_ERROR_MARKERS)


def _state_timestamp_text(item: dict[str, Any]) -> str | None:
    for key in ("updated_at", "ts", "finished_at", "created_at"):
        token = str(item.get(key, "") or "").strip()
        if token:
            return token
    return None


def _state_is_completion_candidate(item: dict[str, Any]) -> bool:
    batch_id = str(item.get("batch_id", "") or "").strip().upper()
    if not batch_id:
        return False
    status = str(item.get("status", "")).strip().lower()
    return _state_has_public_proof_ok(item) or status in DELIVERY_TERMINAL_STATUSES


def _state_proof_ref(item: dict[str, Any]) -> str | None:
    token = _proof_field(
        item.get("proof_manifest", ""),
        item.get("artifact", ""),
        item.get("verify", ""),
        item.get("tests_run", ""),
    )
    return None if token == "none" else token


def _latest_matching_state(
    states: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> dict[str, Any] | None:
    for item in states:
        if predicate(item):
            return item
    return None


def _truthy_flag(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return token in {"1", "true", "yes", "on", "ok"}


def _contract_value_present(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contract_value_present(item) for item in value.values())
    if isinstance(value, list):
        return any(_contract_value_present(item) for item in value)
    return _truth_value_present(value)


def _batch_delivery_contract(
    batch_meta: dict[str, Any],
    active_cycle_meta: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    contract = {
        "value_target": (
            batch_meta.get("value_target")
            or batch_meta.get("novelty_target")
            or active_cycle_meta.get("value_target")
            or active_cycle_meta.get("novelty_target")
        ),
        "user_visible_delta": (
            batch_meta.get("user_visible_delta")
            or batch_meta.get("user_value_delta")
            or active_cycle_meta.get("user_visible_delta")
            or active_cycle_meta.get("user_value_delta")
        ),
        "api_proof": batch_meta.get("api_proof") or active_cycle_meta.get("api_proof"),
        "ui_proof": batch_meta.get("ui_proof") or active_cycle_meta.get("ui_proof"),
        "done_when": batch_meta.get("done_when") or active_cycle_meta.get("done_when"),
    }
    missing = [field for field, value in contract.items() if not _contract_value_present(value)]
    return contract, missing


def _batch_projection_index(queue_payload: dict[str, Any], workboard_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for payload, key in ((queue_payload, "items"), (workboard_payload, "streams")):
        rows = payload.get(key, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            batch_id = _task_batch_id(row)
            if not batch_id:
                continue
            current = index.setdefault(batch_id, {})
            for field, value in row.items():
                if value in (None, "", [], {}):
                    continue
                current[field] = value
    return index


def _load_public_proof_artifact(root: Path, batch_id: str) -> dict[str, Any]:
    token = str(batch_id or "").strip().upper()
    if not token:
        return {}
    path = resolve_orchestrator_read_path(root, f"public-proof/{token}.json")
    payload = read_json_file(path)
    return payload if isinstance(payload, dict) else {}


def _proof_artifact_to_state(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {
        "batch_id": str(payload.get("batch_id", "") or "").strip().upper(),
        "updated_at": str(payload.get("timestamp", "") or payload.get("generated_at", "")).strip(),
        "artifact": str(payload.get("proof_ref", "") or "").strip(),
        "proof_manifest": str(payload.get("proof_ref", "") or "").strip(),
        "verify": "public_proof_runner",
        "tests_run": str(payload.get("api_smoke_status", "") or "").strip(),
        "summary": f"public proof runner status={str(payload.get('status', '')).strip().lower() or 'unknown'}",
        "status": str(payload.get("status", "")).strip().lower() or "unknown",
    }


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
    done_owner_state = task_state in {"done", "closed"}
    if status in MERGE_RESIDUE_STATUSES:
        if not done_owner_state or not _task_has_delivery_evidence(item):
            return None
    elif status not in RETRYABLE_RESIDUE_STATUSES:
        return None

    issue_bits = " | ".join(
        [
            str(item.get("blocking_issue", "")),
            str(item.get("next_action", "")),
        ]
    ).strip().lower()
    if status not in MERGE_RESIDUE_STATUSES and not done_owner_state and not any(marker in issue_bits for marker in INVALID_RESULT_MARKERS):
        return None
    if status not in MERGE_RESIDUE_STATUSES and _task_has_delivery_evidence(item):
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


def _latest_meaningful_delta_at(
    states: list[dict[str, Any]],
    queue_payload: dict[str, Any],
    workboard_payload: dict[str, Any],
    *,
    batch_id: str | None = None,
) -> str | None:
    scoped_batch_id = str(batch_id or "").strip().upper()
    candidates: list[datetime] = []
    for item in states:
        item_batch_id = str(item.get("batch_id", "") or "").strip().upper()
        if scoped_batch_id and item_batch_id != scoped_batch_id:
            continue
        status = str(item.get("status", "")).strip().lower()
        if status in {"ready_to_merge", "done", "closed"} or _task_has_delivery_evidence(item):
            dt = _parse_iso(item.get("updated_at"))
            if dt is not None:
                candidates.append(dt)

    for payload, key in ((queue_payload, "items"), (workboard_payload, "tasks")):
        rows = payload.get(key, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            if scoped_batch_id and _task_batch_id(row) != scoped_batch_id:
                continue
            state = _task_operational_state(row)
            if state not in {"done", "closed"}:
                continue
            dt = (
                _parse_iso(row.get("updated_at"))
                or _parse_iso(row.get("finished_at"))
                or _parse_iso(row.get("completed_at"))
                or _parse_iso(row.get("closed_at"))
            )
            if dt is not None:
                candidates.append(dt)

    if not candidates:
        return None
    return max(candidates).isoformat().replace("+00:00", "Z")


def _build_product_delivery_state(
    *,
    root: Path,
    all_states: list[dict[str, Any]],
    normalized_states: list[dict[str, Any]],
    queue_payload: dict[str, Any],
    workboard_payload: dict[str, Any],
    active_cycle_batch_ids: set[str],
    ignored_historical_states: list[dict[str, Any]],
    quarantined_retryable_residue: list[dict[str, Any]],
    ec2_reachable: bool | None,
    public_probe_status: str,
    maintenance_active: bool,
    maintenance_details: dict[str, Any] | None,
    event_store_primary: bool,
    prior_state: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    previous_state = dict(prior_state) if isinstance(prior_state, dict) else {}
    batch_index = _batch_projection_index(queue_payload, workboard_payload)
    active_batch_ids_ordered = _active_cycle_batch_id_list(queue_payload, workboard_payload)
    active_cycle_meta = {}
    for payload in (queue_payload, workboard_payload):
        candidate = payload.get("active_cycle")
        if isinstance(candidate, dict):
            active_cycle_meta = candidate
            break
    projection_active_batch_id = active_batch_ids_ordered[0] if active_batch_ids_ordered else (
        sorted(active_cycle_batch_ids)[0] if active_cycle_batch_ids else ""
    )

    active_batch_id = ""
    for item in normalized_states:
        batch_id = str(item.get("batch_id", "") or "").strip().upper()
        status = str(item.get("status", "")).strip().lower()
        if batch_id and status in DELIVERY_ACTIVE_STATUSES:
            active_batch_id = batch_id
            break
    if not active_batch_id and not event_store_primary:
        active_batch_id = projection_active_batch_id

    if maintenance_active:
        effective_public_status = "degraded"
    elif ec2_reachable is True:
        effective_public_status = "ok"
    elif ec2_reachable is False:
        effective_public_status = "error"
    else:
        effective_public_status = public_probe_status if public_probe_status in {"ok", "degraded", "error"} else "unknown"

    recent_completed_batch_ids: list[str] = []
    for payload in (queue_payload, workboard_payload):
        active_cycle = payload.get("active_cycle")
        if not isinstance(active_cycle, dict):
            continue
        raw_ids = active_cycle.get("recent_completed_batch_ids")
        if not isinstance(raw_ids, list):
            continue
        for raw in raw_ids:
            token = str(raw or "").strip().upper()
            if token and token not in recent_completed_batch_ids:
                recent_completed_batch_ids.append(token)

    overall_meaningful_delta_at = _latest_meaningful_delta_at(all_states, queue_payload, workboard_payload)
    latest_meaningful_delta_at = (
        _latest_meaningful_delta_at(
            all_states,
            queue_payload,
            workboard_payload,
            batch_id=active_batch_id,
        )
        if active_batch_id
        else overall_meaningful_delta_at
    )

    public_proof_ok_state = _latest_matching_state(all_states, _state_has_public_proof_ok)
    public_proof_error_state = _latest_matching_state(all_states, _state_has_public_proof_error)
    active_public_proof_ok_state = None
    active_public_proof_error_state = None
    if active_batch_id:
        active_public_proof_ok_state = _latest_matching_state(
            all_states,
            lambda item, batch_id=active_batch_id: str(item.get("batch_id", "") or "").strip().upper() == batch_id
            and _state_has_public_proof_ok(item),
        )
        active_public_proof_error_state = _latest_matching_state(
            all_states,
            lambda item, batch_id=active_batch_id: str(item.get("batch_id", "") or "").strip().upper() == batch_id
            and _state_has_public_proof_error(item),
        )
        active_proof_artifact = _load_public_proof_artifact(root, active_batch_id)
        active_proof_artifact_state = _proof_artifact_to_state(active_proof_artifact)
        if str(active_proof_artifact.get("status", "")).strip().lower() == "ok" and active_proof_artifact_state:
            active_public_proof_ok_state = active_proof_artifact_state
        elif str(active_proof_artifact.get("status", "")).strip().lower() == "error" and active_proof_artifact_state:
            active_public_proof_error_state = active_proof_artifact_state

    last_completed_state = _latest_matching_state(all_states, _state_is_completion_candidate)
    prior_last_completed_batch_id = str(previous_state.get("last_completed_batch_id") or "").strip().upper() or None
    prior_last_closed_at = str(previous_state.get("last_closed_at") or "").strip() or None
    prior_last_completion_proof_ref = str(previous_state.get("last_completion_proof_ref") or "").strip() or None
    prior_close_reason = str(previous_state.get("close_reason") or "").strip() or "none"
    last_completed_batch_id = str(
        (last_completed_state or {}).get("batch_id")
        or (recent_completed_batch_ids[0] if recent_completed_batch_ids else "")
        or (prior_last_completed_batch_id or "")
    ).strip().upper() or None
    last_completed_public_proof_state = None
    if last_completed_batch_id:
        last_completed_public_proof_state = _latest_matching_state(
            all_states,
            lambda item, batch_id=last_completed_batch_id: str(item.get("batch_id", "") or "").strip().upper() == batch_id
            and _state_has_public_proof_ok(item),
        )
        last_completed_proof_artifact = _load_public_proof_artifact(root, last_completed_batch_id)
        last_completed_proof_artifact_state = _proof_artifact_to_state(last_completed_proof_artifact)
        if str(last_completed_proof_artifact.get("status", "")).strip().lower() == "ok" and last_completed_proof_artifact_state:
            last_completed_public_proof_state = last_completed_proof_artifact_state

    current_public_proof_ok_state = (
        active_public_proof_ok_state
        if active_batch_id
        else (last_completed_public_proof_state or public_proof_ok_state)
    )
    current_public_proof_error_state = (
        active_public_proof_error_state if active_batch_id else public_proof_error_state
    )

    if effective_public_status == "unknown" and current_public_proof_ok_state is not None:
        effective_public_status = "ok"
    elif effective_public_status == "unknown" and current_public_proof_error_state is not None:
        effective_public_status = "error"
    elif effective_public_status == "unknown" and active_batch_id and latest_meaningful_delta_at:
        effective_public_status = "degraded"

    proof_batch_id = str(
        (current_public_proof_ok_state or {}).get("batch_id")
        or active_batch_id
        or (last_completed_batch_id or "")
    ).strip().upper()
    batch_meta = batch_index.get(proof_batch_id, {}) if proof_batch_id else {}
    visible_delta_hint = batch_meta.get("user_value_delta_visible")
    user_visible_delta_confirmed = bool(current_public_proof_ok_state) and (
        visible_delta_hint is None or _truthy_flag(visible_delta_hint) or bool(visible_delta_hint)
    )

    raw_product_done = bool(
        current_public_proof_ok_state is not None
        and effective_public_status == "ok"
        and user_visible_delta_confirmed
    )
    active_batch_contract, active_batch_contract_missing = _batch_delivery_contract(
        batch_index.get(active_batch_id, {}) if active_batch_id else {},
        active_cycle_meta,
    )
    active_batch_contract_complete = not active_batch_contract_missing
    runtime_active_batches = {
        str(item.get("batch_id", "") or "").strip().upper()
        for item in normalized_states
        if str(item.get("status", "")).strip().lower() in DELIVERY_ACTIVE_STATUSES
        and str(item.get("batch_id", "") or "").strip()
    }
    runtime_terminal_residue_only = bool(normalized_states) and not runtime_active_batches and all(
        str(item.get("status", "")).strip().lower() in DELIVERY_TERMINAL_STATUSES
        for item in normalized_states
    )
    preclose_active_batch_id = active_batch_id
    if event_store_primary and raw_product_done:
        active_batch_id = ""
    if event_store_primary and not runtime_active_batches and (
        runtime_terminal_residue_only
        or raw_product_done
        or (
            projection_active_batch_id
            and not normalized_states
        )
    ):
        active_batch_id = ""

    completion_batch_id = ""
    completion_from_active_batch = False
    if raw_product_done:
        completion_batch_id = preclose_active_batch_id or proof_batch_id or last_completed_batch_id or ""
        completion_from_active_batch = bool(preclose_active_batch_id)
    elif not active_batch_id and last_completed_batch_id and current_public_proof_ok_state is not None:
        completion_batch_id = last_completed_batch_id

    canonical_active_batch_id = ""
    if active_batch_id and not completion_batch_id:
        canonical_active_batch_id = active_batch_id

    ops_clean = (
        len(quarantined_retryable_residue) == 0
        and len(ignored_historical_states) == 0
        and len(normalized_states) == 0
        and not canonical_active_batch_id
    )

    if effective_public_status == "error" and not maintenance_active:
        phase = "external_outage"
        freeze_reason = "external_outage"
        next_batch_eligible = False
    elif completion_batch_id:
        phase = "product_done_ops_dirty" if completion_from_active_batch and not ops_clean else "idle_ready_for_next_batch"
        freeze_reason = "none"
        next_batch_eligible = True
    elif canonical_active_batch_id:
        if latest_meaningful_delta_at and not active_batch_contract_complete:
            phase = "active_delivery"
            freeze_reason = "missing_batch_contract"
            next_batch_eligible = False
        elif latest_meaningful_delta_at:
            phase = "verifying_public_proof"
            freeze_reason = "waiting_public_proof"
            next_batch_eligible = False
        else:
            phase = "active_delivery"
            freeze_reason = "none"
            next_batch_eligible = False
    else:
        phase = "idle_ready_for_next_batch"
        freeze_reason = "none"
        next_batch_eligible = bool(effective_public_status != "error")

    current_value_batch_id = canonical_active_batch_id or projection_active_batch_id or last_completed_batch_id or proof_batch_id
    current_value_meta = batch_index.get(current_value_batch_id, {}) if current_value_batch_id else {}
    current_novelty_target = str(
        current_value_meta.get("novelty_target")
        or active_cycle_meta.get("novelty_target")
        or ""
    ).strip() or None
    current_user_visible_delta = str(
        current_value_meta.get("user_visible_delta")
        or current_value_meta.get("user_value_delta")
        or active_cycle_meta.get("user_visible_delta")
        or active_cycle_meta.get("user_value_delta")
        or ""
    ).strip() or None
    current_public_proof_state = (
        active_public_proof_ok_state
        or active_public_proof_error_state
        or (last_completed_public_proof_state if not canonical_active_batch_id else None)
        or (last_completed_state if not canonical_active_batch_id else None)
        or {}
    )
    if current_public_proof_ok_state is not None:
        current_public_proof_state = current_public_proof_ok_state
    elif current_public_proof_error_state is not None:
        current_public_proof_state = current_public_proof_error_state

    current_public_proof_status = "none"
    if current_public_proof_ok_state is not None:
        current_public_proof_status = "ok"
    elif current_public_proof_error_state is not None:
        current_public_proof_status = "error"
    elif canonical_active_batch_id and latest_meaningful_delta_at:
        current_public_proof_status = "pending"

    last_public_proof_ok_at = _state_timestamp_text(current_public_proof_ok_state or {})
    last_completion_proof_ref = prior_last_completion_proof_ref
    last_closed_at = prior_last_closed_at
    close_reason = prior_close_reason
    if completion_batch_id:
        last_completed_batch_id = completion_batch_id
        last_completion_proof_ref = (
            _state_proof_ref(current_public_proof_state)
            or _state_proof_ref(last_completed_state or {})
            or prior_last_completion_proof_ref
        )
        last_closed_at = (
            _state_timestamp_text(current_public_proof_state)
            or _state_timestamp_text(last_completed_state or {})
            or overall_meaningful_delta_at
            or now.isoformat().replace("+00:00", "Z")
        )
        close_reason = "public_proof_ok"
    elif last_completed_batch_id and last_completed_state is not None:
        last_completion_proof_ref = _state_proof_ref(last_completed_state) or prior_last_completion_proof_ref
        last_closed_at = _state_timestamp_text(last_completed_state) or overall_meaningful_delta_at or prior_last_closed_at
        if _state_has_public_proof_ok(last_completed_state):
            close_reason = "public_proof_ok"
        else:
            status = str(last_completed_state.get("status", "") or "").strip().lower() or "unknown"
            close_reason = f"terminal_state:{status}"
    elif last_completed_batch_id and close_reason == "none":
        close_reason = "recent_completed_projection"

    product_done = bool(completion_batch_id or (not canonical_active_batch_id and last_completed_batch_id))
    advisory_mismatch: list[str] = []
    if event_store_primary and projection_active_batch_id and not canonical_active_batch_id:
        advisory_mismatch.append("active_cycle_projection_without_canonical_active_batch")
    projection_open = any(
        _task_operational_state(row) in DELIVERY_ACTIVE_OWNER_STATES
        for payload in (queue_payload, workboard_payload)
        for key in (("items",) if payload is queue_payload else ("tasks",))
        for row in payload.get(key[0], [])
        if isinstance(row, dict)
    )
    if not canonical_active_batch_id and projection_open:
        advisory_mismatch.append("projection_non_terminal_without_canonical_active_batch")
    if quarantined_retryable_residue:
        advisory_mismatch.append("historical_runtime_residue_quarantined")
    if canonical_active_batch_id and not normalized_states:
        advisory_mismatch.append("active_cycle_projection_without_runtime_state")

    return {
        "schema_version": "product_delivery_state.v1",
        "active_batch_id": canonical_active_batch_id or None,
        "phase": phase,
        "product_done": bool(product_done),
        "ops_clean": bool(ops_clean),
        "public_proof_status": effective_public_status,
        "user_visible_delta_confirmed": bool(user_visible_delta_confirmed),
        "next_batch_eligible": bool(next_batch_eligible),
        "ec2_reachable": bool(ec2_reachable or maintenance_active)
        if ec2_reachable is not None or maintenance_active
        else bool(effective_public_status == "ok"),
        "freeze_reason": freeze_reason,
        "current_public_proof": {
            "batch_id": str(current_public_proof_state.get("batch_id", "") or "").strip().upper() or None,
            "status": current_public_proof_status,
            "updated_at": str(current_public_proof_state.get("updated_at", "") or "").strip() or None,
            "artifact": str(current_public_proof_state.get("artifact", "") or "").strip() or None,
            "verify": str(current_public_proof_state.get("verify", "") or "").strip() or None,
            "proof_ref": (
                str(current_public_proof_state.get("proof_manifest", "") or "").strip()
                or str(current_public_proof_state.get("artifact", "") or "").strip()
                or str(current_public_proof_state.get("verify", "") or "").strip()
                or None
            ),
        },
        "current_value_target": {
            "batch_id": current_value_batch_id or None,
            "novelty_target": current_novelty_target,
            "user_visible_delta": current_user_visible_delta,
        },
        "maintenance_active": bool(maintenance_active),
        "maintenance_reason": str((maintenance_details or {}).get("maintenance_reason") or "none").strip() or "none",
        "maintenance_command": str((maintenance_details or {}).get("maintenance_command") or "").strip(),
        "maintenance_age_s": (maintenance_details or {}).get("maintenance_age_s"),
        "maintenance_source": str((maintenance_details or {}).get("maintenance_source") or "none").strip() or "none",
        "last_meaningful_delta_at": latest_meaningful_delta_at,
        "last_public_proof_ok_at": last_public_proof_ok_at,
        "last_completed_batch_id": last_completed_batch_id,
        "last_closed_at": last_closed_at,
        "last_completion_proof_ref": last_completion_proof_ref,
        "close_reason": close_reason,
        "advisory_mismatch": advisory_mismatch,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
    }


def build_runtime_truth_snapshot(
    root: Path,
    *,
    state_limit: int = 12,
    event_limit: int = 50,
    ec2_reachable: bool | None = None,
    public_probe_status: str | None = None,
    maintenance_active: bool = False,
    maintenance_details: dict[str, Any] | None = None,
    public_probe_fn: Callable[[str], bool] | None = None,
    persist_delivery_state: bool | None = None,
) -> dict[str, Any]:
    root = Path(root)
    prior_delivery_state = load_product_delivery_state(root)
    sqlite_path = event_store_path(root)
    queue_payload = _load_projection_payload(root, "priority-queue.json")
    workboard_payload = _load_projection_payload(root, "parallel-workstreams.json")
    graph_states = latest_graph_states(root, limit=max(50, state_limit * 4))
    workboard_task_index = _load_workboard_task_index(root)
    active_cycle_batch_ids = _active_cycle_batch_ids(queue_payload, workboard_payload)
    all_states = [_normalize_state(row) for row in graph_states if isinstance(row, dict)]
    all_states.sort(key=_sort_ts, reverse=True)
    quarantined_retryable_residue: list[dict[str, Any]] = []
    normalized_states: list[dict[str, Any]] = []
    ignored_historical_states: list[dict[str, Any]] = []
    for item in all_states:
        quarantined = _quarantine_retryable_residue(item, workboard_task_index)
        in_active_cycle = _state_matches_active_cycle(item, active_cycle_batch_ids, workboard_task_index)
        if quarantined is not None:
            quarantined_retryable_residue.append(quarantined)
        elif in_active_cycle:
            normalized_states.append(item)
        else:
            ignored_historical_states.append(item)
    shown_states = normalized_states[: max(1, state_limit)]

    state_counts = Counter(str(row.get("status", "")).strip().lower() or "unknown" for row in normalized_states)
    all_recent_event_rows = [row for row in recent_events(root, hours=6, limit=max(20, event_limit)) if isinstance(row, dict)]
    recent_event_rows = [
        row
        for row in all_recent_event_rows
        if _event_matches_active_cycle(row, active_cycle_batch_ids, workboard_task_index)
    ]
    recent_event_rows.sort(key=_sort_ts, reverse=True)
    recent_event_types = Counter(str(row.get("event_type", "")).strip() or "unknown" for row in recent_event_rows)

    queue_projection = resolve_orchestrator_read_path(root, "priority-queue.json")
    workboard_projection = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
    event_store_primary = sqlite_path.exists() and bool(all_states or all_recent_event_rows)
    runtime_truth_source = "sqlite" if event_store_primary else "fallback"
    legacy_bridges = _legacy_bridge_snapshot(root, hide_paths=event_store_primary)
    if event_store_primary:
        agentic_runtime_status = "ok"
    elif sqlite_path.exists():
        agentic_runtime_status = "degraded"
    else:
        agentic_runtime_status = "unknown"

    probe_status = str(public_probe_status or "").strip().lower()
    if probe_status not in {"ok", "degraded", "error", "unknown"}:
        probe_status = "unknown"
    if ec2_reachable is None and probe_status == "unknown" and public_probe_fn is not None:
        public_base_url = _default_public_app_base_url().rstrip("/")
        probe = public_probe_fn or _probe_http_ok
        probe_status = "ok" if probe(f"{public_base_url}/api/health") else "error"
    delivery_state = _build_product_delivery_state(
        root=root,
        all_states=all_states,
        normalized_states=normalized_states,
        queue_payload=queue_payload,
        workboard_payload=workboard_payload,
        active_cycle_batch_ids=active_cycle_batch_ids,
        ignored_historical_states=ignored_historical_states,
        quarantined_retryable_residue=quarantined_retryable_residue,
        ec2_reachable=ec2_reachable,
        public_probe_status=probe_status,
        maintenance_active=bool(maintenance_active),
        maintenance_details=maintenance_details if isinstance(maintenance_details, dict) else {},
        event_store_primary=bool(event_store_primary),
        prior_state=prior_delivery_state,
        now=datetime.now(timezone.utc),
    )
    delivery_state_file = product_delivery_state_path(root)
    if _persist_delivery_state_enabled(root, persist_delivery_state):
        persist_product_delivery_state(root, delivery_state)

    return {
        "event_store_primary": bool(event_store_primary),
        "runtime_truth_source": runtime_truth_source,
        "source": "event_store" if event_store_primary else "projection_fallback",
        "projection_secondary_only": not bool(event_store_primary),
        "legacy_registry_secondary_only": True,
        "sqlite_path": str(sqlite_path),
        "graph_state_count": len(normalized_states),
        "graph_state_count_total": len(all_states),
        "ignored_historical_state_count": len(ignored_historical_states),
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
        "product_delivery_state": delivery_state,
        "product_delivery_state_path": str(delivery_state_file),
        "projection_paths": {
            "queue": str(queue_projection),
            "workboard": str(workboard_projection),
        },
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
