---
status: active
last_verified: 2026-03-13
---

# Plane backlog integration spec

## Decision
Plane OSS is the canonical planning system for Finance Copilot.

## Current state
- Plane is the documented front-door.
- A Plane runtime adapter already exists in `platform/automation/planning/plane/plane_runtime_sync.py`.
- A runtime truth reader already exists in `platform/automation/runtime/truth/runtime_truth_reader.py`.
- The migration is not complete until webhook-driven sync is the live primary path into SQLite or event state.
- Backlog docs are already demoted to reference or history.
- Plane webhook intake is now exposed at `/api/planning/plane/webhook` and routes into `platform/automation/planning/plane/plane_runtime_sync.py`.
- Current runtime behavior allows `plane_planning` to remain `unknown` or `degraded` without blocking app runtime startup or runtime truth health.

## Canonical stack
- Plane OSS self-hosted
- official Plane MCP server
- Plane REST API
- Plane webhooks

## API compatibility rule
- Reconciliation must prefer Plane `work-items` endpoints.
- Legacy `module-issues` endpoints are compatibility fallback only during cutover.

## What Plane owns
- initiative creation
- epic creation
- module creation
- work item creation
- prioritization and planning state transitions

## Canonical entity mapping
- Initiative = strategic stream
- Epic = product or architecture epic
- Module = executable batch named `BATCH-xx`
- Work item = executable task named from `runtime_task_id`

## Required work item metadata
- `runtime_task_id`
- `runtime_role`
- `runtime_kind`

## Cutover target
- Primary path:
  - Plane webhook -> `platform/automation/planning/plane/plane_runtime_sync.py` -> SQLite or event state -> runtime projections
- Backup path:
  - `platform/automation/planning/plane/plane_runtime_sync.py --reconcile-api` using Plane REST API
- Preferred read path after cutover:
  - `runtime_truth_reader.py` -> SQLite or event state -> projection fallback only if needed
- Forbidden end state:
  - dual-write Plane + docs + queue
  - repo docs used as canonical backlog creation surfaces

## Rules
- Do not create new batches or tasks in repo docs.
- Do not maintain a second backlog hierarchy in queue files or planner prompts.
- Do not add a custom backlog UI or custom wrapper while Plane + official MCP cover the workflow.
- The only allowed custom planning code in phase 1 is the minimal business mapping from Plane objects to runtime identifiers and runtime import logic.
- Validate `X-Plane-Signature` when a Plane webhook secret is configured.
- Do not add a second reconciliation script outside `platform/automation/planning/plane/plane_runtime_sync.py`; fallback reconciliation stays in the same bridge module.
- Inside `platform/automation/planning/plane/plane_runtime_sync.py`, treat `ingest_plane_payload()` and `reconcile_from_plane_api()` as the only sync entrypoints; file-driven imports must route through the same ingestion path instead of applying projections directly.
- Active prompts and scripts must never present `docs/product/planning/tasks.md`, `stories.md`, `epics.md`, or `docs/planning/*` as canonical backlog sources.
- Plane unavailability degrades planning only; it must not block `finance-copilot.sh start`, runtime truth reading, or monitor startup.

## Runtime fields required after import
- `plane_workspace_slug`
- `plane_project_id`
- `plane_module_id`
- `plane_work_item_id`
- `plane_work_item_identifier`
- `planning_source=plane`
