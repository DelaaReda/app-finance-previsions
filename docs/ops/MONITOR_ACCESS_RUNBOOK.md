# Monitor Access Runbook

## Purpose
Define the canonical access paths for FC Monitor.

The monitor is now operated in `LAN-only` mode by default.
Public tunnels are disabled to avoid ambiguous URLs and stale health signals.

## Canonical Access Paths

### From inside the VM
- UI: `http://127.0.0.1:7779/`
- lightweight status: `http://127.0.0.1:7779/api/status?lite=1`
- doctor: `http://127.0.0.1:7779/api/doctor?refresh=1`

### From the macOS host
- UI: `http://192.168.64.9:7780/`
- lightweight status: `http://192.168.64.9:7780/api/status?lite=1`

The `7780` endpoint is a VM-side LAN proxy that forwards to local monitor port `7779`.

## Source Of Truth
- current LAN URL file: `logs-codex-runs/monitor-lan-url.txt`
- local monitor process: `apps/monitor/server.py`
- LAN proxy process: `scripts/monitor_lan_proxy.py`
- guard/orchestration: `scripts/monitor_stack_guard.sh`

## Operating Rules
- Treat the LAN URL as the canonical host-facing monitor link.
- Do not treat `loca.lt` or `localhost.run` URLs as canonical runtime access.
- Public tunnels remain opt-in only via `FC_MONITOR_MANAGE_TUNNEL=1`.

## Quick Checks
```bash
cat logs-codex-runs/monitor-lan-url.txt
curl -sS http://127.0.0.1:7779/api/status?lite=1 | jq '{health,execution_mode,core_roles}'
curl -sS http://192.168.64.9:7780/api/status?lite=1 | jq '{health,execution_mode,core_roles}'
```

Expected:
- VM-local `7779` responds.
- host-facing LAN proxy `7780` responds.
- `monitor-lan-url.txt` matches the current VM LAN address.

## Recovery
```bash
bash scripts/monitor_stack_guard.sh
cat logs-codex-runs/monitor-lan-url.txt
```

If a public tunnel is still running unexpectedly:
```bash
pkill -f 'localtunnel|localhost.run|/bin/lt' || true
```
