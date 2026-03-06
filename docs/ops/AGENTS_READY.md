# Agents Readiness (Operational State)

## Changelog
- **2026-03-04**: Full rewrite in English; converted from historical snapshot to operational readiness standard tied to current runtime.

## 1) Purpose and Scope
This document defines what “ready” means for agent operations before and during active orchestration.

Scope:
- Core lane readiness (`planner/dev/admin`).
- Advisory lane status (`po_scrum_master`).
- Required gates (contracts, sessions, queue/workboard, monitor).

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- Runtime execution **MUST** happen inside VM workspace `/home/venom/analyse-financiere`.
- Runtime execution **MUST NOT** run on macOS host (servers, crons, role ticks).
- Runtime runbooks **MUST** be written as VM-local commands (no `ssh dev-vm-utm ...` wrappers in canonical steps).
- Host context **MUST** be checked with `bash scripts/runtime_host_check.sh` before start/restart/install-cron operations.
- Core lanes **MUST** be available before declaring runtime ready.
- Advisory lane **MUST NOT** influence global health readiness.
- Queue/workboard **MUST** parse and remain state-consistent.
- Contract guard suites **MUST** pass before major rollout changes.

## 3) Interfaces and Schemas
Readiness checklist schema:
- `runtime_services`: backend/frontend/monitor
- `core_lanes`: planner/dev/admin tick freshness
- `contracts`: latest valid contract per core lane
- `orchestration_data`: queue/workboard health
- `guards`: contract guard + runtime context tests
- `advisory`: po_scrum_master status (informational)

## 4) Runtime Behavior and Edge Cases
Current behavior:
- `full` profile runs planner/dev/admin and utility jobs.
- `canary` profile runs planner/dev only.
- `scrum_master` runs as advisory in `full` via cron flags (`FC_PO_SCRUM_MASTER_CRON=1`, `FC_PO_SCRUM_MASTER_RUN_NOW=1`).

Approved direction:
- `po_scrum_master` every 5 minutes in `full` profile only.

Edge cases:
- Temporary stale monitor state should not auto-fail readiness if core lanes are healthy and recovering.
- Historical errors must be labeled historical, not active blockers.

## 5) Operator Commands and Expected Outputs
- Quick readiness snapshot:
```bash
bash scripts/runtime_host_check.sh
bash scripts/fc_health_check.sh --strict
bash scripts/monitor_agents.sh
```
Expected:
- `runtime_is_vm=1`, services up, and core lane coverage visible.

- Verify tests:
```bash
python3 platform/automation/tests/test_role_contract_guard.py
python3 platform/automation/tests/test_role_runtime_context.py
```
Expected:
- Passing suites with no critical contract regressions.

## 6) Observability and Troubleshooting
Primary runtime artifacts:
- `/home/venom/analyse-financiere/docs/operations/orchestrator/executors-monitoring-latest.json`
- `/home/venom/analyse-financiere/logs-codex-runs/fc-ticks/*.tick.log`
- `/home/venom/analyse-financiere/logs-codex-runs/role-runner/*.events.log`

Monitor checks:
- `/api/status`
- `/api/runtime-diagnostics`

## 7) Compatibility and Migration Notes
- Legacy role names can exist in historical logs; readiness is evaluated on canonical core lanes.
- Config migration to YAML v1 may run with temporary ENV fallback.
- Advisory `po_scrum_master` remains non-blocking.

## 8) Acceptance Criteria
- Core lanes emit fresh valid contracts.
- Queue/workboard are coherent and actionable.
- Guard test baseline is green.
- Monitor status and CLI checks agree on core runtime state.

## Runtime Config & Advisory Cron (2026-03-04)

- Canonical runner config path: `platform/config/runner/runner.v1.yaml`.
- Canonical runner schema path: `platform/config/schema/runner.v1.schema.json`.
- `scripts/fc_setup_crons.sh` validates config before writing crontab.
- Full profile includes advisory `po_scrum_master` cron (`3-58/5`) gated by `FC_PO_SCRUM_MASTER_CRON_ENABLED`.
- Canary profile keeps advisory cron disabled by default.
- Runtime doctor:
  - CLI: `bash scripts/fc_doctor.sh --json`
  - Monitor API: `/api/doctor` and `/api/doctor/latest`
