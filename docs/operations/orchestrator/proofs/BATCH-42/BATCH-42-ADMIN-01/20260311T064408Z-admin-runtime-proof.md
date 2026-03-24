# BATCH-42-ADMIN-01 Runtime Proof

- Timestamp: 2026-03-11T06:44:08Z
- Scope: Geopolitical Risk Graph + Conflict Escalation runtime truth and observability after `BATCH-42-DEV-03`

## Probes

1. `bash scripts/runtime_host_check.sh`
2. `bash scripts/monitor_agents.sh`
3. `bash scripts/stale_cron_sweep.sh --dry-run --threshold 330`
4. `curl -fsS --max-time 16 http://127.0.0.1:8050/api/judge/geopolitical-risk-graph`
5. `pytest apps/api/src/domains/judge/tests/test_judge_route_orchestration.py apps/api/src/domains/judge/tests/test_judge_geopolitical_risk_graph_service.py -q`
6. `node apps/web/src/domains/forecasts/contracts/apiConnector.test.js`
7. `timeout 25 bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779 --timeout 16`
8. `bash scripts/fc_doctor.sh --json`
9. `bash scripts/fc_status_brief.sh`

## Findings

- VM runtime gate passed: `runtime_is_vm=1`.
- Dev chain is live for the task scope:
  - `/api/judge/geopolitical-risk-graph` returned `ok=true` with canonical `judge_geopolitical_risk_graph_service` source markers.
  - Judge route/service regression suite passed: `19 passed`.
  - Forecast connector regression suite passed: `37 passed`.
- Stale state sweep stayed clean: `matched=0 stale=0 reset_failed=0`.
- Monitor observability was degraded when this admin validation started:
  - local listener `127.0.0.1:7779` was down,
  - only the LAN proxy on `192.168.64.9:7780` was still listening,
  - `monitor_contract_smoke.sh` and `fc_status_brief.sh` initially failed against the expected local monitor endpoint.
- Repaired with a reversible runtime action only:
  - restarted the local monitor server with `nohup python3 scripts/monitor_server.py >> logs-codex-runs/monitor-server.log 2>&1 < /dev/null &`.
- Post-repair observability checks passed:
  - listener check showed both `0.0.0.0:7779` and `192.168.64.9:7780`,
  - `monitor_contract_smoke.sh` returned `PASS health=OK roles=1 agents=4 queue_states=4 workboard_ready=0 admin_timeouts_recent=0 issues_records=8`,
  - `fc_status_brief.sh` returned `Santé: OK`,
  - `fc_doctor.sh --json` reported `providers.status=ok`, `monitor_listener_ok=true`, `monitor_status_code=200`.
- Remaining degradation is shared orchestration debt, not a BATCH-42 runtime blocker:
  - `fc_doctor.sh --json` still reports top-level `status=degraded` from queue/workboard mismatch `BATCH-39:queue=IN_PROGRESS:workboard=DONE`.

## Conclusion

- `BATCH-42-ADMIN-01` is runtime-unblocked after local monitor restoration.
- No code or config change was required; only a live monitor restart and proof capture were needed.
- Planner can merge this admin lane and continue to `BATCH-42-GOV_REVIEW`; residual mismatch debt belongs to shared orchestration follow-up, not to the geopolitical graph slice.
