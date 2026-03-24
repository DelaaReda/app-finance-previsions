from __future__ import annotations

from typing import Any

from .compat import BaseModel, ConfigDict


class PlannerDecision(BaseModel):
    model_config = ConfigDict(extra="allow")

    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    owner_role: str = "planner"
    target_role: str = ""
    task_kind: str = ""
    rationale: str = ""
    next_action: str = ""
    blocking_issue: str = "none"
    queue_snapshot_ref: str = ""
    workboard_snapshot_ref: str = ""


class CapabilityTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    owner_role: str = "planner"
    target_role: str = ""
    task_kind: str = ""
    backend: str = ""
    model: str = ""
    thinking: str = ""
    sandbox: str = ""
    timeout_seconds: int = 0
    prompt_digest: str = ""
    prompt_preview: str = ""
    queue_snapshot_ref: str = ""
    workboard_snapshot_ref: str = ""
    metadata: dict[str, Any] = {}


class CapabilityResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    owner_role: str = "planner"
    target_role: str = ""
    backend: str = ""
    status: str = ""
    rc: int = 0
    summary: str = ""
    blocking_issue: str = "none"
    artifact: str = "none"
    verify: str = "none"
    files_touched: str = "none"
    tests_run: str = "none"
    commit_sha: str = "none"
    raw_output_ref: str = ""
    backend_ref: str = ""
    result_path: str = ""
    metadata: dict[str, Any] = {}


class DeliveryProof(BaseModel):
    model_config = ConfigDict(extra="allow")

    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    artifact: str = "none"
    verify: str = "none"
    tests_run: str = "none"
    commit_sha: str = "none"
    proof_manifest: str = ""
    summary: str = ""


class RuntimeCheck(BaseModel):
    model_config = ConfigDict(extra="allow")

    cycle_id: str = ""
    task_id: str = ""
    status: str = "unknown"
    source: str = ""
    detail: dict[str, Any] = {}


class ScrumAdvice(BaseModel):
    model_config = ConfigDict(extra="allow")

    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    target_role: str = ""
    message_id: str = ""
    recommendation: str = ""
    blocking_issue: str = "none"


class PlannerGraphState(BaseModel):
    model_config = ConfigDict(extra="allow")

    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    task_kind: str = ""
    owner_role: str = "planner"
    target_role: str = ""
    queue_snapshot_ref: str = ""
    workboard_snapshot_ref: str = ""
    capability_request: dict[str, Any] = {}
    capability_result: dict[str, Any] = {}
    delivery_proof: dict[str, Any] = {}
    guard_status: str = "unknown"
    runtime_health: str = "unknown"
    next_action: str = ""
    blocking_issue: str = "none"
    checkpoint_id: str = ""
    current_node: str = "load_runtime_truth"
    status: str = "pending"
    updated_at: str = ""
    engine: str = "shadow_fallback"


class OrchestrationEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str = ""
    ts: str = ""
    event_type: str = ""
    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    owner_role: str = ""
    target_role: str = ""
    checkpoint_id: str = ""
    graph_node: str = ""
    payload: dict[str, Any] = {}
