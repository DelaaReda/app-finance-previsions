---
status: active
last_verified: 2026-03-13
---

# Monitor architecture spec

## Purpose
The monitor exposes canonical health and runtime business signals without reintroducing planning logic.

## Canonical observability split
- Monitor = business health, proofs, bottlenecks, execution signals
- OpenTelemetry = technical telemetry standard
- Phoenix = optional LLM or agent tracing layer if needed
- OpenClaw doctor or status = operator health source

## Current implementation reality
- The durable runtime reader and event-store-first patterns already exist.
- Too many active monitor or doctor paths still depend directly on compatibility projections or legacy registries.
- The migration is complete only when SQLite or runtime truth reading remains authoritative even if a projection is stale or corrupted.

## Required health surfaces
- Runtime:
  - SQLite connectivity
  - event store health
  - planner graph health
  - dispatch or merge recovery signals
- Planning:
  - Plane webhook freshness
  - Plane API or MCP reachability
  - reconciliation lag
  - `plane_planning` status
- Providers:
  - `app_providers`
  - `agent_providers`
- Operator plane:
  - OpenClaw `doctor/status/health/models status`
  - `openclaw_gateway`
- Worker hygiene:
  - `worker_orphan_count`
  - TTL cleanup visibility

## Monitoring rules
- App provider failures must not degrade agent provider status unless a true shared dependency is broken.
- Agent fallback from Codex to Qwen must be visible under agent telemetry only.
- Plane planning failures must not be hidden inside generic runtime status.
- Proofs remain in repo or runtime storage; Plane receives links, comments, and worklogs only.

## What the monitor must not do
- create backlog
- invent runtime work outside imported Plane state
- turn compatibility projections into primary truth
