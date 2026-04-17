# Planner Mono-Lane Cutover Runbook

## Purpose
Cut over to planner-only scheduling while keeping `planner` as the canonical runtime role.

Boundary:
- This runbook is VM-local orchestration only.
- The `127.0.0.1:7779` monitor checks below are control-plane checks, not public app-serving checks.

Compatibility notes:
- `planner_architect_orchestrator` is an accepted alias.
- `FC_EXPERIMENTAL_PLANNER_ONLY=1` enables the mono-lane guard.
- `planner-experimental` schedules only the planner lane plus essential infra guards.

## Preconditions
- Run only on the VM workspace: `/home/venom/analyse-financiere`.
- Verify host before any runtime action:

```bash
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/runtime_host_check.sh"
```

Expected:
- `runtime_is_vm=1`

## Snapshot
Capture snapshots before the cutover.

```bash
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "STAMP=\$(date +%Y%m%d_%H%M%S); mkdir -p logs-codex-runs/ops/snapshots; crontab -l > logs-codex-runs/ops/snapshots/crontab.backup.\${STAMP}; cp docs/operations/orchestrator/parallel-workstreams.json logs-codex-runs/ops/snapshots/parallel-workstreams.\${STAMP}.json; cp docs/operations/orchestrator/priority-queue.json logs-codex-runs/ops/snapshots/priority-queue.\${STAMP}.json; tmux ls > logs-codex-runs/ops/snapshots/tmux.\${STAMP}.txt 2>/dev/null || true; echo \${STAMP}"
```

## Dry Run The Migration
Dry-run is mandatory before apply.

```bash
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "python3 platform/automation/migrate_to_planner_monolane.py"
```

Expected:
- JSON payload with `mode=dry_run`
- report path under `evidence/runtime-gates/`
- non-zero `task_changes` only if open non-planner work still exists

## Apply The Migration
Apply only after reviewing the dry-run report.

```bash
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "python3 platform/automation/migrate_to_planner_monolane.py --apply"
```

What it does:
- reassigns open workboard tasks to `planner`
- preserves original execution target under `meta.planner_monolane.planner_subagent_target_role`
- normalizes planner-ready tasks to the canonical planner-ready state
- reassigns open queue items to `owner_role=planner`
- writes a reversible report in `evidence/runtime-gates/`

## Enable Planner-Only Scheduling
Install the mono-lane cron profile.

```bash
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "FC_EXPERIMENTAL_PLANNER_ONLY=1 bash scripts/fc_setup_crons.sh --profile planner-experimental"
```

Optional immediate tick:

```bash
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "FC_EXPERIMENTAL_PLANNER_ONLY=1 bash scripts/fc_agent_tick.sh planner"
```

## Validate
Run these checks after cutover.

```bash
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "crontab -l | rg 'planner-experimental|fc_agent_tick\.sh planner|monitor_stack_guard|cleanup_stale_role_locks'"
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "python3 platform/automation/migrate_to_planner_monolane.py --report evidence/runtime-gates/latest-planner-monolane-check.json"
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "curl -sS http://127.0.0.1:7779/api/status | jq '{health,doctor,agents:.agents|keys,queue:.queue.state_counts}'"
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "tail -n 120 logs-codex-runs/fc-ticks/planner.cron.log"
```

Expected:
- planner ticks continue with `rc=0`
- non-planner cron lanes are not scheduled in planner-experimental profile
- follow-up dry-run shows `task_changes=0` or only known intentional deltas
- planner-owned subagents are visible through `planner_subagent_manager.py status`

## Rollback
Restore parallel scheduling first, then rollback the migration with the apply report.

```bash
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "FC_EXPERIMENTAL_PLANNER_ONLY=0 bash scripts/fc_setup_crons.sh --profile full"
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "python3 platform/automation/migrate_to_planner_monolane.py --rollback --report evidence/runtime-gates/<apply-report>.json"
```

If needed, restore the crontab snapshot directly:

```bash
platform/policies/exec_safe.sh --workdir /home/venom/analyse-financiere -- "crontab logs-codex-runs/ops/snapshots/crontab.backup.<STAMP>"
```

## Evidence
- `evidence/runtime-gates/planner-monolane-migration-*.json`
- `docs/operations/orchestrator/parallel-workstreams.json`
- `docs/operations/orchestrator/priority-queue.json`
- `docs/operations/orchestrator/planner-subagents-registry.json`
- `docs/operations/orchestrator/planner-subagents-events.jsonl`
- `logs-codex-runs/fc-ticks/planner.cron.log`
