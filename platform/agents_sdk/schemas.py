"""Structured request and evidence payloads for SDK workers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkerRunRequest(BaseModel):
    stream_id: str
    task_id: str
    objective: str
    batch_id: str | None = None
    doc_refs: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    model: str | None = None


class WorkerEvidence(BaseModel):
    summary: str
    planner_artifact: str
    root_cause: str
    fix_applied: str
    verify: str
    reuse_check: str = "NONE(no_direct_reuse_this_tick)"
    tests_run: str = "SKIP(doc_only)"
    cmd: str = "SKIP(planner_doc_only)"
    files_touched: list[str] = Field(default_factory=list)
    architecture_check: str
    vision_alignment: str
    recommended_next: str
    blocking_issue: str | None = None

    def to_workboard_patch(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "planner_artifact": self.planner_artifact,
            "root_cause": self.root_cause,
            "fix_applied": self.fix_applied,
            "verify": self.verify,
            "reuse_check": self.reuse_check,
            "tests_run": self.tests_run,
            "cmd": self.cmd,
            "files_touched": list(self.files_touched),
            "architecture_check": self.architecture_check,
            "vision_alignment": self.vision_alignment,
            "recommended_next": self.recommended_next,
            "blocking_issue": self.blocking_issue,
        }
