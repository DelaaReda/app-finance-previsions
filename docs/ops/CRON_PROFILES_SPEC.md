# Cron Profiles Specification

## Changelog
- **2026-03-04**: New document; formalized full/canary schedule matrix, profile behavior, and advisory lane policy.
- **2026-03-06**: Added `planner-experimental` mono-lane profile for planner-owned orchestration.

## 1) Purpose and Scope
This spec defines cron profile behavior for orchestration roles and utility jobs.

Profiles:
- `full`
- `canary`
- `planner-experimental`

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- Profiles **MUST** be installed via `scripts/fc_setup_crons.sh`.
- `full` **MUST** schedule core lanes planner/dev/admin.
- `canary` **MUST** schedule planner/dev and keep admin paused.
- `planner-experimental` **MUST** schedule planner only for delivery lanes, while keeping essential infra/cleanup jobs.
- `po_scrum_master` advisory cron **MUST** be enabled only in `full` profile (approved target).

## 3) Interfaces and Schemas
### Installer interface
```bash
bash scripts/fc_setup_crons.sh --profile full
bash scripts/fc_setup_crons.sh --profile canary
bash scripts/fc_setup_crons.sh --profile planner-experimental
```

### Current schedule matrix (observed)
- `full`
  - planner: `0,22,44`
  - dev: `6,28,50`
  - admin: `*/5` (configurable via env)
- `canary`
  - planner: `0,30`
  - dev: `10,40`
  - admin: paused
- `planner-experimental`
  - planner: `0,22,44`
  - dev: paused
  - admin: paused
  - scrum_master: paused

### Utility jobs (both profiles)
- VM resume guard
- auto recovery
- chromium watchdog
- stale lock cleanup
- monitor guard
- log cleanup
- health snapshot
- auto batch close
- dependency recompute (`scripts/dependency_recompute.sh`, every 5 minutes)

## 4) Runtime Behavior and Edge Cases
- Installer removes old managed cron lines before writing new ones.
- Legacy scrum/master cron lines are purged by installer filters.
- Advisory `scrum_master` execution remains gated in tick launcher unless explicit flags are provided.
- In `planner-experimental`, non-planner lane ticks are ignored by `fc_agent_tick.sh` when `FC_EXPERIMENTAL_PLANNER_ONLY=1`.

## 5) Operator Commands and Expected Outputs
- Install profile:
```bash
bash scripts/fc_setup_crons.sh --profile full
crontab -l | grep -E 'fc_agent_tick|monitor_stack_guard|health_snapshot' | grep -v '^#'
```
Expected:
- profile-specific role lines and utility lines are present.

- Verify canary:
```bash
bash scripts/fc_setup_crons.sh --profile canary
crontab -l | grep -E 'fc_agent_tick\.sh (planner|dev|admin)'
```
Expected:
- planner/dev present, admin absent.

- Verify planner-experimental:
```bash
bash scripts/fc_setup_crons.sh --profile planner-experimental
crontab -l | grep -E 'fc_agent_tick\.sh (planner|dev|admin|scrum_master)'
```
Expected:
- planner present
- dev/admin/scrum_master absent

## 6) Observability and Troubleshooting
Profile drift indicators:
- Missing expected role lines.
- Unexpected legacy role lines.
- Health mismatches caused by schedule gaps.

Troubleshooting sources:
- `logs-codex-runs/fc-ticks/*.cron.log`
- `logs-codex-runs/health-snapshot.log`
- monitor `/api/status` sources and freshness.

## 7) Compatibility and Migration Notes
- Cron profile behavior is stable; additional advisory lane scheduling should remain additive.
- Environment controls remain available for timeout/cadence tuning during migration.
- `planner_architect_orchestrator` remains a compatibility alias; `planner` stays canonical in the installed cron lines.

## 8) Acceptance Criteria
- Installing profile `full`, `canary`, or `planner-experimental` yields deterministic role schedules.
- Utility jobs remain present in both profiles.
- Advisory lane policy remains explicit and non-breaking.
