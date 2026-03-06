# Cron Profiles Specification

## Purpose
Define the supported cron profiles for the current runtime architecture.

Current target architecture:
- one scheduled orchestrator lane: `planner`
- `dev`, `admin`, and `scrum_master` operate as planner-owned capabilities/subagents in planner-only mode
- utility/runtime guard jobs stay scheduled independently

## Profiles

### `planner-experimental`
Target profile for active orchestration.

Behavior:
- schedules `planner` only for orchestration work
- keeps essential infra/cleanup jobs
- does not schedule independent `dev`, `admin`, or `scrum_master` delivery lanes

Notes:
- planner delegates bounded work through `planner_subagent_manager.py`
- non-planner role ticks are ignored when `FC_EXPERIMENTAL_PLANNER_ONLY=1`

### `full`
Supported compatibility and incident profile.

Behavior:
- keeps legacy multi-lane scheduling available for recovery, diagnosis, or controlled fallback
- not the target steady-state architecture

### `canary`
Reduced compatibility profile for limited testing.

Behavior:
- keeps a smaller legacy schedule surface
- not the target steady-state architecture

## Normative Rules
- Cron profiles **MUST** be installed through `scripts/fc_setup_crons.sh`.
- `planner-experimental` **MUST** be treated as the target runtime profile.
- `full` and `canary` **MUST NOT** be treated as the architectural target; they are fallback/test profiles.
- Utility jobs **MUST** remain installed across profiles when required for runtime health.
- Legacy `po_scrum_master` compatibility scripts **MUST NOT** be interpreted as target scheduling policy.

## Installer Interface
```bash
bash scripts/fc_setup_crons.sh --profile planner-experimental
bash scripts/fc_setup_crons.sh --profile full
bash scripts/fc_setup_crons.sh --profile canary
```

## Expected Schedule Shape

### `planner-experimental`
- planner: scheduled
- dev: not independently scheduled
- admin: not independently scheduled
- scrum_master: not independently scheduled
- utility jobs: scheduled

### `full`
- planner/dev/admin legacy lines may be scheduled
- used only for rollback, diagnostics, or compatibility operation

### `canary`
- reduced compatibility schedule
- used only for limited testing

## Utility Jobs
Typical utility jobs include:
- monitor guard
- stale lock cleanup
- health snapshot / reconciliation helpers
- dependency recompute where enabled

These are orthogonal to planner-only orchestration and stay valid.

## Operator Commands

Install target profile:
```bash
bash scripts/fc_setup_crons.sh --profile planner-experimental
crontab -l | rg 'fc_agent_tick\.sh (planner|dev|admin|scrum_master)|monitor_stack_guard|cleanup_stale_role_locks'
```

Expected:
- planner line present
- dev/admin/scrum_master independent lane lines absent
- utility jobs present

Install compatibility profile:
```bash
bash scripts/fc_setup_crons.sh --profile full
```

Expected:
- legacy multi-lane lines may reappear for incident recovery

## Observability
Primary verification points:
- `crontab -l`
- `logs-codex-runs/fc-ticks/planner.cron.log`
- `/api/status`
- `bash scripts/fc_doctor.sh --json`

Expected in target mode:
- `execution_mode=planner_experimental`
- `core_roles=["planner"]`

## Acceptance Criteria
- `planner-experimental` installs deterministically
- planner-only scheduling remains stable
- compatibility profiles remain available without changing the target architecture definition
