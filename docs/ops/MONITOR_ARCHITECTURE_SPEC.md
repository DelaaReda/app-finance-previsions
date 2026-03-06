# Monitor Architecture Specification

## Changelog
- **2026-03-04**: New document; formalized monitor layering contract (collection, aggregation, API/UI), core-health rule, and advisory visibility.

## 1) Purpose and Scope
This spec defines FC Monitor architecture and behavior for runtime observability.

Scope:
- Data sources and path resolution.
- Health computation policy.
- API contracts.
- UI behavioral guarantees.

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- Monitor **MUST** compute global health from `planner/dev/admin` only.
- Advisory lanes **MUST** be observable but non-blocking.
- Monitor **SHOULD** prefer writable canonical workspace roots.
- API payloads **MUST NOT** regress required keys to `null` unexpectedly.

## 3) Interfaces and Schemas
### Required APIs
- `GET /api/status`
- `GET /api/runtime-diagnostics`
- `GET /api/agent-insights`
- `GET /api/iteration-issues`
- `GET /api/issues/feed`
- `GET /api/issues/summary`
- `GET /api/workboard`

### Status payload key groups
- `health`
- `agents`
- `rate_limits`
- `kpi`
- `runtime_freshness`
- `sources`
- `dispatcher_tshape`
- `po_scrum_master`
- `agent_messages`

### Agent message view model
- `open_count`, `delivered_count`, `actioned_count`, `closed_count`
- `open_by_role`
- `last_message_id_by_role`
- `latest_action_status_by_role`

## 4) Runtime Behavior and Edge Cases
- Root resolution scores candidates by orchestrator presence, writable logs, and freshness.
- Shared mount roots are penalized to avoid stale mirror attachment.
- Historical permission errors are shown as historical unless recent evidence exists.
- If monitor data is temporarily unavailable, payload should degrade gracefully with unknown placeholders.

## 5) Operator Commands and Expected Outputs
- Start monitor stack (project flow):
```bash
bash scripts/monitor_stack_guard.sh
```
Expected:
- monitor API reachable and tunnel guard handling as configured.

- Contract smoke:
```bash
bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779
```
Expected:
- PASS with non-null critical status fields.

## 6) Observability and Troubleshooting
Monitor data dependencies:
- `docs/operations/orchestrator/*.json*`
- `logs-codex-runs/fc-ticks/*`
- `logs-codex-runs/role-runner/*`
- role state contracts in `/home/venom/.openclaw/cron/role-state`
- message bus and advisory report files

Troubleshooting rule:
- If UI appears stale, verify selected `sources` and workspace root scoring outcome.

## 7) Compatibility and Migration Notes
Target architecture split:
1. Collectors
2. Aggregators
3. API/UI presentation

Current implementation remains monolithic in `apps/monitor/server.py`; split is planned progressively with compatibility preserved.

## 8) Acceptance Criteria
- API remains backward-compatible for existing consumers.
- Core health policy remains stable under advisory activity.
- Message/advisory visibility is present and actionable.
- Monitor contract smoke remains green.

## 2026-03-05 Layering Progress Update

### Current extraction state
- Implemented monitor module tree: `apps/monitor/src/{collectors,aggregators,api}`.
- `doctor` API is mounted from `apps/monitor/src/api/doctor_router.py`.

### Remaining split steps (non-breaking)
1. move `/api/status` builders to `aggregators/health.py` + `api/status_router.py`,
2. move `/api/runtime-diagnostics` builders to `aggregators/diagnostics.py` + router,
3. keep `apps/monitor/server.py` as bootstrap only (app init + include routers).

### Compatibility invariant
- Existing public payload keys remain additive and stable.
## Update 2026-03-06 — Admin Dispatch + Dev Passive Signals

### `/api/status` additions

- `admin_dispatch` block:
  - `status`
  - `last_action`
  - `last_reason`
  - `dispatch_reason_code`
  - `autonomy_reason_code`
  - `stream_fairness_slot`
  - `cooldown_left_s`

### `/api/runtime-diagnostics` additions

- `signals.dispatcher_starvation_s`
- `signals.passive_with_ready_streak`
- `signals.admin_dispatch_status`
- `signals.admin_dispatch_last_action`
- `signals.admin_dispatch_last_reason`

These fields are additive and non-breaking.

Validation (VM):
```bash
cd /home/venom/analyse-financiere
scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779
python3 -m pytest -q apps/monitor/tests/test_status_never_null.py apps/monitor/tests/test_runtime_diagnostics.py
```
