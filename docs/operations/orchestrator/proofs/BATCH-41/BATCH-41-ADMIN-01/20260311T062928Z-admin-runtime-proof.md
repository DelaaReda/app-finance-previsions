# BATCH-41-ADMIN-01 Runtime Proof

- Timestamp: 2026-03-11T06:29:28Z
- Scope: Free Global Signal Mesh runtime truth and observability after `BATCH-41-DEV-03`

## Probes

1. `bash scripts/runtime_host_check.sh`
2. `bash scripts/monitor_agents.sh`
3. `bash scripts/stale_cron_sweep.sh --dry-run --threshold 330`
4. `timeout 25 bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779 --timeout 16`
5. `bash scripts/fc_doctor.sh --json`
6. `curl -fsS --max-time 16 http://127.0.0.1:8050/api/forecasts/global-signal-mesh`
7. `pytest apps/api/src/domains/forecasts/tests/test_global_signal_mesh_route.py -q`

## Findings

- VM runtime gate passed: `runtime_is_vm=1`.
- Runtime scheduler is live on the VM and scoped to planner-owned capability execution.
- Monitor surface is healthy for the task scope:
  - `monitor_contract_smoke.sh` returned `PASS health=OK roles=1 agents=4 queue_states=4 workboard_ready=0 admin_timeouts_recent=0 issues_records=8`.
  - `fc_doctor.sh --json` reported `providers.status=ok`, `api_status=200`, `monitor_status_code=200`, `monitor_listener_ok=true`, `api_listener_ok=true`.
- Stale state sweep was clean: `matched=0 stale=0 reset_failed=0`.
- Task endpoint is healthy:
  - `/api/forecasts/global-signal-mesh` returned `ok=true`.
  - payload includes BATCH-41 runtime-visible contract fields: `sources_catalog`, per-source `health`, top-level `observability`, `coverage.free_nominal_path_only=true`, and SLA freshness `within_target=true`.
- Contract verification passed: `pytest apps/api/src/domains/forecasts/tests/test_global_signal_mesh_route.py -q` -> `18 passed`.
- Residual degradation is shared orchestration debt, not a BATCH-41 runtime blocker:
  - `monitor_agents.sh` still shows planner `GO_WITH_CAUTION` with historical `invalid_subagent_result`, `admin_retry_ready`, and `manager_stat`.
  - `fc_doctor.sh --json` remains top-level `status=degraded` because planner dispatch observability still tracks an active capability and unrelated historical browser-proof debt (`VB-04-ADMIN-01`).

## Conclusion

- `BATCH-41-ADMIN-01` is runtime-unblocked.
- No task-scoped runtime or observability repair was required.
- Planner can merge this admin lane and continue to `BATCH-41-GOV_REVIEW`; only shared planner-control-plane observability debt remains outside this batch scope.
