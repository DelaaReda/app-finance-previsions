---
status: active
last_verified: 2026-03-13
---

# Canonical runtime mode

## Canonical operating model
- Plane OSS = planning front-door
- official Plane MCP + Plane webhooks = backlog interface and sync intake
- LangGraph + SQLite = runtime truth
- OpenClaw + systemd = operator plane
- codex exec = primary agent execution
- qwen cli = fallback for agents only
- g4f = app only
- public app-serving runtime = EC2 Ubuntu (`http://3.98.20.77`, `http://ec2-3-98-20-77.ca-central-1.compute.amazonaws.com`)

## Current implementation reality
- The durable runtime already exists around LangGraph, SQLite, event store, runtime truth reading, planner graph runtime, and model plane.
- Active Python imports no longer depend on the removed legacy shim paths under `platform/automation/orchestration_runtime/`.
- Active runtime scripts now read execution state from `logs-codex-runs/orchestrator-state` first.
- Legacy registries and JSON projections still exist, but they are now compatibility or diagnostics surfaces rather than primary runtime truth.
- The local VM is no longer the canonical app-serving host.
- Backend, frontend, and public endpoint validation must run against the EC2 public runtime, not local VM listeners.
- Local VM remains the orchestration and operator workspace only.
- Current validated behavior on 2026-03-13:
  - targeted runtime pytest suite passes
  - `./finance-copilot.sh gate` passes
  - monitor, critical endpoint, doctor, and runtime e2e gates pass
  - `fc_doctor` may still report a global `degraded` status when non-runtime checks such as `plane_planning` are unconfigured; this does not imply runtime truth failure

## Truth boundaries
- Planning truth:
  - Plane workspace, project, modules, and work items
- Runtime truth:
  - SQLite state, event store, graph state, planner dispatch and merge lifecycle
- Compatibility projections:
  - `logs-codex-runs/orchestrator-state/*`
  - `priority-queue.json`
  - `parallel-workstreams.json`
  - workboards and status views
  - legacy registries kept for transition only
- Reference and history:
  - repo planning docs, scrum docs, tasks hub, archived runbooks
  - `docs/operations/**`

## Mandatory rules
- Create and prioritize backlog in Plane, not in repo docs.
- Agents use the official Plane MCP server for backlog read or write.
- Active scripts and prompts must source backlog truth from Plane sync and execution truth from SQLite or planner graph, never from `docs/product/planning/tasks.md`, `stories.md`, `epics.md`, or `docs/planning/*`.
- Active code must not read or write `docs/orchestrator-ops/*`; that tree is removed from the live runtime path.
- On the local VM, do not start or rely on backend/frontend/monitor listeners for normal operation.
- All manual API usage, smoke checks, and frontend validation from the repo workspace must target the public EC2 endpoints.
- Planner runtime must import planned work from Plane into SQLite first, then derive compatibility projections from runtime state.
- Runtime may send comments, proof links, worklogs, and useful state changes back to Plane.
- Runtime must never create a second planning hierarchy outside Plane.

## Bridge removal priorities
- make `plane_runtime_sync.py` the real sync path into runtime truth
- make `runtime_truth_reader.py` the main read path for monitor and doctor
- demote legacy JSON or JSONL registries to compatibility or diagnostics only
- keep planner graph write-primary
- reduce `parallel_workstream.py` to projection or controlled mutation
- keep `finance-copilot.sh start` independent from Plane and OpenClaw health during the cutover
- keep `docs/operations/orchestrator/*` limited to proofs, storage, and compatibility projection, never as runtime truth

## Runtime engine rules
- `planner` remains the only scheduler.
- planner graph is write-primary.
- `planner_subagent_manager.py` is a capability executor, not a global orchestrator.
- `parallel_workstream.py` is a projection or controlled mutation helper, not a source of planning decisions.
