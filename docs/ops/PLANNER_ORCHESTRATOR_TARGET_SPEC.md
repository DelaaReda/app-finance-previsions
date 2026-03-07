---
status: canonical
last_verified: 2026-03-06
canonical_replaces:
  - docs/ops/PLANNER_MONO_LANE_CUTOVER_RUNBOOK.md
---

# Planner Orchestrator Target Spec

## Purpose
This document is the implementation directive for the current repository state.

The repository is already in planner-only scheduling mode.
This base must be preserved.

The target is not:
- a return to four full cron lanes
- a flat planner-only runtime with no business-role distinction

The target is:
- one scheduled orchestrator: `planner`
- explicit business responsibility domains preserved under planner authority
- OpenClaw used for runtime/session/transport
- Codex multi-agent used for specialized bounded execution
- application code kept as source of truth for runtime state, delivery truth, and product priorities

## Current Truth Of The Repo
- scheduling is already planner-only in target mode
- `planner` is the only scheduled runtime lane when planner orchestrator mode is enabled
- `planner_architect_orchestrator` is accepted only as a compatibility alias
- `dev`, `admin`, and `scrum_master` are no longer required as independent scheduled cron lanes in target mode
- pre-tick runtime reconciliation already exists
- delivery gating already exists
- planner-owned delegation already exists and must remain thin
- live planner delegation transport is `openclaw`

Canonical implementation anchors:
- `platform/config/runner/runner.v1.yaml`
- `scripts/fc_setup_crons.sh`
- `platform/automation/planner_subagent_manager.py`
- `platform/automation/orchestrator_paths.py`
- `platform/automation/state_reconciler.py`
- `platform/automation/delivery_value_gate.py`
- `apps/monitor/server.py`
- `platform/automation/fc_doctor.py`

## Runtime State Boundary
- Mutable orchestration runtime state must write first to `logs-codex-runs/orchestrator-state/`.
- `docs/operations/orchestrator` is a compatibility-read and evidence/documentation space during migration.
- Queue/workboard readers must resolve paths through `platform/automation/orchestrator_paths.py`, not hard-coded docs paths.
- Operator pause/maintenance state must be stored in `logs-codex-runs/orchestrator-state/runtime-state.json` and surfaced consistently in monitor and doctor.

## Target Architecture

```text
scheduler cron
    ↓
planner (canonical single scheduled orchestrator)
    ↓
capabilities:
  dev
  admin
  scrum_master
    ↓
OpenClaw runtime/session transport
    ↓
Codex multi-agent execution
```

### Scheduling Rule
- `planner` is the only scheduled orchestrator lane
- `planner_architect_orchestrator` may remain as compatibility alias only
- `dev`, `admin`, and `scrum_master` are capabilities under planner authority, not target cron lanes

### Runtime / Compute Split
- application code is authoritative for:
  - queue/workboard state
  - guards
  - delivery truth
  - product-priority policy
- OpenClaw is authoritative for:
  - runtime sessions
  - transport
  - agent lifecycle where needed
- Codex is authoritative for:
  - bounded specialized execution
  - parallel delegated work
  - isolated reasoning/execution contexts

### Worker Rule
- a worker returns a result
- the parent keeps authority
- no worker directly completes a business task
- no worker directly mutates final orchestration truth

## Responsibilities Mapping

### Planner
Responsibilities:
- product vision alignment
- backlog prioritization
- batch creation
- task framing
- dependency resolution
- delivery gating
- worker/subagent dispatch
- merge worker results
- final decision authority

Planner:
- decides
- plans
- delegates
- merges results
- validates delivery

Planner may use:
- Codex multi-agent
- OpenClaw runtime agents

### Dev Capability
Responsibilities:
- task validation
- code patch
- config patch
- tests execution
- verification
- commit
- delivery completion proposal

Mandatory flow:
- claim
- patch
- test
- commit
- verify
- complete

Required completion evidence:
- `root_cause`
- `fix_applied`
- `verify`
- `artifact`
- `tests_run`
- `commit_sha`
- `files_touched`
- `architecture_check`
- `vision_alignment`

Dev capability does not own final orchestration truth.
It returns evidence and a proposed next action to planner.

### Admin Capability
Responsibilities:
- runtime truth
- stale lock cleanup
- stale blocker cleanup
- session repair
- queue/workboard reconciliation
- infra repair
- takeover execution support

Admin corrects:
- `runtime_down`
- stale locks
- stale sessions
- state inconsistencies

Admin capability must not reprioritize product backlog.

### Scrum Master Capability
Responsibilities:
- detect READY starvation
- detect stalled tasks
- detect contract blockers
- trigger claim pressure
- send unblock actions
- escalate to admin when needed
- measure unblock success

Scrum capability must not:
- spawn autonomous business ownership
- complete tasks
- change backlog priority
- mutate final runtime truth directly

## Mandatory Modules

### `platform/automation/state_reconciler.py`
Purpose:
- pre-tick runtime truth repair

Required behavior:
- fix `parked_by_rebuild + IN_PROGRESS`
- clear stale `runtime_down` blockers when probes are healthy
- remove stale/orphan locks
- mark stalled `IN_PROGRESS`
- detect READY starvation

Rule:
- always run before planner execution
- remain idempotent

### `platform/automation/delivery_value_gate.py`
Purpose:
- block false completion

Required behavior:
- block completion when required proof is missing
- require `commit_sha` for code/config/runtime/product-logic work
- require:
  - `verify`
  - `artifact`
  - `tests_run`
  - `files_touched`
  - `architecture_check`
  - `vision_alignment`

Failure behavior:
- downgrade to `REVIEW` or `BLOCKED`
- emit `delivery_value_insufficient`

### `platform/automation/product_priority_guard.py`
Purpose:
- prevent orchestration work from dominating when product value is degraded

Planner must verify:
- copilot usability
- forecast validity
- data freshness
- product-vs-orchestration work ratio

Rule:
- planner must not proliferate orchestration-only work when product P0 is broken without explicit justification

### Thin Worker Bridge
Preferred canonical implementation:
- extend `platform/automation/planner_subagent_manager.py`

If a dedicated `worker_manager.py` exists, it must remain a thin façade only.

Allowed responsibilities:
- `plan`
- `run`
- `collect`
- `cleanup`

Not allowed:
- second orchestration platform
- independent worker authority over business state
- permanent shadow lanes outside planner control

Bridge contract:
- planner requests bounded work
- OpenClaw handles runtime/session transport
- Codex executes specialized task
- structured result comes back
- planner merges it into authoritative app state

## Model Policy
- model choice is config-driven
- model names must not be hard-coded in orchestration logic
- strongest model class reserved for planner/orchestration/vision-critical decisions
- strong model class reserved for delivery work
- lighter model class reserved for coordination, scans, and bounded diagnostics

Canonical config location:
- `platform/config/runner/runner.v1.yaml`

Project Codex configuration should prefer:
- `.codex/config.toml`

The architecture must not depend on a specific marketing model name.

## Monitor Requirements
Monitor must expose and keep coherent:
- `execution_mode`
- `core_roles`
- `planner_subagents`
- `delivery_integrity`
- `product_value_metrics`

Target monitor panels:
- dynamic workers / planner subagents
- delivery value
- runtime reconciliation

## Execution Order

### Commit 1
`feat(orchestration): harden state reconciler`

Scope:
- strengthen `state_reconciler.py`
- keep planner-only runtime stable

### Commit 2
`feat(delivery): harden delivery value gate`

Scope:
- strengthen `delivery_value_gate.py`
- enforce proof-first completion

### Commit 3
`feat(orchestration): add product priority guard`

Scope:
- add `product_priority_guard.py`
- wire product-value checks into doctor/monitor

### Commit 4
`feat(runtime): harden thin planner bridge for OpenClaw/Codex`

Scope:
- strengthen planner-owned delegation
- keep lifecycle minimal and observable

### Commit 5
`feat(monitor): expose planner delegation and delivery metrics`

Scope:
- expose worker/subagent visibility
- expose delivery/product signals

## Rollback
Preferred rollback path keeps planner-only scheduling intact.

Order:
1. disable planner delegation if needed
2. keep `planner` as sole scheduled lane
3. switch thin bridge to no-op or dry mode if needed
4. downgrade delivery gate from `enforce` to `warn-only` only if strictly necessary
5. keep `state_reconciler` active
6. keep product-priority protections active where safe

Escalated rollback:
- restoring legacy multi-lane cron scheduling is a manual incident action, not the default rollback path

## Explicitly Out Of Scope
- returning to four full independent cron lanes as the target architecture
- planner-only minimalism that erases `dev/admin/scrum_master` responsibility domains
- building a large worker platform that recreates Codex/OpenClaw
- allowing workers/subagents to mutate final backlog/workboard truth directly
- silent fallback that replaces planner or delivery authority

## Final Result Expected
After implementation:
- planner orchestrates everything
- dev capability produces real delivery evidence
- admin capability guarantees runtime truth
- scrum capability maintains flow pressure
- Codex executes specialized subagents
- OpenClaw handles runtime/session transport

Absolute priorities:
- delivery quality
- runtime coherence
- reduction of orchestration noise
