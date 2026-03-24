"""Context objects shared across one bounded worker run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlannerTaskContext:
    """Runtime context passed into an SDK worker run."""

    stream_id: str
    task_id: str
    objective: str
    role: str = "planner"
    batch_id: str | None = None
    doc_refs: list[str] = field(default_factory=list)
    runtime_metadata: dict[str, Any] = field(default_factory=dict)

    def to_prompt_block(self) -> str:
        refs = ", ".join(self.doc_refs) if self.doc_refs else "none"
        batch = self.batch_id or self.stream_id
        return (
            f"stream_id={self.stream_id}; "
            f"task_id={self.task_id}; "
            f"batch_id={batch}; "
            f"role={self.role}; "
            f"doc_refs={refs}"
        )
