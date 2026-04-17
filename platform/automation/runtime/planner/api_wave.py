from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import load_runtime_state, write_orchestrator_json
from runtime.truth.api_wave import (
    API_WAVE_CANONICAL_MANIFEST_FILE,
    API_WAVE_CANONICAL_STATE_FILE,
    API_WAVE_EXECUTION_MODE,
    API_WAVE_STREAM_ID,
    load_api_wave_manifest as _load_truth_manifest,
    load_api_wave_state as _load_truth_state,
    persist_api_wave_state as _persist_truth_state,
)

API_WAVE_MANIFEST_FILE = API_WAVE_CANONICAL_MANIFEST_FILE
API_WAVE_STATE_FILE = API_WAVE_CANONICAL_STATE_FILE
API_WAVE_SCHEMA_VERSION = "api_wave_state.v1"
API_WAVE_MANIFEST_SCHEMA_VERSION = "api_wave_manifest.v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def api_wave_manifest_path(root: Path) -> Path:
    return Path(root) / API_WAVE_MANIFEST_FILE


def api_wave_state_path(root: Path) -> Path:
    return Path(root) / "logs-codex-runs" / "orchestrator-state" / API_WAVE_STATE_FILE


def api_wave_owner_task_id(endpoint_id: str) -> str:
    token = str(endpoint_id or "").strip().upper().replace("-", "_") or "ENDPOINT"
    return f"APIWAVE-{token}-DEV-01"


def _manifest_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows = manifest.get("endpoints")
    if not isinstance(rows, list):
        rows = manifest.get("items")
    return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _completed_ids(state: dict[str, Any]) -> set[str]:
    raw = state.get("completed_endpoint_ids")
    if not isinstance(raw, list):
        raw = state.get("completed_endpoints")
    return {str(item).strip() for item in raw if str(item).strip()} if isinstance(raw, list) else set()


def _deferred_ids(state: dict[str, Any]) -> set[str]:
    raw = state.get("deferred_endpoint_ids")
    if not isinstance(raw, list):
        raw = state.get("deferred_endpoints")
    if isinstance(raw, dict):
        raw = list(raw.keys())
    out: set[str] = set()
    if not isinstance(raw, list):
        return out
    for item in raw:
        if isinstance(item, dict):
            token = str(item.get("endpoint_id") or "").strip()
        else:
            token = str(item or "").strip()
        if token:
            out.add(token)
    return out


def default_api_wave_manifest() -> dict[str, Any]:
    return {
        "schema_version": API_WAVE_MANIFEST_SCHEMA_VERSION,
        "mode": API_WAVE_EXECUTION_MODE,
        "enabled": False,
        "stream_id": API_WAVE_STREAM_ID,
        "endpoints": [],
        "updated_at": "",
    }


def default_api_wave_state() -> dict[str, Any]:
    return {
        "schema_version": API_WAVE_SCHEMA_VERSION,
        "wave_id": API_WAVE_STREAM_ID,
        "stream_id": API_WAVE_STREAM_ID,
        "mode": API_WAVE_EXECUTION_MODE,
        "current_endpoint_id": "",
        "current_task_id": "",
        "current_owner_task_id": "",
        "current_status": "idle_ready_for_next_endpoint",
        "current_dispatch_backend": "",
        "current_blocked_reason": "",
        "completed_endpoint_ids": [],
        "deferred_endpoint_ids": [],
        "attempts_by_endpoint": {},
        "consecutive_blocks_by_endpoint": {},
        "last_proof_ref": "",
        "last_public_proof_ref": "",
        "last_public_proof_status": "",
        "last_meaningful_delta_at": "",
        "last_completed_endpoint_id": "",
        "next_endpoint_id": "",
        "updated_at": "",
        "last_transition_at": "",
        "last_dispatch_at": "",
        "last_completion_at": "",
    }


def load_api_wave_manifest(root: Path, *, persist_defaults: bool = False) -> dict[str, Any]:
    payload = _load_truth_manifest(root)
    if not payload and persist_defaults:
        return default_api_wave_manifest()
    normalized = default_api_wave_manifest()
    if isinstance(payload, dict):
        normalized.update(payload)
    normalized["endpoints"] = _manifest_items(normalized)
    return normalized


def save_api_wave_manifest(root: Path, payload: dict[str, Any]) -> Path:
    normalized = default_api_wave_manifest()
    if isinstance(payload, dict):
        normalized.update(payload)
    normalized["schema_version"] = API_WAVE_MANIFEST_SCHEMA_VERSION
    normalized["mode"] = API_WAVE_EXECUTION_MODE
    normalized["stream_id"] = API_WAVE_STREAM_ID
    normalized["updated_at"] = _utc_now()
    normalized["endpoints"] = _manifest_items(normalized)
    return write_orchestrator_json(root, API_WAVE_MANIFEST_FILE, normalized, mirror_docs=False)


def load_api_wave_state(root: Path, *, persist_defaults: bool = False) -> dict[str, Any]:
    payload = _load_truth_state(root)
    if not payload and persist_defaults:
        payload = default_api_wave_state()
        _persist_truth_state(root, payload)
    normalized = default_api_wave_state()
    if isinstance(payload, dict):
        normalized.update(payload)
    return normalized


def save_api_wave_state(root: Path, payload: dict[str, Any]) -> Path:
    normalized = default_api_wave_state()
    if isinstance(payload, dict):
        normalized.update(payload)
    normalized["schema_version"] = API_WAVE_SCHEMA_VERSION
    normalized["wave_id"] = API_WAVE_STREAM_ID
    normalized["stream_id"] = API_WAVE_STREAM_ID
    normalized["mode"] = API_WAVE_EXECUTION_MODE
    normalized["updated_at"] = _utc_now()
    return _persist_truth_state(root, normalized)


def api_wave_mode_enabled(root: Path) -> bool:
    runtime_state = load_runtime_state(root)
    execution_mode = str(runtime_state.get("execution_mode") or "").strip().lower()
    if execution_mode:
        return execution_mode == API_WAVE_EXECUTION_MODE
    manifest = load_api_wave_manifest(root, persist_defaults=False)
    return bool(manifest.get("enabled", False))


def get_api_wave_entry(manifest: dict[str, Any], endpoint_id: str) -> dict[str, Any] | None:
    token = str(endpoint_id or "").strip()
    if not token:
        return None
    for item in _manifest_items(manifest):
        if str(item.get("endpoint_id") or "").strip() == token:
            return item
    return None


def entry_for_batch_id(root: Path, batch_id: str) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, Any]]:
    manifest = load_api_wave_manifest(root, persist_defaults=True)
    state = load_api_wave_state(root, persist_defaults=True)
    token = str(batch_id or "").strip()
    if not token:
        return None, manifest, state
    current_endpoint_id = str(state.get("current_endpoint_id") or "").strip()
    if token == API_WAVE_STREAM_ID and current_endpoint_id:
        current_entry = get_api_wave_entry(manifest, current_endpoint_id)
        if current_entry is not None:
            return current_entry, manifest, state
    for item in _manifest_items(manifest):
        endpoint_id = str(item.get("endpoint_id") or "").strip()
        owner_task_id = api_wave_owner_task_id(endpoint_id)
        if token in {endpoint_id, owner_task_id, API_WAVE_STREAM_ID if endpoint_id == current_endpoint_id else ""}:
            return item, manifest, state
    return None, manifest, state


def api_wave_delivery_contract(entry: dict[str, Any]) -> dict[str, Any]:
    endpoint_id = str(entry.get("endpoint_id") or "api_wave_endpoint").strip() or "api_wave_endpoint"
    route_path = str(entry.get("route_path") or "").strip() or "/api/health"
    public_smoke_path = str(entry.get("public_smoke_path") or route_path).strip() or route_path
    if not public_smoke_path.startswith("http://") and not public_smoke_path.startswith("https://"):
        public_smoke_path = f"http://3.98.20.77{public_smoke_path}"
    ui_required = bool(entry.get("ui_required") or (entry.get("ui_proof", {}) if isinstance(entry.get("ui_proof"), dict) else {}).get("required"))
    return {
        "value_target": endpoint_id,
        "user_visible_delta": f"judge_parity:{route_path}",
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": [public_smoke_path],
            "success_condition": "returns stable ok=true contract with metadata parity",
            "smoke_ref": public_smoke_path,
        },
        "ui_proof": {
            "kind": "public_ui_smoke",
            "url": "http://3.98.20.77/",
            "label": endpoint_id.replace("_", "-"),
            "required": ui_required,
        },
        "done_when": "public_proof_status=ok && user_visible_delta_confirmed=true",
    }


def select_next_endpoint(manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    completed = _completed_ids(state)
    deferred = _deferred_ids(state)
    current = str(state.get("current_endpoint_id") or "").strip()
    items = sorted(
        _manifest_items(manifest),
        key=lambda item: int(item.get("priority_rank") or item.get("priority") or 999),
    )
    if current and current not in completed and current not in deferred:
        current_entry = get_api_wave_entry(manifest, current)
        if current_entry is not None:
            return current_entry
    for item in items:
        endpoint_id = str(item.get("endpoint_id") or "").strip()
        if endpoint_id and endpoint_id not in completed and endpoint_id not in deferred:
            return item
    return None


def ensure_current_endpoint(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    manifest = load_api_wave_manifest(root, persist_defaults=True)
    state = load_api_wave_state(root, persist_defaults=True)
    current_endpoint_id = str(state.get("current_endpoint_id") or "").strip()
    current_status = str(state.get("current_status") or "").strip()
    entry = get_api_wave_entry(manifest, current_endpoint_id) if current_endpoint_id else None
    if entry is not None and current_status not in {"completed", "deferred", "idle_exhausted"}:
        state["next_endpoint_id"] = str(entry.get("endpoint_id") or "").strip()
        return manifest, state, entry
    selected = select_next_endpoint(manifest, state)
    if selected is None:
        state["current_endpoint_id"] = ""
        state["current_task_id"] = ""
        state["current_owner_task_id"] = ""
        state["current_status"] = "idle_exhausted"
        state["next_endpoint_id"] = ""
        state["current_blocked_reason"] = ""
        state["last_transition_at"] = _utc_now()
        save_api_wave_state(root, state)
        return manifest, load_api_wave_state(root), None
    endpoint_id = str(selected.get("endpoint_id") or "").strip()
    state["current_endpoint_id"] = endpoint_id
    state["current_task_id"] = api_wave_owner_task_id(endpoint_id)
    state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_id)
    state["current_status"] = "idle_ready_for_next_endpoint"
    state["current_blocked_reason"] = ""
    state["next_endpoint_id"] = endpoint_id
    state["last_transition_at"] = _utc_now()
    save_api_wave_state(root, state)
    return manifest, load_api_wave_state(root), selected


def apply_public_proof_result(root: Path, *, batch_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    entry, manifest, state = entry_for_batch_id(root, batch_id)
    if entry is None:
        return state
    endpoint_id = str(entry.get("endpoint_id") or "").strip()
    proof_ref = str(artifact.get("proof_ref") or "").strip()
    proof_status = str(artifact.get("status") or "").strip() or "unknown"
    state["last_proof_ref"] = proof_ref
    state["last_public_proof_ref"] = proof_ref
    state["last_public_proof_status"] = proof_status
    state["last_transition_at"] = _utc_now()
    manifest_items = _manifest_items(manifest)
    for item in manifest_items:
        if str(item.get("endpoint_id") or "").strip() == endpoint_id:
            item["last_public_proof"] = proof_ref
    manifest["endpoints"] = manifest_items
    save_api_wave_manifest(root, manifest)
    if proof_status == "ok" and bool(artifact.get("user_visible_delta_confirmed")):
        completed = list(_completed_ids(state))
        if endpoint_id not in completed:
            completed.append(endpoint_id)
        state["completed_endpoint_ids"] = completed
        state["current_endpoint_id"] = ""
        state["current_task_id"] = ""
        state["current_owner_task_id"] = ""
        state["current_status"] = "idle_ready_for_next_endpoint"
        state["current_blocked_reason"] = ""
        state["last_completed_endpoint_id"] = endpoint_id
        state["next_endpoint_id"] = ""
        state["last_completion_at"] = _utc_now()
    else:
        state["current_status"] = "verifying_public_proof"
        state["current_endpoint_id"] = endpoint_id
        state["current_task_id"] = api_wave_owner_task_id(endpoint_id)
        state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_id)
    save_api_wave_state(root, state)
    return load_api_wave_state(root)
