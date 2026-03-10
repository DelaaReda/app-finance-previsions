# BATCH-15-ADMIN-01 Runtime Proof

- Timestamp UTC: `2026-03-10T12:39:00Z`
- Scope: Strategy Playbooks Engine admin validation after `BATCH-15-DEV-03`
- Runtime host: VM (`runtime_is_vm=1`)

## Root Cause

`apps/monitor/server.py` was recomputing planner subagent state repeatedly inside one `/api/status` request path. In planner-only mode, non-planner `contract()` reads call `_contract_is_stale_for_planner_mode()`, which re-entered `_active_planner_subagent_roles()` and therefore `planner_subagent_manager.status_snapshot(...)`. The cold monitor path crossed the 8s probe timeout and made runtime observability look down even when port `7779` was serving.

## Fix Applied

- Added a short-lived monitor-side cache for planner subagent snapshots in `apps/monitor/server.py`.
- Cache timestamp now records completion time, so the first expensive snapshot can be reused by later checks in the same request window.

## Verification

- `bash scripts/runtime_host_check.sh`
  - `runtime_host_kind=vm_runtime`
  - `runtime_is_vm=1`
- Cold local timing after patch, measured against live monitor on `127.0.0.1:7779`:
  - `/api/status?lite=1` → `OK` in `1.204s`
  - `/api/status` → `OK` in `3.153s`
  - `/api/runtime-diagnostics?lite=1` → `OK` in `8.320s`
  - `/api/runtime-diagnostics` → `OK` in `1.860s`
- Contract probes:
  - `bash scripts/fc_status_brief.sh` → `Santé: OK · mode=planner_experimental`
  - `bash scripts/monitor_contract_smoke.sh --quiet` → exit `0`
- Strategy Playbooks checks:
  - `python3 -m pytest apps/api/src/domains/judge/tests/test_judge_route_orchestration.py -k 'strategy_playbook or signal_divergence' -q` → `6 passed`
  - `node --test apps/web/src/domains/forecasts/tests/test-strategy-playbooks-widget.js` → `pass`

## Notes

- Broader monitor unit suite still has pre-existing failures outside this fix scope:
  - `apps/monitor/tests/test_status_planner_dev_policy.py::test_status_autoheals_admin_runtime_stale_blocker`
  - `apps/monitor/tests/test_task_progress.py::test_task_progress_boosts_with_artifact_and_test`
