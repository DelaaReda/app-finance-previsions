# Orchestration Reliability Specification

## Changelog
- **2026-03-04**: Full rewrite in English; aligned with current runtime and approved target direction (core-health policy, advisory lane policy, message bus, YAML config roadmap, doctor contract).

## 1) Purpose and Scope
This specification defines reliability guarantees for Finance Copilot orchestration.

Scope includes:
- Scheduler profiles and role cadence.
- Contract quality gates and issue reporting.
- Health computation policy.
- Runtime path/lock/session consistency.
- Incident diagnostics and fallback behavior.

Out of scope:
- Product feature logic inside domain endpoints.
- UI design details (covered in monitor architecture spec).

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
### Topology
- Delivery topology **MUST** remain `planner/dev/admin` as core lanes.
- `scrum_master` **MUST** run as an operational coordination lane (full remediation, dual authority).

### Health policy
- Global health **MUST** be computed from core lanes: `planner/dev/admin/scrum_master`.
- Transient scrum-only incidents SHOULD degrade to `STALE` first (guarded), and only escalate to `DEGRADED` on sustained/hard blockers.

### Contracts
- Every core tick **MUST** emit a valid normalized contract.
- `issues`, `issue_count`, `issue_severity` **MUST** be present on each core tick.
- `blocked` contracts **MUST** include at least one issue code with severity `medium|high|critical`.

### State consistency
- Queue/workboard/state files **MUST** be read from canonical orchestrator roots (`docs/operations/orchestrator` first, compatibility alias accepted).
- Stale locks **MUST** be cleaned automatically by scheduled cleanup jobs.
- Dependency and queue/workboard consistency **SHOULD** be refreshed periodically (`scripts/dependency_recompute.sh`) to avoid silent `WAITING_DEP` plateaus.

### Safety and fallback
- Fallback contracts **MUST** be explicit (checkpoint/rate-limit/no-delta), never silent.
- Retry/fallback behavior **SHOULD** preserve deterministic evidence fields.

## 3) Interfaces and Schemas
### Core health interface
- Source endpoint: `GET /api/status`.
- Core keys: `health`, `agents`, `rate_limits`, `runtime_freshness`.
- Policy key: core roles are defined by monitor `CORE_ROLES=(planner,dev,admin,scrum_master)`.

### Contract evidence (core)
Minimal required evidence keys per normalized runtime contract:
- `task_update`
- `issues`
- `issue_count`
- `issue_severity`
- `run_note`
- Role artifact marker (role-specific)

Conditional keys:
- Delivery close/handoff: `cmd`, `tests_run`.
- Non-delivery modes (`analysis_only|none_no_ready|none_no_signal`): `channels_read`, `impact_assessment`, `impact_action`.

### Queue/workboard sources
- Primary: `/home/venom/analyse-financiere/docs/operations/orchestrator/priority-queue.json`
- Primary: `/home/venom/analyse-financiere/docs/operations/orchestrator/parallel-workstreams.json`
- Compatibility alias: `docs/orchestrator-ops/*`

## 4) Runtime Behavior and Edge Cases
### Current (observed)
- `full` profile schedules planner/dev/admin plus utility jobs.
- `full` profile also schedules `scrum_master` every 5 minutes as operational lane.
- `canary` profile schedules planner/dev and pauses admin.

### Approved target
- `scrum_master` runs as **scheduled operational lane** (`*/5`) in `full` profile only.
- `scrum_master` is included in global health with anti-oscillation guard.
- `canary` remains limited (no advisory cron lane).

### Edge cases
- If status is stale but no hard blocker exists, health may be `STALE` (not `DEGRADED`).
- Historical permission errors must remain informational unless they are recent.
- Scrum-only transient blockers should not hard-flip global health to `DEGRADED`.

## 5) Operator Commands and Expected Outputs
- Install cron profile:
```bash
bash scripts/fc_setup_crons.sh --profile full
bash scripts/fc_setup_crons.sh --profile canary
```
Expected:
- `full`: planner/dev/admin/scrum_master jobs present.
- `canary`: planner/dev only.

- Health snapshot:
```bash
bash scripts/fc_health_check.sh --strict
bash scripts/monitor_agents.sh
bash scripts/dependency_recompute.sh
```
Expected:
- Backend/frontend/monitor status + queue/workboard alignment.

- Contract guard tests:
```bash
python3 platform/automation/tests/test_role_contract_guard.py
```
Expected:
- Guard suite passes with issue-reporting and blocked-contract checks.

## 6) Observability and Troubleshooting
Primary telemetry/log surfaces:
- `logs-codex-runs/fc-ticks/*.tick.log`
- `logs-codex-runs/role-runner/*.live.log`
- `logs-codex-runs/role-runner/*.events.log`
- `docs/operations/orchestrator/executors-monitoring-latest.json`
- `docs/operations/orchestrator/agent-iteration-issues.jsonl`

Monitor APIs for reliability checks:
- `GET /api/status`
- `GET /api/runtime-diagnostics`
- `GET /api/issues/feed`
- `GET /api/issues/summary`

## 7) Compatibility and Migration Notes
- Compatibility aliases (`docs/orchestrator-ops`) are read-compatible but canonical writes should target `docs/operations/orchestrator`.
- Runtime config strategy is transitioning toward YAML v1 canonical with temporary ENV fallback.
- `scrum_master` cron lane is active in `full` profile and defaults to operational mode.

## 8) Acceptance Criteria
- Health calculation includes `scrum_master` with anti-flap guard and remains stable.
- Contract guard blocks malformed core outputs consistently.
- Queue/workboard/state mismatch is detectable from monitor diagnostics.
- Reliability checks are reproducible from CLI (`fc_health_check`, `monitor_agents`) and monitor APIs.

## 2026-03-06 Scrum Master Operational Addendum

### Scrum operational lane
- `scrum_master` runs on cron every 5 min in full profile.
- Controlled by `FC_SCRUM_MASTER_MODE` and `FC_SCRUM_MASTER_CRON_ENABLED` (legacy `FC_PO_SCRUM_MASTER_*` accepted).
- Full remediation mode enabled via `FC_SCRUM_MASTER_FULL_REMEDIATION=1`.
- Escalation policy defaults to `FC_SCRUM_MASTER_ESCALATE_AFTER_CYCLES=2`.

## 2026-03-06 Throughput Addendum (P0)

### Admin takeover rule (hard requirement)
- `AUTO_TRIGGER=blocked_explicit` must be enabled only when blocked roles intersect with actionable lanes `{planner,dev}`.
- `blocked_roles=[admin]` alone must not keep takeover active.
- Dispatcher telemetry must expose:
  - `autonomy_reason_code`
  - `dispatch_reason_code`
  - `stream_fairness_slot`

### Dev anti-passive rule (hard requirement)
- When `dev_has_ready_task=1` and dev keeps passive updates (`analysis_only|none_no_ready|none_no_signal`), runtime must enforce actionability.
- Persistent state file:
  - `/home/venom/.openclaw/cron/role-state/dev.autonomy.state.json`
- Mandatory tracked fields:
  - `none_no_signal_streak`
  - `last_delivery_ts`
  - `last_enforced_ts`
  - `last_ready_seen_ts`
  - `enforced_fail_streak`
  - `cooldown_until_epoch`

### VM validation commands
```bash
cd /home/venom/analyse-financiere
python3 -m pytest -q \
  platform/automation/tests/test_admin_dispatcher_autonomy.py \
  platform/automation/tests/test_admin_dispatcher_flow.py \
  platform/automation/tests/test_dev_autonomy_enforcement.py \
  platform/automation/tests/test_role_contract_guard.py
```
- Health includes scrum contribution with guard against transient-only flapping.

### Runner config contract
- Versioned runner config is now validated during cron setup.
- Runtime env propagation includes:
  - `RUNNER_CONFIG_FILE`
  - `RUNNER_CONFIG_FALLBACK_ENV`
- Startup traces include `config_version`.

## 2026-03-05 Monitor Runtime-Recovered Normalization

### Problem
A stale admin contract could keep `status=ALERTE` / `blocker=backend_api_unreachable` even when provider probes were already healthy.

### Rule
When doctor providers confirm runtime is healthy (`api_health_ok=1` and `monitor_status_ok=1`) and admin blocker is one of:
- `BACKEND_API_UNREACHABLE`
- `BACKEND_API_HEALTHCHECK_FAIL`
- `MONITOR_API_UNREACHABLE`
- `BACKEND_AND_MONITOR_UNREACHABLE`

the monitor must normalize the display state as recovered-soft:
- `soft_blocker=true`
- `blocker=NONE`
- `status=WAIT` (if stale alert-like)
- `delta=RUNTIME_RECOVERED_SOFT` (if stale runtime-degraded marker)

This is display/aggregation normalization only; it does not alter raw runner logs.

## 2026-03-05 Batch Autonomy Rule (No Inter-Batch Dependencies)

- Queue-level `depends_on` between batches is disabled for active/planned streams.
- Any legacy `WAITING_DEP` batch state is normalized to `PLANNED` and can be promoted to `READY` by scheduler policy.
- Task dependencies are constrained to same-stream tasks only; cross-stream links are sanitized at recompute time.
- Legacy queue dependencies are preserved only as audit metadata in `legacy_depends_on`.

## 2026-03-05 Local-DAG Fairness and Actionability Addendum

### Dispatch fairness (admin dispatcher)
- READY selection now uses weighted fairness across streams (priority-biased, anti-starvation).
- New telemetry fields in dispatcher events:
  - `dispatch_reason_code`
  - `stream_fairness_slot`
- Anti-starvation promotion uses `ready_wait_cycles` with threshold `ADMIN_DISPATCHER_FAIRNESS_MAX_STARVE_CYCLES`.

### Runner anti-stall actionability
- New runtime threshold: `TMUX_ROLE_ACTIONABILITY_FORCE_THRESHOLD`.
- On repeated passive outputs (`none_no_ready|none_no_signal`) while lane is active, reconcile forces an actionable next step.
- Fallback evidence now includes deterministic fields:
  - `fallback_reason`
  - `fallback_count_window`
  - `actionability_state`

### Validation
- `python3 -m pytest -q platform/automation/tests/test_admin_dispatcher_flow.py`
- `python3 -m pytest -q platform/automation/tests/test_role_runtime_context.py`

## 2026-03-06 Cross-Dep Invariant + Monitor Collector Split

### Cross-batch autonomy invariant (runtime validation)
- `parallel_workstream validate` now enforces explicit blocking invariants:
  - `INV-CROSS-DEP-QUEUE` when queue items still carry inter-batch `depends_on`.
  - `INV-CROSS-DEP-TASK` when cross-stream task dependencies survive sanitization.
- Validation evidence now includes:
  - `cross_dep_count`
  - `cross_task_dep_count`
  - `queue_inter_batch_dep_count`

### Monitor split progress (collectors layer)
- Message bus parsing/aggregation moved out of `apps/monitor/server.py` into:
  - `apps/monitor/src/collectors/message_bus.py`
- `server.py` now delegates agent-message snapshot collection to the collectors layer.
- Public API contract remains unchanged (`/api/status` retains `agent_messages` shape).

### Validation
- `python3 -m pytest -q platform/automation/tests/test_parallel_workstream_queue_sync.py`
- `python3 -m pytest -q apps/monitor/tests/test_agent_messages_status.py`
- `bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779`
## Update 2026-03-06 — Throughput Unblock (P0)

- Admin autonomy now uses actionable blockers only (`planner|dev`).
- `admin`-only blocker no longer triggers takeover activation.
- Dispatcher emits explicit reasons:
  - `autonomy_reason_code`
  - `dispatch_reason_code`
  - `stream_fairness_slot`
- Dev READY path is consumed proactively when dev lane is empty.
- Dev passive loop guard now tracks `passive_with_ready_streak` and escalates contract intent to `claim_or_progress_now`.

### Validate

- `python3 -m pytest -q platform/automation/tests/test_admin_dispatcher_autonomy.py`
- `python3 -m pytest -q platform/automation/tests/test_role_contract_guard.py`
- `bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779`

### Rollback

- `FC_ADMIN_AUTONOMY_ENABLED=0`
- `FC_ADMIN_DISPATCH_ENABLED=0`
- `FC_DEV_STRICT_ACTIONABILITY=0`

## 2026-03-06 Queue/Workboard Consistency Addendum
- Doctor consistency now derives workboard stream state from all task states (priority: `IN_PROGRESS` > `READY_DEV` > `READY_PLANNER/READY` > `WAITING_DEP` > `PLANNED`).
- Queue/workboard mismatch comparison normalizes `READY` and `READY_PLANNER` as equivalent.
- Runner queue reconciliation accepts `WAITING_DEP` and `PLANNED` as valid desired states during bidirectional sync.

## 2026-03-06 Stabilization Patch (S1-S5)

### Runtime truth overrides (admin)
- `FC_ADMIN_RUNTIME_OVERRIDE_ON_LIVE_PROBE=1` (default).
- If admin contract carries runtime blocker (`RUNTIME_DOWN*`, backend/monitor unreachable) but live probes are green:
  - normalize to `STATUS=PASS`, `VERDICT=PASS`, `BLOCKER_ID=NONE`, `DELTA=RUNTIME_VERIFIED_OK`.
  - evidence markers: `admin_runtime_override_applied=1`, `runtime_probe_api_ok=1`, `runtime_probe_monitor_ok=1`.

### Dispatcher autonomy trigger hardening
- `blocked_explicit` takeover now requires actionable blocked roles only: `{planner,dev}`.
- `blocked_roles=[admin]` now yields `autonomy_trigger=none`, `autonomy_reason_code=ADMIN_ONLY_BLOCK`.
- Decision log now includes `actionable_blocked_roles=`.

### DEV throughput controls
- Added `FC_DEV_WIP_TARGET` (default `2`) to fill DEV lane proactively.
- Added same-task claim cooldown:
  - `FC_DEV_SAME_TASK_CLAIM_COOLDOWN_S` (default `600`).
  - state file: `${FC_ADMIN_DISPATCH_STATE_DIR}/last_dev_claim.json`.
- Dispatch reason codes:
  - `READY_DEV_LANE_EMPTY` (legacy compatible, when DEV WIP was 0),
  - `READY_DEV_WIP_FILL` (when filling toward target WIP).

### DEV anti-loop enforcement
- Added runtime loop breaker in contract normalization:
  - `FC_DEV_CLAIM_LOOP_BREAKER=1` (default),
  - `FC_DEV_CLAIM_LOOP_THRESHOLD=3` (default).
- Signals/evidence:
  - `dev_claim_loop_count`, `claim_loop_breaker=1`, issue `dev_claim_loop` when breaker trips.

### Planner evidence softening with runtime markers
- Guard no longer hard-blocks planner for incomplete quality fields when runtime markers exist (`queue_version`, `workboard_version`) and strict mode is off.
- New env toggle:
  - `FC_PLANNER_EVIDENCE_STRICT=1` to restore strict blocking behavior.

### Monitor/Doctor alignment
- `admin_dispatch_snapshot` parser fixed (`key=value` regex with proper whitespace class).
- Runtime diagnostics signals now include:
  - `dev_claim_loop_count`,
  - `admin_runtime_override_applied`.
- Doctor state equivalence now treats aliases as equivalent:
  - `READY_DEV -> READY`,
  - `READY_PLANNER -> READY`.

### Validation commands (VM)
- `python3 -m pytest -q platform/automation/tests/test_admin_dispatcher_autonomy.py platform/automation/tests/test_admin_dispatcher_flow.py platform/automation/tests/test_dev_ready_force_claim.py platform/automation/tests/test_role_contract_guard.py platform/automation/tests/test_fc_doctor.py apps/monitor/tests/test_status_never_null.py apps/monitor/tests/test_runtime_diagnostics.py`
- `bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779`
- `bash scripts/critical_endpoints_smoke.sh --base-url http://127.0.0.1:8050`
- `bash scripts/runtime_e2e_gate.sh`
