---
status: reference
last_verified: 2026-03-13
related_to:
  - /home/venom/analyse-financiere/docs/ops/MONITOR_ARCHITECTURE_SPEC.md
  - /home/venom/analyse-financiere/docs/ops/reference/AGENT_ACTIVITY_FEED_SPEC.md
---

# Agent Activity Feed — Operations Runbook

Status note:
- reference runbook for the optional activity feed
- not a canonical entrypoint for overall runtime truth
- use together with monitor architecture docs, not instead of them

## Start
```bash
cd /home/venom/analyse-financiere
FC_MONITOR_ACTIVITY_FEED_ENABLED=1 \
FC_MONITOR_ACTIVITY_WINDOW_HOURS=6 \
FC_MONITOR_ACTIVITY_MAX_EVENTS=300 \
FC_MONITOR_DEP_GRAPH_ENABLED=1 \
bash scripts/monitor_stack_guard.sh
cat logs-codex-runs/monitor-lan-url.txt
```

Canonical access:
- VM: `http://127.0.0.1:7779/`
- Mac host: `http://192.168.64.9:7780/`
- tunnels: disabled by default

Reference:
- [MONITOR_ACCESS_RUNBOOK.md](/home/venom/analyse-financiere/docs/ops/reference/MONITOR_ACCESS_RUNBOOK.md)

## Validate
```bash
curl -sS http://127.0.0.1:7779/api/status?lite=1 | jq '.activity_summary'
curl -sS 'http://127.0.0.1:7779/api/agent-activity?window=6&limit=120' | jq '.throughput,.system_summary.current_bottleneck'
curl -sS 'http://127.0.0.1:7779/api/tasks/active?window=6&limit=40' | jq '.items[0]'
curl -sS 'http://127.0.0.1:7779/api/dependencies/map?limit=200' | jq '.summary,.bottlenecks[0]'
curl -sS 'http://192.168.64.9:7780/api/status?lite=1' | jq '.activity_summary'
```

Expected:
- `activity_summary` non-null.
- `timeline` ordered and deduplicated.
- `tasks/active` includes `progress_pct/current_step`.
- `dependencies/map` includes `bottlenecks` when WAITING_DEP exists.

## Recover
If payload is empty or stale:
```bash
bash scripts/fc_health_check.sh --strict
bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779
```
Then verify sources:
- `docs/operations/orchestrator/events.jsonl`
- `logs-codex-runs/role-runner/*.events.log`
- `docs/operations/orchestrator/parallel-workstreams.json`

## Rollback
```bash
cd /home/venom/analyse-financiere
FC_MONITOR_ACTIVITY_FEED_ENABLED=0 bash scripts/monitor_stack_guard.sh
```
This disables the new feed while keeping legacy status/runtime APIs.

## Evidence paths
- `docs/operations/orchestrator/events.jsonl`
- `logs-codex-runs/role-runner/*.events.log`
- `docs/operations/orchestrator/parallel-workstreams.json`
- `docs/operations/orchestrator/priority-queue.json`
