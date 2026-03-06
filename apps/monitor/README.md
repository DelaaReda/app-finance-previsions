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

- Workspace root is auto-detected from canonical runtime paths.
- Root selection now prefers a writable workspace with valid runtime data
  (`priority-queue.items`, `parallel-workstreams.tasks`, fresh tick/live logs),
  to avoid attaching the UI to stale or read-only mirrored paths.
- Override root/state with env vars if needed:
  - `FC_MONITOR_ROOT`
  - `FC_MONITOR_STATE_DIR`

## API Contract (Runtime)

Core endpoints:
- `/api/status`
- `/api/runtime-diagnostics`
- `/api/dev-parent` (latest dev-parent coaching snapshot, if available)

Contract smoke:

```bash
bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779
```

Health check integration:

```bash
bash scripts/fc_health_check.sh
```

## Planner Troubleshooting Endpoints

- `/api/logs/planner/events` → clean runner events
- `/api/planner/timeline` → planner timeline (deduplicated)
- `/api/planner/log-bundle` → guardian latest + guardian events + planner audit + timeline + runner events
- `/planner-debug` → dedicated Planner Debug page (auto-refresh + score/streaks/issues/reco + logs)
