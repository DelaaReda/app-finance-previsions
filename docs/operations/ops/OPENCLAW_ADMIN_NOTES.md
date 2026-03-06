# OpenClaw Admin Notes

## Current Runtime Truth
- OpenClaw is the runtime/session transport layer under the planner orchestrator.
- Planner remains the only scheduled orchestration role.
- `dev`, `admin`, and `scrum_master` are planner-owned capabilities, not independent cron lanes.

## Active Gateway Baseline
- Service: `systemctl --user status openclaw-gateway.service`
- Heap baseline: `--max-old-space-size=1024`
- Semi-space baseline: `--max-semi-space-size=32`
- Expected state: `active (running)` without restart loop

## Active Config Baseline
- Config file: `~/.openclaw/openclaw.json`
- Logging level: `warn`
- Console logging: `warn`
- Memory search sources: `["memory"]`
- Session-memory indexing: disabled
- Sync watch: disabled
- Cache max entries: `20000`
- Default verbosity: `on`

These settings are intentional. They reduce gateway churn and prevent Node OOM under planner-owned subagent load.

## Canonical Planner Bridge
- Config source: `platform/config/runner/runner.v1.yaml`
- Active backend: `features.planner_orchestrator.backend = "openclaw"`
- Planner bridge implementation: `platform/automation/planner_subagent_manager.py`

## Operator Checks
1. `systemctl --user --no-pager --full status openclaw-gateway.service`
2. `openclaw agent --agent planner --json --thinking low --timeout 60 --message 'Reply with exactly {\"status\":\"ok\"}'`
3. `curl -s http://127.0.0.1:7779/api/status`

Expected:
- gateway active
- OpenClaw probe returns JSON
- monitor reports `execution_mode=planner_experimental`

## Log Hygiene
- Active log: `~/.openclaw/logs/gateway-debug.log`
- Archive path: `~/.openclaw/logs/archive/`
- If the active log grows abnormally, archive and recreate it before blaming planner orchestration.

## Non-goals
- Do not reintroduce legacy role-session assumptions (`tester`, `qa`, four-lane watchdog health).
- Do not build a second worker platform on top of OpenClaw.
- Do not let subagents mutate backlog/workboard truth directly.
