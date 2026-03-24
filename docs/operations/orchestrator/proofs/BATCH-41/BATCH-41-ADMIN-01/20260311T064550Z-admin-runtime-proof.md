# BATCH-41-ADMIN-01 Runtime Proof

- Timestamp UTC: `2026-03-11T06:45:50Z`
- Scope: `Free Global Signal Mesh [ADMIN-01]`
- Policy: runtime/observability validation only, no queue/workboard edits

## Runtime truth

- `bash scripts/runtime_host_check.sh`
  - `runtime_is_vm=1`
- `curl -fsS --max-time 20 http://127.0.0.1:8050/api/forecasts/global-signal-mesh`
  - HTTP `200`
  - payload includes `mesh_id=free_global_signal_mesh`
  - payload includes `sources_catalog[].health`
  - payload includes `observability.freshness_expected_counts`
  - payload includes `coverage.free_nominal_path_only=true`
  - payload freshness SLA reports `within_target=true`
- `pytest apps/api/src/domains/forecasts/tests/test_global_signal_mesh_route.py -q`
  - `18 passed`

## Observability truth

- `timeout 30 bash scripts/fc_status_brief.sh`
  - failed after the built-in `8s` monitor probe budget
- `timeout 30 bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779 --timeout 20`
  - terminated by outer timeout; not green inside the bounded admin window
- `timeout 30 bash scripts/fc_doctor.sh --json`
  - `status=degraded`
  - runtime lifecycle `running`
  - scheduler/session/locks/providers all `ok`
  - queue/workboard mismatch narrowed to `BATCH-39`
  - planner dispatch still shows one active admin capability for `BATCH-41-ADMIN-01`
- `timeout 30 bash scripts/stale_cron_sweep.sh --dry-run --threshold 330`
  - `matched=0 stale=0`
- `timeout 30 bash scripts/monitor_agents.sh`
  - planner is still pushing `BATCH-41-ADMIN-01`
  - output also showed a workboard parse warning: `Expecting ',' delimiter: line 47896 column 31 (char 1992353)`

## Interpretation

- Task-scoped runtime is healthy: the delivered `global-signal-mesh` API is live and its contract/tests are green.
- Task-scoped admin merge is not cleanly unblocked from observability yet:
  - monitor-facing admin probes are still too slow or brittle for the default scripted budget
  - planner dispatch still holds an active admin capability for the same task
  - `BATCH-41-ADMIN-01` remains `IN_PROGRESS` in the workboard
- No stale cron locks or API outage were found, so no runtime repair was applied here.

## Planner signal

- Unblock status: `partial`
- Safe conclusion:
  - do not treat `BATCH-41` as a runtime outage
  - treat the remaining blocker as planner/control-plane observability debt
- Next planner move:
  - either collect/retire the active `planner_admin_*` capability and merge using the existing runtime evidence
  - or explicitly re-run/relax the monitor-budget probes before merge if a green scripted admin gate is mandatory
