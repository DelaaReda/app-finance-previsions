---
status: active_supporting_doc
last_verified: 2026-03-13
---

# Product planning

Plane OSS is the canonical front-door for creating and prioritizing planning objects for Finance Copilot.

## Current implementation reality
- The backlog cutover is doctrinally done.
- The technical cutover is still being completed through the runtime sync path.
- This directory must stay reference-only for backlog creation even while runtime bridge removal continues.

## Canonical mapping
- Initiative = strategic stream
- Epic = product or architecture epic
- Module = executable batch named `BATCH-xx`
- Work item = executable unit inside the batch

## Required runtime metadata on Plane work items
- `runtime_task_id`
- `runtime_role`
- `runtime_kind`

## Rules after cutover
- Do not create new epics, batches, or tasks in repo docs.
- Agents must use the official Plane MCP server for backlog operations.
- Plane webhooks are the intended primary sync flow into runtime.
- This directory is reference, execution notes, exports, and compatibility material only.
- Runtime truth remains LangGraph + SQLite, not Plane.
- Historical planning material lives in [archive/README.md](./archive/README.md).
- Supporting matrices and blueprints live in [reference/README.md](./reference/README.md).

## Canonical references
- [../../ops/PLANE_BACKLOG_INTEGRATION_SPEC.md](../../ops/PLANE_BACKLOG_INTEGRATION_SPEC.md)
- [../../ops/CANONICAL_RUNTIME_MODE.md](../../ops/CANONICAL_RUNTIME_MODE.md)
- [../../ops/LANGGRAPH_PYDANTICAI_ORCHESTRATION_TARGET.md](../../ops/LANGGRAPH_PYDANTICAI_ORCHESTRATION_TARGET.md)
