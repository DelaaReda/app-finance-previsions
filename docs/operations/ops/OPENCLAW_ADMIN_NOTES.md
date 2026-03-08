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
- Main WhatsApp agent policy:
  - `main` must use `codex-cli-main/gpt-5.4`
  - default OpenClaw thinking must remain `xhigh`
  - `main.workspace` must be `/home/venom`
  - `main` is the broad-access director agent for WhatsApp-driven requests across the VM/project
  - `main.memorySearch.extraPaths` must include repo `SOUL.md`, `USER.md`, `MEMORY.md`, `memory/`, docs paths, and OpenClaw workspace memory
  - `channels.whatsapp.enabled` must stay `true` with allowlist access for `+14389799898`
  - `codex-cli-main` must run `codex exec --dangerously-bypass-approvals-and-sandbox`
  - validated director scope:
    - VM write/read works from `main`
    - project memory/doc reads work from `main`
    - `sudo` write/read/delete works from `main` on the current gateway/runtime
  - do not add `thinkingDefault` under `agents.list[].main`; OpenClaw rejects that schema and the gateway will fail to load
- Planner/control-plane policy:
  - `planner` now runs as the full-rights team lead on `codex-full/gpt-5.4` with `thinking=xhigh`
  - `adminapp-codex` and `clawsentinel` remain on the narrower `codex-cli/gpt-5.4`
  - keep their dedicated capability/control-plane workspaces under `logs-codex-runs/openclaw-control-plane/`
  - `planner` may repair orchestration/config/spec/runtime/backend blockers directly when that is the shortest path to restore delivery
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
