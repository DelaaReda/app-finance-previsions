# BATCH-15-ADMIN-01 Runtime Proof

- Timestamp: 2026-03-10T14:47:48Z
- Scope: Strategy Playbooks Engine runtime and observability only
- Workspace: `/home/venom/analyse-financiere`
- HEAD: `19b80d6f47f62d6139db6cc700e96848300a1663`

## Host and runtime truth

- `bash scripts/runtime_host_check.sh`
  - `runtime_host_kind=vm_runtime`
  - `runtime_is_vm=1`
  - `pwd=/home/venom/analyse-financiere`
- `bash scripts/fc_status_brief.sh`
  - `Sante: OK`
  - `mismatch_count=0`
  - `waiting_dep=10`
  - `planner_quality=100`
- `bash platform/automation/stale_cron_sweep.sh --dry-run`
  - `matched=0 stale=0 reset_ok=0 reset_failed=0 skipped_live=0 skipped_timeout=0`

## Observability probes

- `bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779`
  - `PASS health=OK roles=1 agents=4 queue_states=4 workboard_ready=0 admin_timeouts_recent=0 issues_records=1`
- `bash scripts/health_snapshot.sh`
  - `health=STALE`
  - `stale=[]`
  - `critical_widgets=stale`
- `bash scripts/fc_doctor.sh --json`
  - top-level `status=degraded`
  - `checks.sessions.status=ok`
  - `checks.queue_workboard.status=ok`
  - `checks.providers.status=ok`
  - `checks.product_value.status=degraded`
  - degraded reason is shared freshness debt (`blocked_reasons=["news_stale"]`), not a Strategy Playbooks runtime failure

## Strategy Playbooks lane checks

- `pytest -q apps/api/src/domains/judge/tests/test_strategy_playbooks.py apps/api/src/domains/judge/tests/test_strategy_playbooks_live_data.py`
  - `22 passed`
- `node --test apps/web/src/domains/forecasts/tests/test-strategy-playbooks-widget.js`
  - `1 suite passed`
  - widget assertions: `6/6 passed`

## Conclusion

- No Strategy Playbooks runtime, stale-lock, or broken execution-path defect is present in current task scope.
- Batch lane remains runtime-unblocked after the DEV chain.
- Remaining noise is shared observability debt only:
  - `health_snapshot.sh` still rolls up `critical_widgets=stale`
  - `fc_doctor.sh --json` is top-level `degraded` because `news_stale` is outside this batch lane
