from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.planner.api_wave import (
    API_WAVE_BATCH_ID,
    api_wave_delivery_contract,
    api_wave_manifest_path,
    api_wave_mode_enabled,
    api_wave_owner_task_id,
    api_wave_state_path,
    apply_public_proof_result,
    ensure_current_endpoint,
    entry_for_batch_id,
    load_api_wave_manifest,
    load_api_wave_state,
    record_blocked_or_deferred,
    save_api_wave_manifest as persist_api_wave_manifest,
    save_api_wave_state as persist_api_wave_state,
    select_next_endpoint,
)
from runtime.truth.event_store import latest_graph_states


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def api_wave_proof_path(root: Path, endpoint_id: str) -> Path:
    token = str(endpoint_id or "").strip().lower().replace("-", "_")
    return Path(root) / "logs-codex-runs" / "orchestrator-state" / "api-wave-proof" / f"{token}.json"


def load_api_wave_proof(root: Path, endpoint_id: str) -> dict[str, Any]:
    path = api_wave_proof_path(root, endpoint_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def persist_api_wave_proof(root: Path, endpoint_id: str, payload: dict[str, Any]) -> Path:
    path = api_wave_proof_path(root, endpoint_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return path


def build_api_wave_snapshot(
    root: Path,
    *,
    delivery_state: dict[str, Any] | None = None,
    normalized_states: list[dict[str, Any]] | None = None,
    prior_state: dict[str, Any] | None = None,
    now: Any = None,
) -> dict[str, Any]:
    root = Path(root)
    delivery_state = delivery_state if isinstance(delivery_state, dict) else {}
    manifest = load_api_wave_manifest(root, persist_defaults=True)
    enabled = bool(manifest.get("enabled")) and api_wave_mode_enabled(root)
    if not enabled:
        return {
            "enabled": False,
            "mode": "api_autonomy_mode",
            "stream_id": API_WAVE_BATCH_ID,
            "batch_id": API_WAVE_BATCH_ID,
            "wave_batch_id": API_WAVE_BATCH_ID,
            "wave_id": API_WAVE_BATCH_ID,
            "dispatch_ready": False,
            "current_endpoint": None,
            "next_endpoint": None,
            "current_endpoint_id": "",
            "next_endpoint_id": "",
            "current_task_id": "",
            "current_status": "disabled",
            "current_proof_status": "none",
            "completed_endpoint_ids": [],
            "deferred_endpoint_ids": [],
            "deferred_endpoints": [],
            "blocked_streaks": {},
            "remaining_count": 0,
            "total_count": 0,
            "last_public_proof_ref": "none",
            "last_public_proof_status": "none",
            "reason": "disabled",
            "state": load_api_wave_state(root, persist_defaults=True),
        }

    state = load_api_wave_state(root, persist_defaults=True)
    if isinstance(prior_state, dict):
        merged = dict(prior_state)
        merged.update(state)
        persist_api_wave_state(root, merged)
        state = load_api_wave_state(root, persist_defaults=True)

    current_entry = ensure_current_endpoint(root)
    state = load_api_wave_state(root, persist_defaults=True)
    current_entry = current_entry or entry_for_batch_id(root, state.get("current_endpoint_id"))[0]
    next_entry = select_next_endpoint(manifest, state)
    current_endpoint_id = str(state.get("current_endpoint_id") or "").strip()
    current_task_id = str(state.get("current_owner_task_id") or state.get("current_task_id") or "").strip()
    current_status = str(state.get("current_status") or "idle_ready_for_next_endpoint").strip().lower()
    current_proof_status = str(state.get("last_public_proof_status") or "none").strip().lower() or "none"
    last_public_proof_ref = str(state.get("last_public_proof_ref") or "none").strip() or "none"
    reason = "idle"

    graph_rows = normalized_states if isinstance(normalized_states, list) else latest_graph_states(root, limit=80)
    observed = None
    for row in graph_rows:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("task_id") or "").strip()
        if current_task_id and task_id.upper() == current_task_id.upper():
            observed = row
            break

    ec2_reachable = bool(delivery_state.get("ec2_reachable"))
    classic_active_batch_id = str(delivery_state.get("active_batch_id") or "").strip().upper()

    if current_entry is None:
        current_status = "exhausted"
        reason = "exhausted"
    elif not ec2_reachable:
        current_status = "external_outage"
        reason = "external_outage"
    elif classic_active_batch_id and classic_active_batch_id != API_WAVE_BATCH_ID:
        current_status = "waiting_active_batch"
        reason = "waiting_active_batch"
    elif observed is None:
        current_status = "ready"
        reason = "dispatch_ready"
    else:
        observed_status = str(observed.get("status") or "").strip().lower()
        observed_updated_at = str(observed.get("updated_at") or "").strip()
        observed_issue = str(observed.get("blocking_issue") or "").strip()
        previously_seen = (
            str(state.get("last_observed_task_status") or "").strip().lower() == observed_status
            and str(state.get("last_observed_task_updated_at") or "").strip() == observed_updated_at
            and str(state.get("last_observed_blocking_issue") or "").strip() == observed_issue
        )

        if observed_status in {"running", "pending", "review", "in_progress"}:
            current_status = "active_delivery"
            reason = "active_delivery"
        elif observed_status in {"ready_to_merge", "done", "completed", "merged"}:
            if last_public_proof_ref != "none" and current_proof_status == "ok":
                artifact = load_api_wave_proof(root, current_endpoint_id) if current_endpoint_id else {}
                if artifact:
                    apply_public_proof_result(root, batch_id=API_WAVE_BATCH_ID, artifact=artifact)
                    state = load_api_wave_state(root, persist_defaults=True)
                    current_entry = ensure_current_endpoint(root)
                    current_endpoint_id = str(state.get("current_endpoint_id") or "").strip()
                    current_task_id = str(state.get("current_owner_task_id") or state.get("current_task_id") or "").strip()
                    current_status = str(state.get("current_status") or "idle_ready_for_next_endpoint").strip().lower()
                    current_proof_status = str(state.get("last_public_proof_status") or "ok").strip().lower() or "ok"
                    last_public_proof_ref = str(state.get("last_public_proof_ref") or "none").strip() or "none"
                    reason = "dispatch_ready" if current_entry is not None else "exhausted"
                else:
                    current_status = "verifying_public_proof"
                    current_proof_status = "pending"
                    reason = "waiting_public_proof"
            else:
                current_status = "verifying_public_proof"
                current_proof_status = "pending"
                reason = "waiting_public_proof"
        elif observed_status in {"blocked", "failed", "retryable"}:
            if not previously_seen:
                state = record_blocked_or_deferred(root, state, current_entry or {}, observed)
            state = load_api_wave_state(root, persist_defaults=True)
            current_status = str(state.get("current_status") or "blocked").strip().lower()
            if current_status == "blocked_route_admin":
                reason = "route_admin"
            elif current_status == "blocked_escalate_scrum":
                reason = "route_scrum"
            elif current_status == "defer_current_endpoint":
                reason = "defer_current_endpoint"
            else:
                reason = "backoff"
        else:
            current_status = "ready"
            reason = "dispatch_ready"

        updated = dict(state)
        updated["last_observed_task_status"] = observed_status
        updated["last_observed_task_updated_at"] = observed_updated_at
        updated["last_observed_blocking_issue"] = observed_issue
        updated["current_status"] = current_status
        updated["current_endpoint_status"] = current_status
        updated["updated_at"] = _utc_now()
        persist_api_wave_state(root, updated)
        state = load_api_wave_state(root, persist_defaults=True)

    completed = list(state.get("completed_endpoint_ids") or [])
    deferred = list(state.get("deferred_endpoint_ids") or [])
    selectable = [
        row
        for row in manifest.get("items", [])
        if isinstance(row, dict) and bool(row.get("selectable", True))
    ]
    remaining_count = max(len(selectable) - len(completed) - len(deferred), 0)
    dispatch_ready = bool(
        ec2_reachable
        and current_entry is not None
        and reason == "dispatch_ready"
        and not classic_active_batch_id
    )
    return {
        "enabled": True,
        "mode": "api_autonomy_mode",
        "stream_id": API_WAVE_BATCH_ID,
        "batch_id": API_WAVE_BATCH_ID,
        "wave_batch_id": API_WAVE_BATCH_ID,
        "wave_id": API_WAVE_BATCH_ID,
        "dispatch_ready": dispatch_ready,
        "current_endpoint": current_entry,
        "next_endpoint": next_entry if next_entry != current_entry else None,
        "current_endpoint_id": str(state.get("current_endpoint_id") or "").strip(),
        "next_endpoint_id": str(state.get("next_endpoint_id") or "").strip(),
        "current_task_id": str(state.get("current_owner_task_id") or state.get("current_task_id") or "").strip(),
        "current_status": current_status,
        "current_proof_status": current_proof_status,
        "completed_endpoint_ids": completed,
        "completed_endpoints": completed,
        "deferred_endpoint_ids": deferred,
        "deferred_endpoints": list(state.get("deferred_endpoints") or []),
        "blocked_streaks": dict(state.get("consecutive_non_runtime_blocks") or {}),
        "consecutive_block_count_by_endpoint": dict(state.get("consecutive_non_runtime_blocks") or {}),
        "remaining_count": remaining_count,
        "total_count": len(selectable),
        "last_public_proof_ref": last_public_proof_ref,
        "last_public_proof_status": str(state.get("last_public_proof_status") or "none").strip().lower() or "none",
        "reason": reason,
        "state": state,
    }


__all__ = [
    "API_WAVE_BATCH_ID",
    "api_wave_delivery_contract",
    "api_wave_manifest_path",
    "api_wave_mode_enabled",
    "api_wave_owner_task_id",
    "api_wave_proof_path",
    "api_wave_state_path",
    "apply_public_proof_result",
    "build_api_wave_snapshot",
    "entry_for_batch_id",
    "load_api_wave_manifest",
    "load_api_wave_proof",
    "load_api_wave_state",
    "persist_api_wave_manifest",
    "persist_api_wave_proof",
    "persist_api_wave_state",
]
