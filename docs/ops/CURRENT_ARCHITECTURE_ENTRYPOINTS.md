---
status: canonical
last_verified: 2026-03-06
canonical_replaces:
  - docs/operations/README.md
---

# Current Architecture Entrypoints

Read these first. Ignore historical reports unless you are debugging a past incident.

## Canonical docs
- Workspace and path rules: [AGENT_WORKSPACE_INDEX.md](/home/venom/analyse-financiere/docs/ops/AGENT_WORKSPACE_INDEX.md)
- Target runtime architecture: [PLANNER_ORCHESTRATOR_TARGET_SPEC.md](/home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md)
- Execution order: [PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md)
- Monitor/runtime behavior: [MONITOR_ARCHITECTURE_SPEC.md](/home/venom/analyse-financiere/docs/ops/MONITOR_ARCHITECTURE_SPEC.md)

## Canonical code entrypoints
- Runner config: [runner.v1.yaml](/home/venom/analyse-financiere/platform/config/runner/runner.v1.yaml)
- Runtime state/path helper: [orchestrator_paths.py](/home/venom/analyse-financiere/platform/automation/orchestrator_paths.py)
- Planner bridge: [planner_subagent_manager.py](/home/venom/analyse-financiere/platform/automation/planner_subagent_manager.py)
- Pre-tick reconciliation: [state_reconciler.py](/home/venom/analyse-financiere/platform/automation/state_reconciler.py)
- Delivery gate: [delivery_value_gate.py](/home/venom/analyse-financiere/platform/automation/delivery_value_gate.py)
- Product guard: [product_priority_guard.py](/home/venom/analyse-financiere/platform/automation/product_priority_guard.py)
- Monitor API: [server.py](/home/venom/analyse-financiere/apps/monitor/server.py)
- Doctor CLI: [fc_doctor.py](/home/venom/analyse-financiere/platform/automation/fc_doctor.py)

## Historical docs
- Anything under `docs/operations/` that is an incident log, worklog, batch report, or migration diary is historical unless a canonical doc points to it explicitly.
- `docs/orchestrator-ops/` is compatibility/historical.
