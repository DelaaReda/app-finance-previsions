from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable

from runtime.core.contracts import OrchestrationEvent
from runtime.truth.event_store import EventStore
from .model_plane import (
    CollectInvocationRequest,
    ModelInvocationPort,
    ResumeInvocationRequest,
    StartInvocationRequest,
    StatusInvocationRequest,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _event_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part or "") for part in parts)
    return f"{prefix}-{hashlib.sha1(payload.encode('utf-8', errors='ignore')).hexdigest()[:16]}"


def _stable_invocation_id(payload: dict[str, Any]) -> str:
    existing = str(payload.get("invocation_id", "") or "").strip()
    if existing:
        return existing
    return _event_id(
        "invocation",
        payload.get("cycle_id"),
        payload.get("batch_id"),
        payload.get("task_id"),
        payload.get("target_role"),
        payload.get("backend"),
    )


def _stable_idempotency_key(payload: dict[str, Any]) -> str:
    existing = str(payload.get("idempotency_key", "") or "").strip()
    if existing:
        return existing
    return _event_id(
        "idem",
        payload.get("task_id"),
        payload.get("target_role"),
        payload.get("backend"),
        payload.get("session_id"),
        payload.get("prompt_digest"),
        payload.get("result_ref"),
    )


def _enrich_payload(payload: dict[str, Any], *, status: str = "") -> dict[str, Any]:
    enriched = dict(payload)
    enriched["invocation_id"] = _stable_invocation_id(enriched)
    enriched["idempotency_key"] = _stable_idempotency_key(enriched)
    enriched["heartbeat_ts"] = str(enriched.get("heartbeat_ts") or _utc_now()).strip() or _utc_now()
    backend_requested = str(enriched.get("backend_requested") or enriched.get("backend") or "").strip()
    backend_used = str(enriched.get("backend_used") or backend_requested or enriched.get("backend") or "").strip()
    enriched["backend_requested"] = backend_requested
    enriched["backend_used"] = backend_used
    enriched["fallback_reason"] = str(enriched.get("fallback_reason") or "none").strip() or "none"
    enriched["provider_plane"] = str(enriched.get("provider_plane") or "agent").strip() or "agent"
    enriched["policy_plane"] = str(enriched.get("policy_plane") or "model_plane").strip() or "model_plane"
    enriched["backend"] = backend_used or backend_requested
    if status:
        enriched["invocation_status"] = status
    else:
        enriched["invocation_status"] = str(enriched.get("invocation_status", "") or "").strip()
    return enriched


class CodexCliAdapter(ModelInvocationPort):
    def __init__(self, root) -> None:
        self.store = EventStore(root)

    def start(
        self,
        request: StartInvocationRequest,
        invoke: Callable[[], tuple[int, str, str, str]] | None = None,
    ) -> dict[str, Any]:
        payload = _enrich_payload(request.model_dump(), status="started")
        payload["ts"] = _utc_now()
        self.store.append_event(
            OrchestrationEvent(
                event_id=_event_id("model-start", payload.get("invocation_id"), payload.get("task_id"), payload.get("backend")),
                ts=payload["ts"],
                event_type="model.start",
                cycle_id=str(payload.get("cycle_id", "") or ""),
                batch_id=str(payload.get("batch_id", "") or ""),
                task_id=str(payload.get("task_id", "") or ""),
                owner_role=str(payload.get("owner_role", "") or ""),
                target_role=str(payload.get("target_role", "") or ""),
                graph_node="dispatch_capability",
                payload=payload,
            )
        )
        if invoke is None:
            return {"ok": True, "recorded": True, **payload}
        rc, stdout, stderr, backend_ref = invoke()
        result_payload = {
            "ts": _utc_now(),
            "invocation_id": str(payload.get("invocation_id", "") or ""),
            "cycle_id": str(payload.get("cycle_id", "") or ""),
            "batch_id": str(payload.get("batch_id", "") or ""),
            "task_id": str(payload.get("task_id", "") or ""),
            "owner_role": str(payload.get("owner_role", "") or ""),
            "target_role": str(payload.get("target_role", "") or ""),
            "backend": str(payload.get("backend_used", "") or payload.get("backend_requested", "") or payload.get("backend", "") or ""),
            "backend_requested": str(payload.get("backend_requested", "") or payload.get("backend", "") or ""),
            "backend_used": str(payload.get("backend_used", "") or payload.get("backend_requested", "") or payload.get("backend", "") or ""),
            "fallback_reason": str(payload.get("fallback_reason", "") or "none"),
            "provider_plane": str(payload.get("provider_plane", "") or "agent"),
            "idempotency_key": str(payload.get("idempotency_key", "") or ""),
            "heartbeat_ts": _utc_now(),
            "invocation_status": "running" if int(rc) == 0 else "failed_to_start",
            "rc": int(rc),
            "stdout_preview": str(stdout or "")[:400],
            "stderr_preview": str(stderr or "")[:400],
            "backend_ref": str(backend_ref or ""),
        }
        self.store.append_event(
            OrchestrationEvent(
                event_id=_event_id("model-start-result", result_payload["invocation_id"], result_payload["task_id"], result_payload["rc"]),
                ts=result_payload["ts"],
                event_type="model.start_result",
                cycle_id=result_payload["cycle_id"],
                batch_id=result_payload["batch_id"],
                task_id=result_payload["task_id"],
                owner_role=result_payload["owner_role"],
                target_role=result_payload["target_role"],
                graph_node="wait_or_collect_result",
                payload=result_payload,
            )
        )
        return result_payload

    def resume(
        self,
        request: ResumeInvocationRequest,
        invoke: Callable[[], tuple[int, str, str, str]] | None = None,
    ) -> dict[str, Any]:
        payload = _enrich_payload(request.model_dump(), status="resumed")
        payload["ts"] = _utc_now()
        self.store.append_event(
            OrchestrationEvent(
                event_id=_event_id("model-resume", payload.get("invocation_id"), payload.get("task_id"), payload.get("session_id")),
                ts=payload["ts"],
                event_type="model.resume",
                cycle_id=str(payload.get("cycle_id", "") or ""),
                batch_id=str(payload.get("batch_id", "") or ""),
                task_id=str(payload.get("task_id", "") or ""),
                owner_role=str(payload.get("owner_role", "") or ""),
                target_role=str(payload.get("target_role", "") or ""),
                graph_node="wait_or_collect_result",
                payload=payload,
            )
        )
        if invoke is None:
            return {"ok": True, "recorded": True, **payload}
        rc, stdout, stderr, backend_ref = invoke()
        result_payload = {
            "ts": _utc_now(),
            "invocation_id": str(payload.get("invocation_id", "") or ""),
            "cycle_id": str(payload.get("cycle_id", "") or ""),
            "batch_id": str(payload.get("batch_id", "") or ""),
            "task_id": str(payload.get("task_id", "") or ""),
            "owner_role": str(payload.get("owner_role", "") or ""),
            "target_role": str(payload.get("target_role", "") or ""),
            "backend": str(payload.get("backend_used", "") or payload.get("backend_requested", "") or payload.get("backend", "") or ""),
            "backend_requested": str(payload.get("backend_requested", "") or payload.get("backend", "") or ""),
            "backend_used": str(payload.get("backend_used", "") or payload.get("backend_requested", "") or payload.get("backend", "") or ""),
            "fallback_reason": str(payload.get("fallback_reason", "") or "none"),
            "provider_plane": str(payload.get("provider_plane", "") or "agent"),
            "idempotency_key": str(payload.get("idempotency_key", "") or ""),
            "heartbeat_ts": _utc_now(),
            "invocation_status": "running" if int(rc) == 0 else "resume_failed",
            "rc": int(rc),
            "stdout_preview": str(stdout or "")[:400],
            "stderr_preview": str(stderr or "")[:400],
            "backend_ref": str(backend_ref or ""),
        }
        self.store.append_event(
            OrchestrationEvent(
                event_id=_event_id("model-resume-result", result_payload["invocation_id"], result_payload["task_id"], result_payload["rc"]),
                ts=result_payload["ts"],
                event_type="model.resume_result",
                cycle_id=result_payload["cycle_id"],
                batch_id=result_payload["batch_id"],
                task_id=result_payload["task_id"],
                owner_role=result_payload["owner_role"],
                target_role=result_payload["target_role"],
                graph_node="wait_or_collect_result",
                payload=result_payload,
            )
        )
        return result_payload

    def collect(self, request: CollectInvocationRequest, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event_payload = _enrich_payload(
            request.model_dump(),
            status=str(request.result_status or "collected"),
        )
        if isinstance(payload, dict) and payload:
            event_payload["payload"] = payload
        event_payload["ts"] = _utc_now()
        self.store.append_event(
            OrchestrationEvent(
                event_id=_event_id("model-collect", event_payload.get("invocation_id"), event_payload.get("task_id"), event_payload.get("result_status")),
                ts=event_payload["ts"],
                event_type="model.collect",
                cycle_id=str(event_payload.get("cycle_id", "") or ""),
                batch_id=str(event_payload.get("batch_id", "") or ""),
                task_id=str(event_payload.get("task_id", "") or ""),
                owner_role=str(event_payload.get("owner_role", "") or ""),
                target_role=str(event_payload.get("target_role", "") or ""),
                graph_node="validate_contract_and_proof",
                payload=event_payload,
            )
        )
        return event_payload

    def status(
        self,
        request: StatusInvocationRequest,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event_payload = _enrich_payload(
            request.model_dump(),
            status=str(request.invocation_status or "heartbeat"),
        )
        if isinstance(payload, dict) and payload:
            event_payload["payload"] = payload
        event_payload["ts"] = _utc_now()
        self.store.append_event(
            OrchestrationEvent(
                event_id=_event_id("model-status", event_payload.get("invocation_id"), event_payload.get("task_id"), event_payload.get("session_id")),
                ts=event_payload["ts"],
                event_type="model.status",
                cycle_id=str(event_payload.get("cycle_id", "") or ""),
                batch_id=str(event_payload.get("batch_id", "") or ""),
                task_id=str(event_payload.get("task_id", "") or ""),
                owner_role=str(event_payload.get("owner_role", "") or ""),
                target_role=str(event_payload.get("target_role", "") or ""),
                graph_node="wait_or_collect_result",
                payload=event_payload,
            )
        )
        return event_payload
