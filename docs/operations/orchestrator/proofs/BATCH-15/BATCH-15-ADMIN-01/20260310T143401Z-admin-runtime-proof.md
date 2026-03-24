# BATCH-15-ADMIN-01 Runtime Proof

- Timestamp: 2026-03-10T14:34:01Z
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
- `bash scripts/stale_cron_sweep.sh --dry-run`
  - `matched=0 stale=0 reset_ok=0 reset_failed=0`

## Observability probes

- `bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779`
  - first run timed out at the default `8s` curl window
- `bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779 --timeout 16`
  - `PASS health=OK roles=1 agents=4 queue_states=4 workboard_ready=0 admin_timeouts_recent=0 issues_records=1`
- `bash scripts/health_snapshot.sh`
  - `health=STALE`
  - `stale=[]`
  - `critical_widgets=stale`
- `bash scripts/fc_doctor.sh --json`
  - top-level `status=ok`
  - `checks.sessions.status=ok`
  - `checks.queue_workboard.status=ok`
  - `checks.providers.status=ok`
  - `checks.product_value.status=ok`

## Strategy Playbooks lane checks

- `curl -fsS "http://127.0.0.1:8050/api/judge/strategy-playbooks?symbol=SPY&profile=equity_1w&limit=1"`
  - HTTP path returned `ok=true`
  - payload included `playbooks[0].playbook_id="AAPL:1w:no_go:equity_1w"`
  - warnings were non-blocking runtime degradation only: `decision_journal_store_unavailable`
- `cd apps/api/src && PYTHONPATH=/home/venom/analyse-financiere:/home/venom/analyse-financiere/apps/api/src pytest domains/judge/tests/test_strategy_playbooks.py domains/judge/tests/test_judge_route_orchestration.py`
  - `25 passed in 0.93s`
- `cd apps/web/src/domains/forecasts && node tests/test-strategy-playbooks-widget.js && node tests/test-widget-playbook-integration.js && node tests/test-playbook-integration.js`
  - widget test: `6/6 passed`
  - widget integration test: `14/14 passed`
  - playbook integration test: `29 passed, 0 failed`

## Conclusion

- No Strategy Playbooks runtime, stale-lock, or broken execution-path defect is present in current task scope.
- Batch lane is runtime-unblocked.
- Remaining noise is shared observability debt:
  - default monitor smoke timeout is too tight for some runs
  - `health_snapshot.sh` still rolls up `critical_widgets=stale` despite lane-scoped probes passing
