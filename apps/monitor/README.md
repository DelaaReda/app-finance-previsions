# FC Monitor

Canonical location for the orchestration monitor dashboard server.

## Entry points

- Canonical server: `apps/monitor/server.py`
- Compatibility wrapper: `scripts/monitor_server.py`

## Run

```bash
python3 scripts/monitor_server.py
```

Server URL: `http://localhost:7779`

## Notes

- Workspace root auto-detection supports VM and macOS paths.
- Override root/state with env vars if needed:
  - `FC_MONITOR_ROOT`
  - `FC_MONITOR_STATE_DIR`

## Planner Troubleshooting Endpoints

- `/api/logs/planner/events` → clean runner events
- `/api/planner/timeline` → planner timeline (deduplicated)
- `/api/planner/log-bundle` → guardian latest + guardian events + planner audit + timeline + runner events
- `/planner-debug` → dedicated Planner Debug page (auto-refresh + score/streaks/issues/reco + logs)
