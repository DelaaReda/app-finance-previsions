# TMUX Cron Operations Runbook

## Scope
This runbook documents the active OpenClaw cron profile that dispatches role turns into persistent tmux sessions.

Team admin workflow reference:
- `docs/ops/ADMIN_TEAM_CRON_PLAYBOOK.md`
- `docs/ops/ADMIN_TEAM_ITERATIONS.md`
- `docs/ops/AGENT_ROLE_INTEGRATION_MODEL.md`
- `docs/ops/PARALLEL_SCRUM_DELIVERY_MODEL.md`
- `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
- `docs/orchestrator-ops/parallel-role-topology.json`

Named admin triad (for signed updates):
- `adminapp-codex`
- `admin-agents`
- `clawsentinel`

## Governance routing gate (mandatory)
- Operational governance reference: `docs/ops/OPERATIONAL_GOVERNANCE.md`.
- Accepted command flow for runtime actions:
  - `main -> admins -> equipe de livraison`
  - `equipe de livraison -> admins -> main`
- If a request bypasses admins, stop and reroute through admin docs:
  - `docs/ops/ADMIN_TEAM_CHAT.md`
  - `docs/ops/ADMIN_TEAM_ITERATIONS.md`

## Runtime profile (active baseline: 2026-02-26)
- OpenClaw runs 17 cron jobs: 14 role loops + 2 admin loops + 1 stale auto-heal utility.
- Source of truth:
  - `openclaw cron list --all`
  - `/home/venom/.openclaw/cron/jobs.json`
  - `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
- Payload policy:
  - runner-only (`bash scripts/cron_tmux_role_runner.sh <role>`)
- Defaults observed/expected:
  - `thinking=high`
  - `timeoutSeconds=900`
  - `PROMPT_TIMEOUT_SECONDS=180`
  - `RETRY_PROMPT_TIMEOUT_SECONDS=90`
  - `TMUX_ROLE_STALL_ABORT_SECONDS=75`
  - `TMUX_ROLE_NO_DELTA_THRESHOLD=12`
  - `TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk`
  - `TMUX_ROLE_CODEX_EXEC_RESUME=1`
- Evidence schema:
  - `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`
  - `run_note` is mandatory (>= 5 words) to make future troubleshooting easier.
- Restart checklist for admin agents:
  - `docs/ops/ADMIN_POST_RESTART_RUNBOOK.md`

### Legacy snapshot (2026-02-25 11:17 EST)
- 10 cron jobs (core profile). Kept for historical reference only.

## Multi-session coordination protocol (mandatory)
Use this when 2+ agents can edit cron settings at the same time.

1. Claim an edit window in `docs/orchestrator-ops/agent-watchdog.md` with timestamp + owner + target change.
2. Back up the current scheduler file before any edit:
   - `cp /home/venom/.openclaw/cron/jobs.json /home/venom/.openclaw/cron/jobs.json.backup-$(date +%Y%m%d-%H%M%S)`
3. Refresh job IDs just before editing:
   - `openclaw cron list`
4. Apply the smallest possible change (prefer editing one job at a time).
5. Force one validation run for the edited job:
   - `openclaw cron run <job-id> --expect-final --timeout 900000`
6. Record result and release the edit window in `agent-watchdog.md` (success/failure + rollback note).
7. Add signed iteration notes from all 3 admins in `docs/ops/ADMIN_TEAM_ITERATIONS.md`, then mirror runtime decision in `agent-watchdog.md`.

## Live monitoring checklist
Run this checklist in order:

1. Scheduler overview:
   - `openclaw cron list`
2. Last runs for each active job:
   - `openclaw cron runs --id <job-id> --limit 5`
   - Parser robuste multi-format:
     - `openclaw cron runs --id <job-id> --limit 5 | python3 scripts/openclaw_cron_runs_normalize.py`
3. Executor-level auto-monitoring (sans logs bruts):
   - `jq '.summary' docs/orchestrator-ops/executors-monitoring-latest.json`
   - `tail -n 5 docs/ops/AGENT_TOOL_REQUESTS.md`
   - `bash scripts/dg_alert_15m.sh`
4. Watch for these failure patterns:
   - `Error: cron: job execution timed out`
   - summary polluted by shell noise (`clear`, prompt echoes, terminal banners)
   - missing structured fields (`STATUS`, `DELTA`, `EVIDENCE`, `RISKS`, `NEXT`, `VERDICT`, `BLOCKER_ID`, `NEXT_ACTION_UNIQUE`)
   - `EVIDENCE` missing end-of-execution report keys (`exec_report`, `issues`, `suggestions`) or `issues!=none` with `suggestions=none`
5. If IDs changed unexpectedly, treat previous monitoring links as stale and refresh from `openclaw cron list`.

## Quick controls (new)
For day-to-day runtime operations, use `scripts/cron_run_manager.sh`:

1. Runtime snapshot:
   - `bash scripts/cron_run_manager.sh status --stale-threshold 330`
2. Pause / Resume one job:
   - `bash scripts/cron_run_manager.sh pause --job planner`
   - `bash scripts/cron_run_manager.sh resume --job planner`
3. Stop one active run cleanly (disable + session/process stop + re-enable):
   - `bash scripts/cron_run_manager.sh stop-run --job planner --reason manual_intervention`
4. Trigger one job immediately (non-blocking by default):
   - `bash scripts/cron_run_manager.sh run-now --job planner`
   - `bash scripts/cron_run_manager.sh run-now --job planner --expect-final --timeout 300000`
5. Restart one job run (stop + run-now):
   - `bash scripts/cron_run_manager.sh restart --job planner --reason manual_restart`
6. Read latest run summaries:
   - `bash scripts/cron_run_manager.sh last-summary --job planner --limit 3`
7. Sweep stale scheduler states:
   - `bash scripts/cron_run_manager.sh recover-stale --dry-run --threshold 330`

## Debug log sanitation
Current default behavior:
- tmux pane logs are cleaned at stream time via `scripts/tmux_log_clean_stream.py`
- retention is kept per run/iteration (`finance-app/orchestrator-runs/<run-id>/tmux/*.log`)

Live monitor (codex cron sessions):
- capture-based near-real-time monitor (recommended for detached codex TUI sessions):
  - `bash scripts/tmux_codex_live_monitor.sh --mode follow --engine capture`
- watchdog helper (persistent background monitor in dedicated tmux session):
  - `bash scripts/tmux_live_watchdog.sh start`
  - `bash scripts/tmux_live_watchdog.sh status`
  - `bash scripts/tmux_live_watchdog.sh stop`
- pipe-pane attach/detach (raw stream troubleshooting):
  - `bash scripts/tmux_codex_live_monitor.sh --mode start --force-repipe`
  - `bash scripts/tmux_codex_live_monitor.sh --mode follow --engine pipe --lines 120`
  - `bash scripts/tmux_codex_live_monitor.sh --mode stop`
- default log directory:
  - `logs-codex-runs/tmux-live/`
- runner execution trace logs (per role, near-real-time):
  - `logs-codex-runs/role-runner/<role>.live.log`
  - included automatically by `tmux_codex_live_monitor.sh` (disable with `--no-runner-trace`)

If you need a post-processing pass:

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/clean_tmux_logs.sh --mode compact finance-app/orchestrator-runs"
```

Outputs:
- per file: `*.clean.log` in the same `tmux/` directory
- if no actionable signal exists: `NO_DEBUG_SIGNAL: ...` marker in the clean file

For retention-by-iteration, keep raw stream logs and use clean mirrors.
`--purge-raw` exists but is not recommended for normal operations.

Quick example:
- raw: `finance-app/orchestrator-runs/<run-id>/tmux/codex_architect_cron.log`
- clean: `finance-app/orchestrator-runs/<run-id>/tmux/codex_architect_cron.clean.log`

## Legacy observations (2026-02-25 11:17 EST)
- Active profile is stable at scheduler level (`lastStatus=ok`, with expected transient `running` while a job is in flight).
- Forced validations on `planner/dev/tester/qa` returned `ok:true` with structured 8-key summaries.
- Parse reliability improved after runner fix (heredoc stdin parse bug removed), but business-signal quality still needs work (`NO_DELTA` remains high on some roles).
- Job IDs can still churn during concurrent edits; monitoring commands tied to stale IDs can return empty results.

## Notes (2026-02-26)
- `tmux_codex_live_monitor.sh` resolves specialist sessions dynamically and writes runner trace lines into `logs-codex-runs/tmux-live/<session>.log` so logs stay useful even when pane output is empty.
- Runner gate for no-ready periods:
  - editing roles auto-fallback to analysis mode when queue has no `READY` item,
  - `NO_DELTA` streak escalation is suppressed when `queue_has_ready=0` to avoid false `NO_PROGRESS_STREAK`.

## Improvement backlog (next doc-driven hardening)
1. Keep `timeoutSeconds=900`; tune down only with measured evidence (p95 duration, timeout rate, false BLOCKED rate).
2. Keep one canonical runner script for tmux role turns (`cron_tmux_role_runner.sh`) and maintain `cron_tmux_role_turn.sh` as compatibility wrapper only.
3. Enforce a strict edit-window protocol before any cron rewrite to prevent ID churn and stale monitors.
