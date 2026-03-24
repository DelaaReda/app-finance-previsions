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
- SQLite or event-store-backed runtime truth **MUST** be read before any compatibility registry or projection.
- legacy registries **MUST NOT** reconstruct the primary runtime state when `event_store_primary=true`.
- active capability rows with `owner_task_id` outside the target responsibility domain **MUST** be ignored as blockers and quarantined as routing drift.
- planner dispatch and recovery **MUST** bind to the canonical active cycle from queue/workboard runtime truth; stale capability rows from older cycles **MUST NOT** reactivate an old stream or block the current one.
- planner autonomy **MUST NOT** mint or autobatch a fresh batch while canonical `active_cycle.active_batch_ids` is non-empty; if the current cycle is pinned but no lane can run, the planner lane **MUST** surface an explicit blocker on the pinned cycle instead of bypassing it with a side batch.
- planner-owned `complete` actions **MUST** backfill the minimum delivery proof fields (`root_cause`, `fix_applied`, `verify`, `architecture_check`, `vision_alignment`) from canonical task context when the CLI call omits them; a planner closure **MUST NOT** fail only because the lane forgot to restate metadata already inferable from the live task.

### Session Freshness and Resume
- tmux/Codex role sessions **MUST NOT** be resumed blindly across runtime, prompt, or workspace drift.
- auto lanes **MUST** execute from `/home/venom/analyse-financiere`; foreign or deleted workdirs **MUST NOT** count as ready runtime root
- `codex exec resume` **MUST** be gated by a freshness guard that invalidates stale session state when:
  - the role/workspace/model/prompt fingerprint changes
  - the stored session exceeds the allowed max age
- VM resume handling **MUST** recycle stale `codex_*_cron` and `qwen_*_cron` role sessions after a large suspend gap.
- VM resume handling **MUST** clear persisted `*.codex_exec_session_id` and `*.codex_exec_session_meta` artifacts after a large suspend gap.
- a stale tmux thread or stale Codex resume artifact **MUST NOT** remain a blocker for planner or dev lane recovery.
- blocking interactive Codex prompts (`update`, trust/setup, manual choice screens) **MUST NOT** count as live lane readiness; the runner **MUST** recycle or restart the lane instead of treating the session as productive
- resume/bootstrap helpers **MUST NOT** create placeholder tmux sessions that look alive without running a real lane workload

### Tick Coordination
- overlapping planner ticks **MAY** emit `RUN_LOCK_BUSY`, but this **MUST** be treated as cadence backpressure, not as evidence that stale dispatch state is canonical.
- `waiting_on_agents` or similar planner states **MUST** be evaluated against the canonical active cycle only.
- stale active subagent rows from inactive cycles **MUST NOT** keep the planner lane off the current queue/workboard target.
- when SQLite/runtime truth is primary, planner graph rows stuck `running` or `pending` in `wait_or_collect_result` for more than 45 minutes with `last_meaningful_delta=none` **MUST** be quarantined out of canonical `active` dispatch views and treated as stale runtime debt, not live blockers.
- tmux lane existence **MUST NOT** be treated as proof of useful work; a lane whose pane cwd is deleted, not `samefile`-equivalent to `/home/venom/analyse-financiere`, or blocked on an interactive Codex update prompt **MUST** be treated as invalid and recycled automatically.

### Delivery Truth
- no task **MUST** complete without delivery proof
- code/config/runtime/product-logic completion **MUST** require a valid `commit_sha`
- false DONE inflation **MUST** be detectable

### Authority Boundaries
- workers/subagents **MUST** return results, not final business truth
- planner **MUST** remain authoritative for final orchestration mutation
- `admin` capability **MUST NOT** become backlog owner
- `scrum` capability **MUST NOT** become a delivery owner

### Capability Routing
- capability dispatch **MUST** bind to an `owner_task_id` whose canonical task role matches the target capability role
- `dev` capability **MUST** attach only to `dev` tasks
- `admin` capability **MUST** attach only to `admin` tasks
- when Codex is rate-limited for `planner` or `dev`, the secondary Codex fallback **MUST** be `gpt-5.3-codex-spark` with `high` reasoning before degrading to `qwen`
- route-mismatched capability results **MUST NOT** merge back into the workboard as delivery truth
- route-mismatched capability records **MUST** degrade to transport/routing failures, not business blockers on the parent planner task

### Product Priority
- product-value degradation **MUST** be visible
- orchestration-only work **MUST NOT** dominate when P0 product behavior is broken
- planner autonomy **MUST** classify each batch before downstream execution as one of:
  - `net_new`
  - `hardening`
  - `validation`
  - `reuse_only`
- a repeated batch on the same product title/scope **MUST NOT** count as fresh delivery unless it introduces a clearly stated new user-visible capability or closes an explicit regression
- two consecutive `reuse_only` or `validation` batches on the same scope **MUST** trigger a stagnation alert and force the next planner step to define a novelty target before minting more downstream work
- throughput **MUST NOT** be reported as value delivery without a separate net-new user-value assessment

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
- provider policy duplication outside model plane

### `product_priority_guard.py`
Purpose:
- preserve delivery effort for real product value

## Interfaces
Primary checks:
- `/api/status`
- `/api/doctor`
- `bash scripts/fc_doctor.sh --json`
- planner contracts and planner dispatch snapshots derived from runtime truth

Access policy:
- VM-local monitor: `http://127.0.0.1:7779/`
- host-facing monitor: `http://192.168.64.9:7780/`
- public tunnels are disabled by default and are not reliability primitives

Canonical orchestrator sources:
- `logs-codex-runs/orchestrator-state/*`
- `docs/operations/orchestrator/priority-queue.json` as compatibility projection
- `docs/operations/orchestrator/parallel-workstreams.json` as compatibility projection

Active-cycle invariant:
- `active_cycle.active_batch_ids` must be derived from currently open queue/workboard rows only.
- `reconcile_state(...)` must purge any batch from `active_cycle.active_batch_ids` once the batch is already `DONE/CLOSED` in runtime rows.
- purged batch ids move to `recent_completed_batch_ids`; they must not remain the canonical actionable cycle.

## Runtime Behavior

### Target mode
- `planner-experimental` is the target mode
- health and readiness derive from planner plus runtime/provider integrity
- capability outputs from dev/admin/scrum are consumed through planner-owned delegation
- doctor and monitor may remain globally `degraded` when planning-plane or operator-plane checks are not configured, even when runtime truth is healthy

### Compatibility mode
- legacy multi-lane scheduling may still run for rollback or diagnostics
- it is not the target architecture

## Operator Commands
```bash
bash scripts/fc_setup_crons.sh --profile planner-experimental
bash scripts/fc_doctor.sh --json
cat logs-codex-runs/monitor-lan-url.txt
curl -s http://127.0.0.1:7779/api/status?lite=1 | jq '{health,execution_mode,core_roles}'
curl -s http://192.168.64.9:7780/api/status?lite=1 | jq '{health,execution_mode,core_roles}'
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
- corrupted compatibility registries or projections do not break the runtime critical path when SQLite is healthy
