# Parallel Plumbing Quickstart

Canonical orchestration spec (source de verite):
- `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`

## 1) Bootstrap persistent OpenClaw agents (dry-run then apply)
```bash
scripts/bootstrap_openclaw_agents.sh
scripts/bootstrap_openclaw_agents.sh --apply --full-access
```

## 2) Prepare workstreams
```bash
scripts/parallel_workstream.py init --force
scripts/parallel_workstream.py sync-priority --include-pass
scripts/parallel_workstream.py validate
```
Notes:
- Stream template ends with `GOV_REVIEW` in planner lane (planner absorbs governance task flow).
- `po` and `scrum_master` remain valid roles for channels/status visibility and cross-role impact reporting.

## 3) Provision specialized role crons (dry-run first)
```bash
scripts/configure_parallel_team_crons.sh
```

## 4) Apply cron provisioning when ready
```bash
scripts/configure_parallel_team_crons.sh --apply --enable
```
This also provisions a dedicated auto-heal cron:
- `stale-sweep-autoheal-7m` (agent `adminapp-codex`)

## 5) Run orchestration mode
- Admin-only monitoring:
```bash
scripts/set_orchestration_mode.sh --mode admins-only
```
- Full parallel execution:
```bash
scripts/set_orchestration_mode.sh --mode parallel
```

## 6) Health checks
```bash
scripts/validate_parallel_plumbing.sh
openclaw cron list --all
python3 scripts/parallel_workstream.py context --role planner --limit 3
bash scripts/stale_cron_sweep.sh --dry-run --threshold 330
bash scripts/cron_cleanup_duplicates.sh --dry-run --regex '(-tmux-loop$|adminapp-codex-sync-10m$|admin-agents-supervisor-15m$|stale-sweep-autoheal-7m$|dg-alert-15m$)'
python3 scripts/workboard_stale_task_sweep.py --threshold-seconds 14400
bash scripts/dev_quality_gate.sh --all --no-pre-commit
# Find the job id for "stale-sweep-autoheal-7m" from `openclaw cron list --all`, then:
openclaw cron runs --id <stale_job_id> --limit 1
```
Role runner behavior baseline:
- `TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk`
- `TMUX_ROLE_CODEX_EXEC_RESUME=1`
- delivery mode for editing roles is queue-first (no `READY` in queue => analysis mode fallback)

Evidence schema (contract quality):
- `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`
- Contract guard implementation: `scripts/role_contract_guard.py`
- Role memory append module: `scripts/role_memory_append.py`
- Execution monitoring publish module: `scripts/role_execution_monitoring.py`
- Runtime context builder module: `scripts/role_runtime_context.py`
- Guard tests:
```bash
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
```

Near-real-time troubleshooting:
```bash
bash scripts/tmux_codex_live_monitor.sh --mode follow --engine capture --include-admin
bash scripts/tmux_live_watchdog.sh start
bash scripts/tmux_live_watchdog.sh status
bash scripts/dg_alert_15m.sh
```
- Consolidated live logs: `logs-codex-runs/tmux-live/`
- Per-role execution trace: `logs-codex-runs/role-runner/<role>.live.log`
- Effortless status (no raw logs):
  - `docs/orchestrator-ops/executors-monitoring-latest.json`
  - `docs/ops/AGENT_TOOL_REQUESTS.md`

## 7) Daily cadence
- Dispatch + flow check:
  - `scripts/parallel_workstream.py status --role planner --compact`
  - `scripts/parallel_workstream.py status --role po --compact`
  - `scripts/parallel_workstream.py status --role scrum_master --compact`
- Role wake-up context check:
  - `scripts/parallel_workstream.py context --role <role> --limit 3`
- Publication channels + impact check (obligatoire avant action):
  - `scripts/parallel_workstream.py channels --role <role> --limit 5`
- Role claim/complete examples:
- `scripts/parallel_workstream.py claim --role backend_engineer --change-plan "1) scope ... ; 2) dependency impact ... ; 3) risk ... ; 4) verification/tests ... ; 5) rollback/fallback ..."` --architecture-checks "forecast_contract; schema_stability; observability"`
- `scripts/parallel_workstream.py complete --role backend_engineer --task <TASK_ID> --artifact <FILE_OR_TEST> --handoff-to integrator --change-plan "..." --architecture-checks "..."`
  - `scripts/parallel_workstream.py handoff-ack --handoff <HANDOFF_ID> --role integrator`

Reflection hardening (delivery roles):
- Claims must satisfy 5 reflection dimensions in pre-change checks: `scope`, `dependency_impact`, `risk`, `verification`, `rollback`.
- Delivery contracts (`task_update=claim|complete|handoff`) must include:
  - `reflection_passes>=2` (or higher if runtime config sets a stricter threshold)
  - `reflection_dimensions=scope,dependency_impact,risk,verification,rollback`
- Runner parameter: `TMUX_ROLE_MIN_REFLECTION_PASSES` (default `2`, configurable in cron provisioning scripts).
