# Orchestration Reliability Specification

## Purpose
Define reliability guarantees for the current orchestration model:
- one scheduled orchestrator lane: `planner`
- business responsibility domains preserved under planner control
- runtime truth and delivery truth enforced by application code

## Target Topology
- `planner` is the only scheduled orchestrator lane in target mode
- `dev`, `admin`, and `scrum_master` remain explicit responsibility domains under planner ownership
- OpenClaw provides runtime/session transport
- Codex provides specialized bounded execution

This specification replaces older multi-lane target assumptions.

## Normative Rules

### Scheduling
- Target runtime **MUST** use planner-only scheduling.
- Legacy multi-lane cron profiles **MUST** be treated as compatibility or rollback modes.

### Runtime Truth
- Pre-tick reconciliation **MUST** run before planner execution.
- stale runtime blockers **MUST** clear automatically when probes recover
- stale/orphan locks **MUST** be cleaned
- queue/workboard contradictions **MUST** be surfaced and repaired idempotently

### Delivery Truth
- no task **MUST** complete without delivery proof
- code/config/runtime/product-logic completion **MUST** require a valid `commit_sha`
- false DONE inflation **MUST** be detectable

### Authority Boundaries
- workers/subagents **MUST** return results, not final business truth
- planner **MUST** remain authoritative for final orchestration mutation
- `admin` capability **MUST NOT** become backlog owner
- `scrum` capability **MUST NOT** become a delivery owner

### Product Priority
- product-value degradation **MUST** be visible
- orchestration-only work **MUST NOT** dominate when P0 product behavior is broken

## Core Reliability Modules

### `state_reconciler.py`
Purpose:
- repair runtime truth before planner execution

Required outcomes:
- parked/in-progress contradiction fixed
- stale runtime blockers cleared
- stale locks removed
- stalled in-progress surfaced
- READY starvation surfaced

### `delivery_value_gate.py`
Purpose:
- block weak completion

Required outcomes:
- proof required for completion
- commit required where applicable
- failures downgraded cleanly instead of silently accepted

### `planner_subagent_manager.py`
Purpose:
- thin delegation bridge under planner authority

Allowed actions:
- `plan`
- `run`
- `collect`
- `cleanup`

Not allowed:
- second orchestration state machine
- independent worker ownership of final task status

### `product_priority_guard.py`
Purpose:
- preserve delivery effort for real product value

## Interfaces
Primary checks:
- `/api/status`
- `/api/doctor`
- `bash scripts/fc_doctor.sh --json`
- planner contracts and planner subagent registry/events

Canonical orchestrator sources:
- `docs/operations/orchestrator/priority-queue.json`
- `docs/operations/orchestrator/parallel-workstreams.json`

## Runtime Behavior

### Target mode
- `planner-experimental` is the target mode
- health and readiness derive from planner plus runtime/provider integrity
- capability outputs from dev/admin/scrum are consumed through planner-owned delegation

### Compatibility mode
- legacy multi-lane scheduling may still run for rollback or diagnostics
- it is not the target architecture

## Operator Commands
```bash
bash scripts/fc_setup_crons.sh --profile planner-experimental
bash scripts/fc_doctor.sh --json
curl -s http://127.0.0.1:7779/api/status | jq '{health,execution_mode,core_roles}'
python3 -m pytest -q \
  platform/automation/tests/test_state_reconciler.py \
  platform/automation/tests/test_delivery_value_gate.py \
  platform/automation/tests/test_planner_subagent_manager.py \
  platform/automation/tests/test_fc_doctor.py
```

## Rollback
Default rollback path:
1. disable planner delegation if needed
2. keep planner scheduled
3. keep reconciler active
4. downgrade delivery gate from enforce to warn-only only if strictly necessary

Escalated rollback:
- restore compatibility multi-lane scheduling manually via cron profile switch

## Acceptance Criteria
- planner-only runtime stays healthy
- runtime truth is repaired automatically
- delivery truth is enforced
- planner-owned delegation stays thin and observable
- product-priority protections prevent orchestration drift
