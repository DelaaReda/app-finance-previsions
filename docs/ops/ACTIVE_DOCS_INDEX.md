---
status: active
last_verified: 2026-03-13
---

# Active docs index

Single canonical entrypoint into the current architecture and migration state.

## Canonical entrypoints
- [PLANE_BACKLOG_INTEGRATION_SPEC.md](./PLANE_BACKLOG_INTEGRATION_SPEC.md)
- [CANONICAL_RUNTIME_MODE.md](./CANONICAL_RUNTIME_MODE.md)
- [PLANNER_ORCHESTRATOR_TARGET_SPEC.md](./PLANNER_ORCHESTRATOR_TARGET_SPEC.md)
- [LANGGRAPH_PYDANTICAI_ORCHESTRATION_TARGET.md](./LANGGRAPH_PYDANTICAI_ORCHESTRATION_TARGET.md)
- [APP_VS_AGENT_PROVIDER_BOUNDARY.md](./APP_VS_AGENT_PROVIDER_BOUNDARY.md)
- [MONITOR_ARCHITECTURE_SPEC.md](./MONITOR_ARCHITECTURE_SPEC.md)

`docs/ops/README.md`, `CURRENT_ARCHITECTURE_ENTRYPOINTS.md`, and `../product/planning/README.md` are supporting redirects only. They are not separate canonical entrypoints.

## Active supporting docs required by policy
- [ARCHITECTURAL_BLACKLIST.md](./ARCHITECTURAL_BLACKLIST.md)
- [COMMIT_ONLY_WORKFLOW_POLICY.md](./COMMIT_ONLY_WORKFLOW_POLICY.md)
- [ADR_LANGGRAPH_PYDANTIC_RUNTIME_MIGRATION_2026-03-13.md](./ADR_LANGGRAPH_PYDANTIC_RUNTIME_MIGRATION_2026-03-13.md)
- [ORCHESTRATION_RELIABILITY_SPEC.md](./ORCHESTRATION_RELIABILITY_SPEC.md)
- [DOCTOR_JSON_SPEC.md](./DOCTOR_JSON_SPEC.md)
- [../product/planning/README.md](../product/planning/README.md)

## Current reality
- The doctrinal cutover is done in docs.
- The technical cutover is partial.
- `platform/automation/planning/plane/plane_runtime_sync.py` exists but is not yet the uncontested primary sync path.
- `runtime_truth_reader.py` exists but legacy JSON and JSONL bridges still remain too central in monitor and runtime flows.
- `planner_subagent_manager.py` and `parallel_workstream.py` still carry too much bridge logic.
- Legacy registries and buses remain compatibility surfaces, not the desired end state.

## Hard rules
- Plane OSS is the only front-door for creating and prioritizing initiatives, epics, modules (`BATCH-xx`), and work items.
- Agents use the official Plane MCP server for backlog operations.
- Plane webhooks are the primary intended planning sync intake. API polling is reconciliation only.
- LangGraph + SQLite are the execution truth. `planner` is the only scheduler.
- OpenClaw + systemd are the operator plane.
- `codex exec` is the primary agent executor. `qwen cli` is fallback for agents only. `g4f` is app-only.
- Queue, workboard, and repo docs are projections or references only.
- Active scripts and prompts must never treat `docs/product/planning/tasks.md`, `stories.md`, `epics.md`, or `docs/planning/*` as backlog truth.

## Remaining bridge removal priorities
- make `Plane webhook -> platform/automation/planning/plane/plane_runtime_sync.py -> SQLite/event state -> projections` the live primary path
- make `runtime_truth_reader.py` the main reader for monitor and doctor
- demote legacy registries:
  - `planner-subagents-registry.json`
  - `dynamic-workers-registry.json`
  - `agent-message-bus.jsonl`
  - `intent-registry.json`
- flatten `planner_subagent_manager.py`
- reduce `parallel_workstream.py` to projection or controlled mutation only

## Read as reference or history
- [reference/README.md](./reference/README.md)
- [archive/README.md](./archive/README.md)
- [../product/planning/reference/README.md](../product/planning/reference/README.md)
- [../product/planning/archive/README.md](../product/planning/archive/README.md)
