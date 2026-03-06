# ARCH Batches Runtime Refactor — 2026-03-06

Superseded for current target architecture.

This file is a historical implementation snapshot.
Current canonical execution roadmap is:
- `docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md`
- `docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md`

## Scope delivered
- S1: Admin stale runtime blocker override on live probes.
- S2: Planner evidence incomplete softened to `GO_WITH_CAUTION` with runtime markers.
- S3: Scrum advisory auto-intents hardened to soft-fail (no fatal tick).
- S4: DEV throughput and anti-claim-loop controls.
- S5: Doctor/Monitor state-equivalence alignment (`READY_DEV/READY_PLANNER`).

## Files changed (runtime core)
- `platform/automation/admin_dispatcher_tick.sh`
- `platform/automation/cron_tmux_role_runner.sh`
- `platform/policies/role_contract_guard.py`
- `platform/automation/fc_doctor.py`
- `apps/monitor/server.py`

## Rollback switches
- `FC_ADMIN_RUNTIME_OVERRIDE_ON_LIVE_PROBE=0`
- `FC_PLANNER_EVIDENCE_STRICT=1`
- `FC_DEV_WIP_TARGET=1`
- `FC_DEV_CLAIM_LOOP_BREAKER=0`
- `FC_DEV_SAME_TASK_CLAIM_COOLDOWN_S=0`

## Evidence paths
- Runtime gate proof: `docs/operations/orchestrator/proofs/runtime-gate/`
- Dispatcher logs: `logs-codex-runs/fc-ticks/admin.dispatch.log`
- Role contracts: `${HOME}/.openclaw/cron/role-state/*.last_contract`
- Monitor diagnostics: `/api/runtime-diagnostics`
