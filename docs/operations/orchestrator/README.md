---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md
  - /home/venom/analyse-financiere/docs/ops/AGENT_WORKSPACE_INDEX.md
---

# Orchestrator Archive Boundary

This directory is not a single clean source of truth.

It currently contains three different classes of material:
- historical plans and checklists
- human-facing evidence and archived proofs
- runtime-generated artifacts still kept for compatibility and observability

## Do not assume everything here is canonical
For current implementation and operations, start with:
- [CURRENT_ARCHITECTURE_ENTRYPOINTS.md](/home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md)
- [AGENT_WORKSPACE_INDEX.md](/home/venom/analyse-financiere/docs/ops/AGENT_WORKSPACE_INDEX.md)

## Current boundary
### Canonical mutable runtime state
- `logs-codex-runs/orchestrator-state/`

### Compatibility-read runtime artifacts still visible here
- `priority-queue.json`
- `parallel-workstreams.json`
- `executors-monitoring-latest.json`
- planner/runtime event logs and registries

### Historical evidence
- dated plans, cutover checklists, archived proofs, and workstate notes

## Operator rule
- Read from this directory only when a canonical doc explicitly points here.
- Do not treat a runtime-generated JSON or dated checklist here as current policy by default.
