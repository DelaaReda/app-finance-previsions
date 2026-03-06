# Planner Orchestrator Execution Batches

## Purpose
Define the implementation batches for the current target architecture.

Canonical architecture source:
- `docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md`

Current target:
- planner-only scheduling
- explicit capabilities under planner: `dev`, `admin`, `scrum_master`
- app keeps orchestration truth
- OpenClaw provides runtime/session transport
- Codex provides specialized execution

## Batch 1 — Runtime Truth
Commit:
- `feat(orchestration): harden state reconciler`

Priority:
- P0

Scope:
- harden `platform/automation/state_reconciler.py`
- keep pre-tick repair mandatory
- ensure planner-only runtime remains stable

Acceptance:
- stale runtime blockers clear on healthy probes
- stale/orphan locks are removed
- parked/in-progress contradictions are repaired
- READY starvation is surfaced

## Batch 2 — Delivery Truth
Commit:
- `feat(delivery): harden delivery value gate`

Priority:
- P0

Scope:
- harden `platform/automation/delivery_value_gate.py`
- enforce proof-first completion
- keep commit requirement for code/config/runtime/product logic

Acceptance:
- no false complete without required proof
- weak completion is downgraded or blocked
- DONE inflation is detectable

## Batch 3 — Product Priority Guard
Commit:
- `feat(orchestration): add product priority guard`

Priority:
- P0

Scope:
- add `platform/automation/product_priority_guard.py`
- expose product-value metrics in doctor/monitor
- prevent orchestration-only batch inflation when product P0 is degraded

Acceptance:
- product-vs-orchestration ratio visible
- copilot/freshness/forecast validity signals visible
- planner cannot keep generating maintenance-only work without explicit justification

## Batch 4 — Thin Planner Bridge
Commit:
- `feat(runtime): harden thin planner bridge for OpenClaw/Codex`

Priority:
- P1

Scope:
- harden `platform/automation/planner_subagent_manager.py`
- keep delegation minimal: `plan`, `run`, `collect`, `cleanup`
- connect planner-owned delegation cleanly to OpenClaw/Codex

Acceptance:
- planner can delegate bounded work to `dev/admin/scrum_master` capabilities
- results are structured and mergeable
- workers/subagents never own final business truth

## Batch 5 — Capability Contracts And Monitor
Commit:
- `feat(monitor): expose planner delegation and delivery metrics`

Priority:
- P1

Scope:
- clarify planner/dev/admin/scrum capability responsibilities in prompts/config
- require structured evidence from capability outputs
- expose:
  - `execution_mode`
  - `core_roles`
  - `planner_subagents`
  - `delivery_integrity`
  - `product_value_metrics`

Acceptance:
- planner receives actionable outputs, not narrative noise
- monitor reflects target runtime truth
- capability outputs map cleanly to orchestration decisions

## Explicit Non-Goals
- reintroducing four fully independent target cron lanes
- building a large custom worker platform
- allowing workers/subagents to complete business tasks autonomously
- freezing marketing model names in architecture logic

## Rollback
Default rollback path:
1. keep planner-only scheduling
2. disable delegation if needed
3. keep reconciler active
4. relax delivery gate only temporarily if required

Escalated rollback:
- switch cron profile only as an incident or compatibility action
