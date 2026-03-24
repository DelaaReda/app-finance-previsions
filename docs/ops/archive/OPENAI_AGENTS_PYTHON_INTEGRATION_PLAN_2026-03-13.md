---
status: archived
last_verified: 2026-03-13
superseded_by:
  - /home/venom/analyse-financiere/docs/ops/CANONICAL_RUNTIME_MODE.md
  - /home/venom/analyse-financiere/docs/ops/ADR_LANGGRAPH_PYDANTIC_RUNTIME_MIGRATION_2026-03-13.md
---

# OpenAI Agents Python Integration Plan

Status: archived
superseded_by: `docs/ops/CANONICAL_RUNTIME_MODE.md`
reason: superseded architecture; second backbone not canonical

Historical status:
- superseded by `docs/ops/CANONICAL_RUNTIME_MODE.md`
- superseded by `docs/ops/ADR_LANGGRAPH_PYDANTIC_RUNTIME_MIGRATION_2026-03-13.md`
- keep for archive context only

Status note:

- historical / superseded-by `docs/ops/CANONICAL_RUNTIME_MODE.md`
- not an active backbone plan

Date: 2026-03-13
Owner: planner
Status: deprecated-as-primary-runtime

## Decision

This document is kept for historical context only.

Primary orchestration direction has changed to:

- `LangGraph` as durable planner runtime
- typed contracts via `Pydantic` / `PydanticAI`-style models
- current `codex exec` / OpenClaw model plane preserved

See:

- `docs/ops/CANONICAL_RUNTIME_MODE.md`
- `docs/ops/LANGGRAPH_PYDANTICAI_ORCHESTRATION_TARGET.md`
`openai-agents-python` is no longer the preferred backbone, even as a bounded execution layer, because the main maintenance problem is control-plane durability rather than agent prompting ergonomics.

Keep the current project runtime as the canonical layer for:
- queue and workboard persistence
- batch and cycle sequencing
- planner proof contracts
- docs and memory projection
- reconciliation and repair

Use the Agents SDK only for:
- bounded worker execution
- typed tools
- structured outputs
- local handoffs inside one worker run
- optional tracing for worker runs

## Why this shape

The official SDK exposes a small set of primitives centered on `Agent`, `Runner`, function tools, handoffs, context objects, and structured outputs. That maps well to worker execution, but not to this repository's runtime governance model.

Official references:
- https://github.com/openai/openai-agents-python
- https://openai.github.io/openai-agents-python/
- https://openai.github.io/openai-agents-python/agents/
- https://openai.github.io/openai-agents-python/running_agents/
- https://openai.github.io/openai-agents-python/handoffs/

## Non-goals

- do not replace `parallel-workstreams.json`
- do not replace `priority-queue.json`
- do not replace the planner role runner
- do not move project memory into SDK sessions
- do not bypass the existing planner proof fields

## First integration target

Use a bounded worker around the brief-generation flow.

Current anchor files:
- `apps/api/src/domains/forecasts/api/brief.py`
- `apps/api/src/platform/legacy/jobs/market_brief.py`

Recommended first worker:
- `market_brief_worker`

Reason:
- structured input and output already exist
- planner already tracks this area through proof fields
- limited blast radius

## Repo insertion points

New package:
- `platform/agents_sdk/`

Purpose of each file:
- `availability.py`: lazy import gate for `openai-agents`
- `context.py`: canonical run context passed through one worker run
- `schemas.py`: structured request and evidence payloads
- `tools.py`: project-specific SDK tool builders
- `adapters/workboard_adapter.py`: task-to-request and result-to-evidence mapping
- `runners/market_brief_worker.py`: example worker using `Agent`, `Runner`, `handoff`

## Runtime integration model

1. Planner runtime selects a READY task from the canonical workboard.
2. Existing planner bridge or worker launcher builds a `WorkerRunRequest`.
3. `platform/agents_sdk/adapters/workboard_adapter.py` maps the task to SDK input.
4. A bounded SDK worker runs locally.
5. SDK final output is normalized into canonical planner evidence.
6. Existing runtime writes evidence back to the workboard and docs.

## Canonical evidence contract

Every SDK worker should end by producing a payload compatible with current planner expectations:

- `summary`
- `planner_artifact`
- `root_cause`
- `fix_applied`
- `verify`
- `reuse_check`
- `tests_run`
- `cmd`
- `files_touched`
- `architecture_check`
- `vision_alignment`
- `recommended_next`
- `blocking_issue`

Formatting constraints:
- `verify=before=<...>; after=<...>; test=<...>`
- `architecture_check=layer=<...>; imports_ok=<yes|no>; path_target=<...>`
- `vision_alignment=batch=<BATCH-XX>; target=<...>; impact=<...>`

## Rollout phases

### Phase 1

Scaffold only.

Deliver:
- package skeleton
- lazy dependency gate
- request and evidence schemas
- example market brief runner

### Phase 2

Wire one worker behind the current runtime.

Deliver:
- one launcher command
- one task-to-request adapter
- one result-to-workboard adapter

### Phase 3

Add bounded handoffs inside the worker.

Example:
- brief manager agent
- risk prioritization agent
- synthesis agent

### Phase 4

Optional tracing and evaluation on the worker path only.

## Constraints observed in this repo

- no root Python dependency manifest was discovered during this pass
- therefore the scaffold is import-safe but does not hard-wire installation
- all SDK imports are lazy so the new package is inert until explicitly used

## Next branchable step

Wire a dedicated launcher that takes a planner task node and executes:

`market_brief_worker(request_from_workboard_task(task))`

without changing the planner scheduler itself.
