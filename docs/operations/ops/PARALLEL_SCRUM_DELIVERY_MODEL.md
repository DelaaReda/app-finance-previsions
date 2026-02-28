# Parallel Scrum Delivery Model (Codex Agents)

## Goal
Accelerate delivery on backend, frontend, integration, data, infra, and QA in parallel
without losing control of dependencies, validation ownership, or handoffs.

## Team topology
- Analysis: `planner`, `analyst`, `architect`
- Build lanes: `backend_engineer`, `frontend_engineer`, `data_analyst`, `infra_engineer`
- Validation lanes: `tester`, `qa`
- Integration lane: `integrator`
- Delivery governance: `planner` (scope/value + flow/WIP) + `admin-agents` (routing/escalations)
- Reliability/safety: `adminapp-codex`, `admin-agents`, `clawsentinel`

## Plumbing artifacts
- Workboard engine: `scripts/parallel_workstream.py`
- Workboard state: `docs/orchestrator-ops/parallel-workstreams.json`
- Parallel cron provisioning: `scripts/configure_parallel_team_crons.sh`
- Role/cron map generated: `docs/orchestrator-ops/parallel-role-cron-map.json`
- Parallel plumbing validator: `scripts/validate_parallel_plumbing.sh`
- Role wake-up context feed: `scripts/parallel_workstream.py context --role <role>`
- Publication channels feed: `scripts/parallel_workstream.py channels --role <role>`
- Persistent per-role execution memory: `/home/venom/.openclaw/cron/role-state/<role>.last_contract`
- Stale-running cron recovery sweep: `scripts/stale_cron_sweep.sh`
  - dedicated cron lane: `stale-sweep-autoheal-7m` (agent `adminapp-codex`)

## Operating loop
1. Sync streams from priority queue:
   - `scripts/parallel_workstream.py sync-priority --include-pass`
2. Each role claims one READY task:
   - `scripts/parallel_workstream.py claim --role <role> --change-plan "<plan_reasoned>" --architecture-checks "<checks_reasoned>"`
3. Role executes and completes with artifact + handoff:
   - `scripts/parallel_workstream.py complete --role <role> --task <task_id> --artifact <proof> --handoff-to <next_role> --change-plan "<plan_reasoned>" --architecture-checks "<checks_reasoned>"`
4. Receiver acknowledges handoff:
   - `scripts/parallel_workstream.py handoff-ack --handoff <id> --role <receiver_role>`
5. Admin triad monitors flow and resolves drift:
   - `admin-agents` assigns owner/scope
   - `adminapp-codex` auto-executes runtime actions or routes external handoffs
   - `clawsentinel` handles quality-signal and anti-drift

## Stream template (per batch)
- `PLAN` (planner)
- `ANALYSIS` (analyst, depends on `PLAN`)
- `ARCH` (architect, depends on `ANALYSIS`)
- `QA_PREP` (qa, depends on `PLAN`)
- `TEST_PLAN` (tester, depends on `PLAN`)
- `DATA` (data_analyst, depends on `ANALYSIS`)
- `INFRA` (infra_engineer, depends on `ARCH`)
- `BACKEND` (backend_engineer, depends on `ARCH`)
- `FRONTEND` (frontend_engineer, depends on `ARCH`)
- `DEV` (dev, depends on `ARCH`)
- `INTEGRATION` (integrator, depends on `BACKEND`, `FRONTEND`, `INFRA`, `DATA`, `DEV`)
- `QA_EXEC` (qa, depends on `INTEGRATION`, `QA_PREP`, `TEST_PLAN`)
- `SENTINEL_CHECK` (clawsentinel, depends on `QA_EXEC`)
- `GOV_REVIEW` (planner, depends on `QA_EXEC` + `SENTINEL_CHECK`)

Legacy note:
- `PO_REVIEW` and `SCRUM_REVIEW` are deprecated (planner absorbs governance). If older boards still contain them, `scripts/parallel_workstream.py sync-priority` prunes non-DONE legacy tasks automatically.

## Why QA can work in parallel
- Each stream creates `QA_PREP` and `TEST_PLAN` tasks from the start.
- QA/tester do not wait for full dev completion to begin validation design.
- Final `QA_EXEC` depends on integration, so gate remains controlled.

## Cadence
- Continuous mini-iterations (cron loops by role)
- Dispatch + flow/WIP sync every ~15 min (planner absorbs ex-scrum_master)
- Admin checkpoints every 10-15 min
- Sprint-level review stays product-driven via `planner` + human owner (no always-on PO agent)
- Each cron tick acts as wake-up: resume from role memory + last contract + peer signals + workboard context.

## Safety locks
- Runner lock per role: prevents overlapping tmux/codex turns (`RUN_LOCK_BUSY` guard).
- Workboard file lock: `parallel_workstream.py` serializes board writes to prevent task/handoff corruption under parallel crons.
- Task hygiene on READY work: role evidence must include `task_update=` and `lock_check=ok`.
- Cron stale-state auto-heal: admin layer can reset jobs stuck in scheduler running state (disable/enable) via `stale_cron_sweep.sh`.

## Validation contract
All role outputs still follow the 8-key contract:
- `STATUS`
- `DELTA`
- `EVIDENCE`
- `RISKS`
- `NEXT`
- `VERDICT`
- `BLOCKER_ID`
- `NEXT_ACTION_UNIQUE`

For specialized lanes, evidence must include role artifact markers (`BACKEND_ARTIFACT=`, `FRONTEND_ARTIFACT=`, `INTEGRATOR_ARTIFACT=`, etc.).
Inter-role awareness is mandatory in each contract evidence: `channels_read=...`, `impact_assessment=...`, `impact_action=...`.
