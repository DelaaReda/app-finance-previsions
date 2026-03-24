---
status: active
last_verified: 2026-03-13
---

# LangGraph orchestration target

## Target split
- Plane OSS creates and prioritizes backlog.
- LangGraph + SQLite execute imported work.
- Queue, workboard, and repo planning files remain derived projections or references.

## Current implementation reality
- The durable runtime is already present in `platform/automation/runtime/` and `platform/automation/planning/plane/`.
- `platform/automation/planning/plane/plane_runtime_sync.py`, `platform/automation/runtime/truth/runtime_truth_reader.py`, planner graph runtime, and event-store-first paths already exist.
- The migration is incomplete until runtime and monitor read or write primarily through these paths rather than through compatibility registries and projections.

## Canonical entity mapping
- Initiative = strategic stream
- Epic = canonical backlog slice or large architecture program
- Module = executable batch named `BATCH-xx`
- Work item = executable task inside the batch

## Required runtime metadata
- `runtime_task_id`
- `runtime_role`
- `runtime_kind`

## Required imported planning fields
- `plane_workspace_slug`
- `plane_project_id`
- `plane_module_id`
- `plane_work_item_id`
- `plane_work_item_identifier`
- `planning_source=plane`

## Sync contract
- Plane webhooks drive the intended primary import path.
- API reconciliation polling exists for catch-up only.
- Runtime writes canonical state to SQLite and event state.
- Compatibility files are projected from runtime state only.

## Planner and runtime rules
- `planner` reads imported runtime state, not Markdown backlog docs.
- crash recovery resumes from SQLite or event state without double mutation.
- `planner_subagent_manager.py` is a capability runner, not the orchestration brain.
- `parallel_workstream.py` may mutate projections after runtime decisions, but it must not originate new planning.
