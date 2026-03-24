"""Translate between workboard tasks and SDK worker payloads."""

from __future__ import annotations

from typing import Any, Mapping

from ..context import PlannerTaskContext
from ..schemas import WorkerEvidence, WorkerRunRequest


def request_from_workboard_task(task: Mapping[str, Any]) -> WorkerRunRequest:
    stream_id = str(task.get("stream_id") or task.get("stream") or task.get("batch_id") or "").strip()
    task_id = str(task.get("task_id") or task.get("id") or task.get("task") or "").strip()
    objective = str(task.get("title") or task.get("objective") or task.get("next_action") or task_id).strip()

    doc_refs = []
    for key in ("architecture_plan_ref", "planner_artifact", "doc_ref"):
        token = str(task.get(key) or "").strip()
        if token:
            doc_refs.append(token)

    return WorkerRunRequest(
        stream_id=stream_id,
        task_id=task_id,
        objective=objective,
        batch_id=stream_id or None,
        doc_refs=doc_refs,
        inputs=dict(task),
    )


def context_from_request(request: WorkerRunRequest) -> PlannerTaskContext:
    return PlannerTaskContext(
        stream_id=request.stream_id,
        task_id=request.task_id,
        objective=request.objective,
        batch_id=request.batch_id,
        doc_refs=list(request.doc_refs),
        runtime_metadata=dict(request.inputs),
    )


def evidence_from_run_result(result: Any) -> WorkerEvidence:
    final_output = getattr(result, "final_output", result)
    if isinstance(final_output, WorkerEvidence):
        return final_output
    if isinstance(final_output, dict):
        return WorkerEvidence.model_validate(final_output)
    raise TypeError("Unsupported worker result payload for planner evidence mapping")
