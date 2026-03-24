from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.core.availability import build_runtime_capabilities
from runtime.core.contracts import CapabilityResult, CapabilityTask, DeliveryProof, OrchestrationEvent, PlannerGraphState, RuntimeCheck
from runtime.truth.event_store import EventStore


GRAPH_NODES = (
    "load_runtime_truth",
    "reconcile_runtime_state",
    "select_actionable_task",
    "dispatch_capability",
    "wait_or_collect_result",
    "validate_contract_and_proof",
    "apply_workboard_mutation",
    "emit_events_and_monitor_projection",
    "close_or_requeue",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _checkpoint_id(task_id: str, node: str, status: str) -> str:
    payload = f"{task_id}|{node}|{status}|{_utc_now()}"
    return hashlib.sha1(payload.encode("utf-8", errors="ignore")).hexdigest()[:16]


class PlannerGraphRuntime:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.store = EventStore(self.root)
        caps = build_runtime_capabilities()
        self.engine = "langgraph" if caps.get("langgraph_enabled") else "shadow_fallback"

    def observe_dispatch(self, task: CapabilityTask) -> dict[str, Any]:
        state = self._state_for_task(task.task_id)
        state.cycle_id = task.cycle_id or state.cycle_id
        state.batch_id = task.batch_id or state.batch_id
        state.task_id = task.task_id or state.task_id
        state.task_kind = task.task_kind or state.task_kind
        state.owner_role = task.owner_role or state.owner_role
        state.target_role = task.target_role or state.target_role
        state.queue_snapshot_ref = task.queue_snapshot_ref or state.queue_snapshot_ref
        state.workboard_snapshot_ref = task.workboard_snapshot_ref or state.workboard_snapshot_ref
        state.capability_request = task.model_dump()
        state.current_node = "wait_or_collect_result"
        state.status = "running"
        state.next_action = "wait_or_collect_result"
        state.blocking_issue = "none"
        state.updated_at = _utc_now()
        state.checkpoint_id = _checkpoint_id(task.task_id, state.current_node, state.status)
        state.engine = self.engine
        self.store.upsert_graph_state(state)
        self.store.append_event(
            OrchestrationEvent(
                event_id=_checkpoint_id(task.task_id, "dispatch_capability", "event"),
                ts=state.updated_at,
                event_type="graph.dispatch_capability",
                cycle_id=state.cycle_id,
                batch_id=state.batch_id,
                task_id=state.task_id,
                owner_role=state.owner_role,
                target_role=state.target_role,
                checkpoint_id=state.checkpoint_id,
                graph_node="dispatch_capability",
                payload={"capability_task": task.model_dump(), "engine": self.engine},
            )
        )
        return state.model_dump()

    def observe_result(
        self,
        task: CapabilityTask,
        result: CapabilityResult,
        delivery_proof: DeliveryProof | None = None,
        runtime_check: RuntimeCheck | None = None,
    ) -> dict[str, Any]:
        state = self._state_for_task(task.task_id)
        state.cycle_id = task.cycle_id or state.cycle_id
        state.batch_id = task.batch_id or state.batch_id
        state.task_id = task.task_id or state.task_id
        state.task_kind = task.task_kind or state.task_kind
        state.owner_role = task.owner_role or state.owner_role
        state.target_role = task.target_role or state.target_role
        state.capability_request = task.model_dump()
        state.capability_result = result.model_dump()
        state.delivery_proof = (delivery_proof.model_dump() if delivery_proof is not None else state.delivery_proof)
        if runtime_check is not None:
            state.runtime_health = runtime_check.status or state.runtime_health
        result_status = str(result.status or "").strip().lower()
        if result_status in {"completed", "done", "pass", "ok", "success", "merged"}:
            state.current_node = "apply_workboard_mutation"
            state.status = "ready_to_merge"
            state.guard_status = "validated"
            state.next_action = "apply_workboard_mutation"
            state.blocking_issue = "none"
        elif result_status == "blocked":
            state.current_node = "close_or_requeue"
            state.status = "blocked"
            state.guard_status = "blocked"
            state.next_action = "requeue"
            state.blocking_issue = result.blocking_issue or "blocked"
        else:
            state.current_node = "close_or_requeue"
            state.status = "retryable"
            state.guard_status = "retryable"
            state.next_action = "retry_capability"
            state.blocking_issue = result.blocking_issue or f"rc_{int(result.rc)}"
        state.updated_at = _utc_now()
        state.checkpoint_id = _checkpoint_id(task.task_id, state.current_node, state.status)
        state.engine = self.engine
        self.store.upsert_graph_state(state)
        self.store.append_event(
            OrchestrationEvent(
                event_id=_checkpoint_id(task.task_id, "validate_contract_and_proof", "event"),
                ts=state.updated_at,
                event_type="graph.validate_contract_and_proof",
                cycle_id=state.cycle_id,
                batch_id=state.batch_id,
                task_id=state.task_id,
                owner_role=state.owner_role,
                target_role=state.target_role,
                checkpoint_id=state.checkpoint_id,
                graph_node="validate_contract_and_proof",
                payload={
                    "capability_result": result.model_dump(),
                    "delivery_proof": delivery_proof.model_dump() if delivery_proof is not None else {},
                    "runtime_check": runtime_check.model_dump() if runtime_check is not None else {},
                    "engine": self.engine,
                },
            )
        )
        return state.model_dump()

    def observe_merge(self, task: CapabilityTask, merged: bool, note: str = "") -> dict[str, Any]:
        state = self._state_for_task(task.task_id)
        mutation_ts = _utc_now()
        self.store.append_event(
            OrchestrationEvent(
                event_id=_checkpoint_id(task.task_id, "apply_workboard_mutation", "event"),
                ts=mutation_ts,
                event_type="graph.apply_workboard_mutation",
                cycle_id=state.cycle_id or task.cycle_id,
                batch_id=state.batch_id or task.batch_id,
                task_id=state.task_id or task.task_id,
                owner_role=state.owner_role or task.owner_role,
                target_role=state.target_role or task.target_role,
                checkpoint_id=state.checkpoint_id,
                graph_node="apply_workboard_mutation",
                payload={"merged": bool(merged), "note": str(note or ""), "engine": self.engine},
            )
        )
        state.current_node = "close_or_requeue"
        state.status = "merged" if merged else "requeue"
        state.next_action = "done" if merged else "retry_capability"
        state.blocking_issue = "none" if merged else (note or state.blocking_issue or "merge_deferred")
        state.updated_at = _utc_now()
        state.checkpoint_id = _checkpoint_id(task.task_id, state.current_node, state.status)
        state.engine = self.engine
        self.store.upsert_graph_state(state)
        self.store.append_event(
            OrchestrationEvent(
                event_id=_checkpoint_id(task.task_id, "close_or_requeue", "event"),
                ts=state.updated_at,
                event_type="graph.close_or_requeue",
                cycle_id=state.cycle_id,
                batch_id=state.batch_id,
                task_id=state.task_id,
                owner_role=state.owner_role,
                target_role=state.target_role,
                checkpoint_id=state.checkpoint_id,
                graph_node="close_or_requeue",
                payload={"merged": bool(merged), "note": str(note or ""), "engine": self.engine},
            )
        )
        return state.model_dump()

    def snapshot(self, *, limit: int = 50) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "write_primary": True,
            "primary_source": "sqlite_event_store",
            "projection_secondary_only": True,
            "nodes": list(GRAPH_NODES),
            "states": self.store.latest_graph_states(limit=limit),
            "generated_at": _utc_now(),
        }

    def _state_for_task(self, task_id: str) -> PlannerGraphState:
        payload = self.store.load_graph_state(task_id)
        if payload:
            try:
                return PlannerGraphState.model_validate(payload)
            except Exception:
                pass
        return PlannerGraphState(task_id=str(task_id or ""), updated_at=_utc_now(), engine=self.engine)
