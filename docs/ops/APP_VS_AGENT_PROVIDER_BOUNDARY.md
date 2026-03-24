---
status: active
last_verified: 2026-03-13
---

# App vs agent provider boundary

## Canonical split
- App plane:
  - `g4f` is app-only.
  - app failures surface under `app_providers`.
- Agent plane:
  - `codex exec` is primary.
  - `qwen cli` is fallback for agents only.
  - provider policy lives only behind `ModelInvocationPort`.
- Planning plane:
  - Plane OSS is the canonical backlog system.
  - official Plane MCP is the canonical agent interface for backlog operations.
  - Plane is not a provider backend.
- Runtime plane:
  - LangGraph + SQLite are the execution truth.
  - `planner` is the only scheduler.
- Operator plane:
  - OpenClaw + systemd supervise operator services and persistent agents.

## Current implementation reality
- The doctrinal provider split is already coherent.
- The remaining work is to remove fallback logic and bridge behavior that still leaks outside the model plane or planner runtime boundaries.

## Hard rules
- No provider fallback policy outside `model_plane.py` and `codex_cli_adapter.py`.
- `g4f` must never become an agent fallback.
- `qwen cli` must never become an app provider.
- No custom backlog wrapper becomes canonical while Plane MCP covers the need.
- Queue, workboard, and docs are never planning truth.
- Active runners must treat Plane sync as planning truth and SQLite or planner graph as runtime truth; markdown backlog docs are reference only.

## Required status surfaces
- `app_providers`
- `agent_providers`
- `plane_planning`
- `openclaw_gateway`
- `worker_orphan_count`

## Required `ModelInvocationPort` fields
- `invocation_id`
- `idempotency_key`
- `backend_requested`
- `backend_used`
- `fallback_reason`
- `invocation_status`
- `heartbeat_ts`
- `provider_plane=agent`
