# Planner Mono-Lane Cutover Checklist

## Pre-Check
- [ ] VM runtime confirmed with `bash scripts/runtime_host_check.sh`
- [ ] crontab snapshot captured
- [ ] `parallel-workstreams.json` snapshot captured
- [ ] `priority-queue.json` snapshot captured
- [ ] planner-only compatibility layer already installed (`84f0a4c`)
- [ ] planner-owned subagent manager already installed (`fc086ac`)

## Dry-Run Migration
- [ ] run `python3 platform/automation/migrate_to_planner_monolane.py`
- [ ] inspect `task_changes` and `queue_changes`
- [ ] verify only open non-planner work is targeted
- [ ] verify target execution roles are preserved in report metadata

## Canary Activation
- [ ] run `python3 platform/automation/migrate_to_planner_monolane.py --apply`
- [ ] install `planner-experimental` with `FC_EXPERIMENTAL_PLANNER_ONLY=1`
- [ ] force one planner tick
- [ ] confirm non-planner ticks are ignored with `MONOLANE_ROLE_DISABLED`

## Extended Validation
- [ ] planner cron stays green for 2 cycles
- [ ] planner subagent registry updates under `docs/operations/orchestrator/`
- [ ] dry-run follow-up report returns zero unexpected deltas
- [ ] monitor status remains healthy
- [ ] no stale lock growth after cutover

## Stop Conditions
Rollback immediately if any of the following occur:
- planner tick fails for 2 consecutive cycles
- planner cannot spawn/collect subagent results
- queue/workboard drift grows after migration apply
- monitor health degrades because non-planner lanes are still expected
- planner quota exhaustion forces silent downgrade

## Rollback
- [ ] reinstall `full` profile with `FC_EXPERIMENTAL_PLANNER_ONLY=0`
- [ ] rollback migration using the apply report
- [ ] restore crontab snapshot if needed
- [ ] verify planner/dev/admin lanes are back in the crontab
- [ ] verify `/api/status` health and queue/workboard summary are stable

## Evidence Paths
- `evidence/runtime-gates/planner-monolane-migration-*.json`
- `docs/operations/orchestrator/planner-subagents-registry.json`
- `docs/operations/orchestrator/planner-subagents-events.jsonl`
- `logs-codex-runs/fc-ticks/planner.cron.log`
