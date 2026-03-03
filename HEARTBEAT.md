# HEARTBEAT.md

# Keep this file empty (or with only comments) to skip heartbeat API calls.

# Add tasks below when you want the agent to check something periodically.

# Contexte 2026-02-28: Migration stabilisée. Lire docs/ops/AGENTS_READY.md avant tout travail.

## 3-Day Memory Strategy Deployment (28-02-2026)

Role agents now auto-load 3-day context window to prevent architecture regression.
- Function: load_3day_memory_context() in scripts/cron_tmux_role_runner.sh
- Loads: last 3 daily logs + role-specific decisions
- Guards: Auto-blocks copilot-app/*, backend/src/backend/src/*, legacy imports

**First Run Check:**
- [ ] Note: current role-runner does not log the injected memory context text, so grepping logs for it is not a reliable verification.
- [ ] Guard check (reliable): No "copilot-app" appears in role-runner logs.
- [ ] If you want positive verification: add a temporary `trace_event "MemoryContext loaded days=3"` inside `load_3day_memory_context()` in `scripts/cron_tmux_role_runner.sh`, then confirm it appears in `logs-codex-runs/role-runner/<role>.live.log`.

Details: docs/ops/ROLE_MEMORY_STRATEGY_3DAY.md

