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
- deleted tmux workdirs **MUST** fail lane validity even when tmux metadata still looks alive; recovery guards **MUST** inspect pane/process cwd and auto-recreate role lanes instead of counting `(deleted)` sessions as healthy
- the compatibility alias `/home/venom/shared/analyse-financiere` **MUST NOT** count as a productive runtime root for auto lanes; only the canonical path string `/home/venom/analyse-financiere` is valid for lane readiness
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
- deleted or foreign tmux workdirs **MUST** fail lane validity with an explicit recovery reason (`deleted_workdir`, `foreign_workdir`, or `missing_workdir`) so auto-recovery can recreate the lane instead of preserving a false-positive shell.
- lane validity **MUST** inspect both tmux pane metadata and the real cwd of the pane process/children; pane metadata alone is insufficient after VM resume or deleted-workdir drift.
- when the canonical active cycle is pinned on an `admin` or `dev` task that remains `IN_PROGRESS` without any meaningful delivery proof (`artifact`, `runtime_artifact`, `verify`, `summary`, or `last_meaningful_progress_at`) past the configured freshness threshold, planner autonomy **MUST** surface `canonical_handoff_stale` on the active cycle instead of reporting only a generic `active_cycle_pinned` state.

### Delivery Truth
- no task **MUST** complete without delivery proof
- code/config/runtime/product-logic completion **MUST** require a valid `commit_sha`
- false DONE inflation **MUST** be detectable
- repeated completion proofs for the same task without a new state transition **MUST NOT** count as additional delivery progress; they **MUST** be surfaced as proof churn
- retryable runtime-truth residues such as `invalid_subagent_result:start_banner_only` **MUST NOT** stay decision-capable after the canonical task has already returned to `READY_PLANNER`/`READY_*`; they **MUST** be quarantined out of primary planner dispatch reasoning
- this quarantine **MUST** be visible in `runtime_truth_snapshot` itself, not only in planner dispatch views, so admin/monitor/guardian consumers stop reading stale retryable residues as current blockers
- when such retryable residues are quarantined, canonical task rows **MUST** revert to ready-state semantics (`status=READY_*`, default ready `next_action`) instead of continuing to advertise stale `retry_capability`.
- invalid auxiliary tmux sessions (`codex_*_cron`, `qwen_*_cron`, `adminapp_codex_sync`, `admin-agents-sync-cron`, `clawsentinel`) **MUST** be quarantined automatically when they no longer point at the VM workspace, even if their owning cron is separate from the core planner/dev/admin recovery loop.
- degraded app runtime **MUST NOT** be counted as successful independent delivery even when proof coverage is otherwise complete
- completion idempotency for a given `role + task_id + handoff_to` **MUST** be stable and deterministic; a repeated `complete` on an already terminal task with the same idempotency key **MUST** be a no-op instead of generating another proof/event pair

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
- planner supervision artifacts **MUST** stay aligned with canonical active-cycle truth.
  - `planner-guardian-latest.json` **MUST NOT** recommend `autobatch`, fresh `ANALYSIS`, or new batch creation while queue/workboard already expose a non-terminal canonical task on the active cycle.
  - `agent-iteration-issues-latest.json` **MUST** refresh `dev` and `admin` role snapshots from canonical queue/workboard truth on planner active-cycle checks, even when those lanes have no fresh useful tick of their own.
  - when workboard projection fields are too weak for autonomous reasoning, published supervision payloads **MUST** mark them `projection_secondary_only=true` instead of pretending they are decision-capable.
- stagnation hard-stop **MUST** have an explicit exit workflow.
  - planner runtime **MUST** provide a canonical way to set `novelty_target` / `user_visible_delta` on the active cycle before reopening the same scope.
  - once an explicit novelty target is set on the active cycle, the autobatch novelty gate **MAY** reopen the scope intentionally with `reason=novelty_target_set`.
- monitor `status_service` **MUST NOT** override degraded `doctor` backend/app health to `ok` only because a live HTTP probe still answers.
- replaying the same completion proof after a task is already terminal or has been handed back to `READY_PLANNER`/`READY_DEV` **MUST** be a no-op until a fresh claim starts a new work cycle.
- a repeated batch on the same product title/scope **MUST NOT** count as fresh delivery unless it introduces a clearly stated new user-visible capability or closes an explicit regression
- two consecutive `reuse_only` or `validation` batches on the same scope **MUST** trigger a stagnation alert and force the next planner step to define a novelty target before minting more downstream work
- throughput **MUST NOT** be reported as value delivery without a separate net-new user-value assessment
- when the novelty/stagnation guard blocks autobatch or active-cycle continuation, planner autonomy **MUST** stop before claiming more planner work on that same scope and surface `planner_stagnation_requires_novelty_target` explicitly in canonical state instead of continuing same-scope churn.
- runtime implementation rule: canonical queue items **MUST** persist `scope_key`, `novelty_class`, `delivery_kind`, and `user_value_delta_visible`
- runtime implementation rule: canonical queue `meta` **MUST** expose a double scoreboard (`throughput_*` vs `net_new_user_value_*`) plus `stagnation_alert` when the same scope loops on low-novelty classes

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
- proof present without transition **MUST** become `proof_transition_stalled` after TTL instead of remaining silently `IN_PROGRESS`

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

## Canonical Lane Validity
- tmux session presence is advisory only; it is never sufficient proof that a core lane is productive.
- A core lane is productively valid only when bootstrap is healthy and, if the role has actionable work on the active canonical cycle, its `role-state/<role>.last_contract` is both fresh and bound to that same active cycle.
- If actionable work exists and the contract is missing, stale, or off-cycle, the lane must be marked invalid and recovery may restart it automatically.
- If no actionable work exists for the role, a stale contract is advisory debt only; it must not be treated as an active blocker for the canonical cycle.
- A live active-cycle `stagnation_alert` is a hard planner guard, not an advisory signal: canonical planner rows must be blocked with `stagnation_requires_novelty_target` until a novelty target exists.
- If meaningful proof already exists and no blocker is present, canonical state must transition within the proof TTL or be auto-blocked as `proof_transition_stalled`; repeated proof emission without transition is orchestration debt, not progress.
- If active-cycle workboard rows are missing operational fields (`state/status`, owner-role, next action, proof count), the projection must be marked `decision_capable=false` and treated as non-decision-capable.
- Strict delivery completions (`dev`, `admin`) must not pass while local product runtime probes are degraded; the delivery gate must block them with `DELIVERY_RUNTIME_DEGRADED`.
- Supervision surfaces (`planner-guardian-latest.json`, `agent-iteration-issues-latest.json`, doctor snapshots) must follow canonical active-cycle truth. If a hard guard is active or the active canonical task belongs to a downstream role, those surfaces must not recommend planner analysis, planner autobatch, or new-batch behavior that contradicts the current active task.
- The same hard guard must expose a canonical `novelty_target_workflow` with `owner_role=planner`, `next_action=define_novelty_target`, required fields `novelty_target`, `user_value_delta`, `scope_delta`, `success_metric`, and policy `no_new_downstream_work` until the target exists.
- this `novelty_target_workflow` **MUST** be published directly in canonical queue/meta and active batch rows, not only in guardian/advisory artifacts, so planner can recover from the hard stop using queue/workboard truth alone.
- while that workflow is unresolved, active downstream rows on the same canonical cycle **MUST** be policy-blocked as `novelty_target_required_before_downstream`; once the novelty target is present, reconciler **MUST** restore their prior state instead of leaving stale block markers behind.
- Health semantics must be explicit and stable across doctor and monitor surfaces:
  - `doctor.status` = overall control-plane health
  - `product_runtime.status` = user-facing runtime health
  - `app_runtime.backend_api.status` = backend API runtime health
  - `agentic_runtime.status` = delivery control-plane health
  - `doctor.status=degraded` with `product_runtime.status=ok` means orchestration debt, not app outage
  - monitor reachability is advisory-only for `product_runtime`; it must not degrade doctor product runtime when `backend_api` remains healthy
- Completion proof emission must stay idempotent after closure or return-to-planner: replaying the same completion handoff on a task already `DONE`, `READY`, or `READY_PLANNER` must not append a new proof manifest.
- Exiting `stagnation_requires_novelty_target` requires both fields canonically:
  - `novelty_target`
  - `user_visible_delta`
- `novelty_target` alone is insufficient; planner/autobatch reopening must stay blocked while `user_visible_delta` is empty.
- If the hard guard persists without an effective write, canonical truth must publish `novelty_target_audit` with missing fields, age, threshold, and overdue status so supervision can escalate from queue/workboard truth directly.
- If the active canonical cycle contains a downstream `admin` or `dev` task in `READY` or `READY_PLANNER` with `planner_takeover_required=true` or `next_action=retry_capability`, planner autonomy **MUST** attempt a targeted capability dispatch before accepting the cycle as merely pinned.
- If that targeted dispatch does not materialize into execution, planner autonomy **MUST** emit an explicit blocker (`planner_admin_dispatch_not_materialized` / `planner_dev_dispatch_not_materialized`) instead of collapsing the state into a generic `active_cycle_pinned`.
- Planner-owned dispatch selection and planner autonomy capability guards **MUST** reason from operational task state (`status` when it carries canonical runtime meaning) instead of raw `state` only; stale `state=IN_PROGRESS` **MUST NOT** suppress a canonical downstream retry once `status` has already returned to `READY_*`.
- Planner takeover runtime verification **MUST** use lightweight local health surfaces first (`/api/status?lite=1`, `doctor`, direct backend health) and **MUST NOT** fail solely because the full monitor status endpoint is slow during a backend auto-heal window.
- The admin dispatcher **MUST** treat planner-owned admin handoffs as claimable work when canonical task state is `READY`, `READY_PLANNER`, or `READY_ADMIN`; planner-to-admin dispatch is not allowed to stall solely because the task never normalized back to plain `READY`.
- Dispatcher/runtime claim logic **MUST** resolve canonical target role from compatible task fields (`role`, `assigned_to`, `assignee`) instead of trusting only one projection key. Role-field drift in the workboard must not hide active or claimable downstream work.
- When a task row carries a stale `state=IN_PROGRESS` but an operational `status` of `READY`, `READY_PLANNER`, `READY_DEV`, `BLOCKED`, or `WAITING_DEP`, reconciler and monitor surfaces **MUST** treat the operational status as authoritative. Stale `IN_PROGRESS` projection must not count as real execution.
- `READY_PLANNER > 0` with `IN_PROGRESS = 0` on the active cycle is a stalled-flow condition, not an acceptable steady state, when planner intent is still targeting downstream capability dispatch.
- Planner-only runtime is not an acceptable independent-delivery steady state when downstream canonical work exists and `admin_autonomy_active=false`; supervision must surface it as delivery paused, not as healthy progress.
- Full monitor/runtime diagnostics surfaces must prefer a real doctor refresh over deferred placeholders. `doctor_refresh_deferred` is supervision debt and must remain visible until a fresh doctor snapshot exists.
- Periodic backend auto-heal **MUST** treat a non-responsive `/api/health` as restart-worthy even when there is no socket-pressure signature. A live process with timed-out health is degraded runtime, not success.
- `READY_PLANNER` or other capability-ready downstream rows must not remain a canonical steady state when planner takeover depends on a degraded `backend_api`. The reconciler must expose that as a delivery-runtime gate in queue/workboard and restore the rows automatically when backend health returns.
