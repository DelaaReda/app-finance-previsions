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
- [JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md](./JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md)
- [EC2_APP_RUNTIME_QUICK_REFERENCE.md](./EC2_APP_RUNTIME_QUICK_REFERENCE.md)
- [COMMIT_ONLY_WORKFLOW_POLICY.md](./COMMIT_ONLY_WORKFLOW_POLICY.md)
- [ADR_LANGGRAPH_PYDANTIC_RUNTIME_MIGRATION_2026-03-13.md](./ADR_LANGGRAPH_PYDANTIC_RUNTIME_MIGRATION_2026-03-13.md)
- [ORCHESTRATION_RELIABILITY_SPEC.md](./ORCHESTRATION_RELIABILITY_SPEC.md)
- [DOCTOR_JSON_SPEC.md](./DOCTOR_JSON_SPEC.md)
- [../product/planning/README.md](../product/planning/README.md)

## Current reality
- The doctrinal cutover is done in docs.
- The technical cutover is partial.
- The public app-serving stack now lives on EC2 public endpoints, not on the local VM.
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
- The local VM is orchestration-only. Public product/API checks must use the EC2 public endpoints.
- EC2 app control from the UTM VM must go through `scripts/aws_remote_app_control.sh`.
- Mac and the UTM VM share the same workspace view; this is local workspace sharing only.
- EC2 app publication is a separate shared-workspace -> AWS step.
- Canonical operator path is Mac-side publication; if the operator explicitly launches the same wrapper from the UTM VM, it still publishes the same shared workspace snapshot, not VM-local orchestration state.
- Queue, workboard, and repo docs are projections or references only.
- Active scripts and prompts must never treat `docs/product/planning/tasks.md`, `stories.md`, `epics.md`, or `docs/planning/*` as backlog truth.
- If a proof, migration report, team chat dump, or legacy ops note still shows `localhost:*` app endpoints, treat it as historical evidence only. Current operator guidance is `AGENTS.md` + `EC2_APP_RUNTIME_QUICK_REFERENCE.md` + this index.

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
- Historical BATCH proofs, runtime validations, migration reports, and team-chat dumps may still contain pre-EC2 `localhost:*` examples. They are not current runtime instructions.
