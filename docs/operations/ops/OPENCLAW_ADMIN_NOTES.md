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
- `agents.defaults.cliBackends.codex-cli` must override the built-in resume path so it does not pass unsupported flags like `--color` or `--sandbox` to `codex exec resume`
- Memory search sources: `["memory"]`
- Session-memory indexing: disabled
- Sync watch: disabled
- Cache max entries: `20000`
- Default verbosity: `on`
- Canonical persistent agents:
  - `main`
  - `planner`
  - `adminapp-codex`
  - `clawsentinel`
- Canonical capability workspaces:
  - `logs-codex-runs/openclaw-capabilities/planner_dev/`
  - `logs-codex-runs/openclaw-capabilities/planner_admin/`
  - `logs-codex-runs/openclaw-capabilities/planner_scrum_master/`

These settings are intentional. They reduce gateway churn and prevent Node OOM under planner-owned subagent load.

## Canonical Planner Bridge
- Config source: `platform/config/runner/runner.v1.yaml`
- Active backend: `features.planner_orchestrator.backend = "openclaw"`
- Planner bridge implementation: `platform/automation/planner_subagent_manager.py`
- OpenClaw control-plane alignment tool: `platform/automation/openclaw_control_plane.py`
- OpenClaw capability workspace provisioning: `platform/automation/worker_manager.py`

## Operator Checks
1. `systemctl --user --no-pager --full status openclaw-gateway.service`
2. `python3 platform/automation/openclaw_control_plane.py --apply --validate-bridge --validate-agent planner --validate-timeout 45`
3. `curl -s http://127.0.0.1:7779/api/status`

Expected:
- gateway active
- control-plane bridge validation returns `bridge_validation.ok=true`
- monitor reports `execution_mode=planner_experimental`

## Log Hygiene
- Active log: `~/.openclaw/logs/gateway-debug.log`
- Archive path: `~/.openclaw/logs/archive/`
- If the active log grows abnormally, archive and recreate it before blaming planner orchestration.

## Non-goals
- Do not reintroduce legacy role-session assumptions (`tester`, `qa`, four-lane watchdog health).
- Do not build a second worker platform on top of OpenClaw.
- Do not let subagents mutate backlog/workboard truth directly.
- Do not launch planner-owned capabilities from repo root when the repo `.codex/config.toml` is incompatible with the OpenClaw Codex parser; use the dedicated capability workspace instead.
- Do not rely on OpenClaw's built-in `codex-cli` backend defaults without the control-plane override; current Codex resume does not accept `--color`.
