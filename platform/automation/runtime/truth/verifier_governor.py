from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import resolve_orchestrator_read_path, write_orchestrator_json


VERIFIER_STATE_FILE = "verifier-state.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def verifier_state_path(root: Path) -> Path:
    return resolve_orchestrator_read_path(root, VERIFIER_STATE_FILE)


def load_verifier_state(root: Path) -> dict[str, Any]:
    path = verifier_state_path(root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {"schema_version": "verifier_state.v1"}
    return payload if isinstance(payload, dict) else {"schema_version": "verifier_state.v1"}


def persist_verifier_state(root: Path, payload: dict[str, Any]) -> Path:
    state = {"schema_version": "verifier_state.v1"}
    if isinstance(payload, dict):
        state.update(payload)
    state["updated_at"] = _utc_now()
    return write_orchestrator_json(root, VERIFIER_STATE_FILE, state, mirror_docs=False)


def build_verifier_trigger_fingerprint(delivery_state: dict[str, Any]) -> str:
    current_public_proof = (
        delivery_state.get("current_public_proof", {})
        if isinstance(delivery_state.get("current_public_proof"), dict)
        else {}
    )
    current_value_target = (
        delivery_state.get("current_value_target", {})
        if isinstance(delivery_state.get("current_value_target"), dict)
        else {}
    )
    payload = {
        "active_batch_id": str(delivery_state.get("active_batch_id") or "").strip().upper() or None,
        "phase": str(delivery_state.get("phase") or "").strip() or None,
        "public_proof_status": str(delivery_state.get("public_proof_status") or "").strip() or None,
        "last_meaningful_delta_at": str(delivery_state.get("last_meaningful_delta_at") or "").strip() or None,
        "proof_ref": str(current_public_proof.get("proof_ref") or "").strip() or None,
        "proof_batch_id": str(current_public_proof.get("batch_id") or "").strip().upper() or None,
        "target_batch_id": str(current_value_target.get("batch_id") or "").strip().upper() or None,
        "user_visible_delta": str(current_value_target.get("user_visible_delta") or "").strip() or None,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def should_run_verifier(
    delivery_state: dict[str, Any],
    verifier_state: dict[str, Any] | None = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    state = verifier_state if isinstance(verifier_state, dict) else {}
    active_batch_id = str(delivery_state.get("active_batch_id") or "").strip().upper()
    phase = str(delivery_state.get("phase") or "").strip()
    public_proof_status = str(delivery_state.get("public_proof_status") or "").strip().lower()
    product_done = bool(delivery_state.get("product_done"))
    current_public_proof = (
        delivery_state.get("current_public_proof", {})
        if isinstance(delivery_state.get("current_public_proof"), dict)
        else {}
    )
    proof_batch_id = str(current_public_proof.get("batch_id") or "").strip().upper()
    fingerprint = build_verifier_trigger_fingerprint(delivery_state)
    last_fingerprint = str(state.get("last_trigger_fingerprint") or "").strip()
    last_status = str(state.get("last_status") or "").strip().lower()

    if force:
        return {
            "should_run": True,
            "reason": "force",
            "batch_id": active_batch_id or None,
            "trigger_fingerprint": fingerprint,
        }
    if not active_batch_id:
        return {"should_run": False, "reason": "no_active_batch", "batch_id": None, "trigger_fingerprint": fingerprint}
    if phase != "verifying_public_proof":
        return {
            "should_run": False,
            "reason": "phase_not_verifying_public_proof",
            "batch_id": active_batch_id,
            "trigger_fingerprint": fingerprint,
        }
    if product_done:
        return {
            "should_run": False,
            "reason": "batch_already_closed",
            "batch_id": active_batch_id,
            "trigger_fingerprint": fingerprint,
        }
    if public_proof_status == "ok" and proof_batch_id == active_batch_id:
        return {
            "should_run": False,
            "reason": "public_proof_already_ok",
            "batch_id": active_batch_id,
            "trigger_fingerprint": fingerprint,
        }
    if last_fingerprint and last_fingerprint == fingerprint:
        if last_status == "maintenance":
            return {
                "should_run": False,
                "reason": "maintenance_requires_explicit_retry",
                "batch_id": active_batch_id,
                "trigger_fingerprint": fingerprint,
            }
        if public_proof_status == "error":
            return {
                "should_run": False,
                "reason": "public_proof_error_no_new_delta",
                "batch_id": active_batch_id,
                "trigger_fingerprint": fingerprint,
            }
        return {
            "should_run": False,
            "reason": "no_change",
            "batch_id": active_batch_id,
            "trigger_fingerprint": fingerprint,
        }
    reason = "new_batch" if str(state.get("last_batch_id") or "").strip().upper() != active_batch_id else "state_changed"
    return {
        "should_run": True,
        "reason": reason,
        "batch_id": active_batch_id,
        "trigger_fingerprint": fingerprint,
    }


def record_verifier_result(
    root: Path,
    delivery_state: dict[str, Any],
    artifact: dict[str, Any],
    *,
    decision_reason: str,
) -> Path:
    current_public_proof = (
        delivery_state.get("current_public_proof", {})
        if isinstance(delivery_state.get("current_public_proof"), dict)
        else {}
    )
    payload = {
        "last_batch_id": str(artifact.get("batch_id") or delivery_state.get("active_batch_id") or "").strip().upper() or None,
        "last_status": str(artifact.get("status") or "").strip() or None,
        "last_run_at": str(artifact.get("timestamp") or _utc_now()).strip() or _utc_now(),
        "last_trigger_fingerprint": build_verifier_trigger_fingerprint(delivery_state),
        "last_decision_reason": str(decision_reason or "state_changed").strip() or "state_changed",
        "last_public_proof_status": str(delivery_state.get("public_proof_status") or "").strip() or None,
        "last_delivery_phase": str(delivery_state.get("phase") or "").strip() or None,
        "last_meaningful_delta_at": str(delivery_state.get("last_meaningful_delta_at") or "").strip() or None,
        "last_proof_ref": str(artifact.get("proof_ref") or current_public_proof.get("proof_ref") or "").strip() or None,
    }
    return persist_verifier_state(root, payload)
