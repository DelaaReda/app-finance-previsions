# Orchestration Agents Ready

## Status
This document is now a compatibility note.

Historical multi-lane specialist topology is no longer the target architecture.
The current target is defined in:
- `docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md`
- `docs/ops/AGENTS_READY.md`

## Current Runtime Reality
- one scheduled orchestrator lane: `planner`
- `dev`, `admin`, and `scrum_master` operate as explicit responsibility domains under planner ownership
- planner-owned delegation is handled through `platform/automation/planner_subagent_manager.py`

## Minimal Validation
```bash
bash scripts/fc_doctor.sh --json | jq '.checks.sessions'
cat logs-codex-runs/monitor-lan-url.txt
curl -s http://127.0.0.1:7779/api/status?lite=1 | jq '{execution_mode,core_roles,planner_subagents}'
curl -s http://192.168.64.9:7780/api/status?lite=1 | jq '{execution_mode,core_roles,planner_subagents}'
```

Expected:
- `execution_mode="planner_experimental"`
- `core_roles=["planner"]`
- LAN proxy `7780` available for host-side inspection

## Historical Note
If you are reading older docs that assume specialist cron lanes or wide canonical lane normalization, treat them as historical snapshots, not current source of truth.
