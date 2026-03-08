#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

ALLOWED_PARENT_ROLES = {"planner", "dev", "admin"}
FORBIDDEN_PARENT_ROLES = {"scrum_master"}

WORKER_SPECS = {
    "repo_scan_worker": {
        "task_kinds": {"heavy", "parallelizable", "investigation", "repo_scan"},
        "result_kind": "investigation_result",
        "thinking": "medium",
    },
    "test_worker": {
        "task_kinds": {"heavy", "parallelizable", "targeted_test"},
        "result_kind": "test_result",
        "thinking": "medium",
    },
    "qa_review_worker": {
        "task_kinds": {"qa_review", "targeted_test", "browser_validation", "delivery_review"},
        "result_kind": "qa_fix_result",
        "thinking": "high",
    },
    "runtime_diag_worker": {
        "task_kinds": {"heavy", "parallelizable", "runtime_diag", "investigation"},
        "result_kind": "investigation_result",
        "thinking": "medium",
    },
    "patch_proposal_worker": {
        "task_kinds": {"heavy", "parallelizable", "investigation", "patch_proposal"},
        "result_kind": "patch_proposal",
        "thinking": "high",
    },
}

RESULT_KINDS = {
    "evidence",
    "investigation_result",
    "test_result",
    "patch_proposal",
    "qa_fix_result",
    "runtime_diag_result",
}

STATUS_VALUES = {"spawned", "running", "completed", "failed", "merged", "cleaned"}


def canonical_role(role: str) -> str:
    token = (role or "").strip().lower()
    if token in {"backend_engineer", "frontend_engineer", "data_analyst", "integrator"}:
        return "dev"
    if token in {"tester", "qa", "infra_engineer", "clawsentinel"}:
        return "admin"
    if token in {"analyst", "architect", "po", "vision-architect-tasks-planner", "vision_architect_tasks_planner"}:
        return "planner"
    return token


def worker_spec(worker_type: str) -> dict:
    return WORKER_SPECS.get((worker_type or "").strip(), {})


def worker_allowed(parent_role: str, worker_type: str, task_kind: str) -> tuple[bool, str]:
    role = canonical_role(parent_role)
    if role in FORBIDDEN_PARENT_ROLES:
        return False, f"role_forbidden:{role}"
    if role not in ALLOWED_PARENT_ROLES:
        return False, f"role_unsupported:{role}"
    spec = worker_spec(worker_type)
    if not spec:
        return False, f"worker_type_unknown:{worker_type}"
    kind = (task_kind or "").strip().lower()
    if kind and kind not in spec["task_kinds"]:
        return False, f"task_kind_not_allowed:{kind}"
    return True, "ok"


def default_result_kind(worker_type: str) -> str:
    spec = worker_spec(worker_type)
    return str(spec.get("result_kind") or "evidence")


def default_thinking(worker_type: str) -> str:
    spec = worker_spec(worker_type)
    return str(spec.get("thinking") or "medium")


@dataclass
class WorkerResult:
    worker_id: str
    worker_type: str
    owner_task_id: str
    parent_role: str
    result_kind: str
    status: str
    summary: str
    artifact: str = ""
    verify: str = ""
    raw_output_ref: str = ""
    backend: str = ""
    backend_ref: str = ""
    started_at: str = ""
    finished_at: str = ""

    def as_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=True, indent=2) + "\n"


@dataclass
class WorkerRecord:
    worker_id: str
    worker_type: str
    parent_role: str
    owner_task_id: str
    task_kind: str
    status: str
    created_at: str
    expires_at: str
    ttl_min: int
    backend: str = ""
    backend_ref: str = ""
    last_update_at: str = ""
    merged_at: str = ""
    result_kind: str = ""
    summary: str = ""
    artifact: str = ""
    verify: str = ""
    raw_output_ref: str = ""
    message_ref: str = ""
    retries_used: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["metadata"] = dict(self.metadata or {})
        return payload

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=True, indent=2) + "\n"

    @classmethod
    def from_dict(cls, payload: dict) -> "WorkerRecord":
        data = dict(payload or {})
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        return cls(
            worker_id=str(data.get("worker_id", "")),
            worker_type=str(data.get("worker_type", "")),
            parent_role=canonical_role(str(data.get("parent_role", ""))),
            owner_task_id=str(data.get("owner_task_id", "")),
            task_kind=str(data.get("task_kind", "")),
            status=str(data.get("status", "spawned")),
            created_at=str(data.get("created_at", "")),
            expires_at=str(data.get("expires_at", "")),
            ttl_min=int(data.get("ttl_min", 0) or 0),
            backend=str(data.get("backend", "")),
            backend_ref=str(data.get("backend_ref", "")),
            last_update_at=str(data.get("last_update_at", "")),
            merged_at=str(data.get("merged_at", "")),
            result_kind=str(data.get("result_kind", "")),
            summary=str(data.get("summary", "")),
            artifact=str(data.get("artifact", "")),
            verify=str(data.get("verify", "")),
            raw_output_ref=str(data.get("raw_output_ref", "")),
            message_ref=str(data.get("message_ref", "")),
            retries_used=int(data.get("retries_used", 0) or 0),
            metadata={str(k): str(v) for k, v in metadata.items()},
        )


def save_result(path: Path, result: WorkerResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.to_json(), encoding="utf-8")
