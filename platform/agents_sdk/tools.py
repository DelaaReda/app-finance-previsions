"""Project-specific tool builders for SDK workers."""

from __future__ import annotations

import json
from typing import Any

from .schemas import WorkerEvidence


def build_market_brief_tools(function_tool: Any) -> list[Any]:
    """Create a minimal, bounded toolset for the brief worker."""

    @function_tool
    def read_brief_contract() -> str:
        """Return canonical file anchors for the brief-generation flow."""
        return json.dumps(
            {
                "api_route": "apps/api/src/domains/forecasts/api/brief.py",
                "offline_job": "apps/api/src/platform/legacy/jobs/market_brief.py",
                "planning_handoff": "docs/product/planning/BATCH-25_EXECUTION_HANDOFF_2026-03-13.md",
                "planning_proof": "docs/product/planning/BATCH-25_PROOF_CHECKLIST_2026-03-13.md",
            },
            sort_keys=True,
        )

    @function_tool
    def emit_worker_evidence(
        summary: str,
        planner_artifact: str,
        root_cause: str,
        fix_applied: str,
        verify: str,
        architecture_check: str,
        vision_alignment: str,
        recommended_next: str,
    ) -> dict[str, Any]:
        """Return canonical evidence ready for planner/runtime ingestion."""
        payload = WorkerEvidence(
            summary=summary,
            planner_artifact=planner_artifact,
            root_cause=root_cause,
            fix_applied=fix_applied,
            verify=verify,
            architecture_check=architecture_check,
            vision_alignment=vision_alignment,
            recommended_next=recommended_next,
            files_touched=[planner_artifact],
        )
        return payload.to_workboard_patch()

    return [read_brief_contract, emit_worker_evidence]
