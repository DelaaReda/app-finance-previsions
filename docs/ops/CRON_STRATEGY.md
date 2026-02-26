# CRON STRATEGY v1

## Active baseline (parallel, 15 jobs)
- Profile: tmux-by-role (specialized lanes) + tri-admin + stale auto-heal.
- Source of truth (avoid doc drift):
  - `openclaw cron list --all`
  - `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
- Jobs:
  - 12 role loops: `planner`, `analyst`, `architect`, `backend_engineer`, `frontend_engineer`, `data_analyst`, `infra_engineer`, `integrator`, `dev`, `tester`, `qa`, `clawsentinel`
    - note: scope/value + flow/WIP reviews are absorbed by `planner` (no always-on `po`/`scrum_master` loops)
  - 2 admin loops: `adminapp-codex-sync-10m`, `admin-agents-supervisor-15m`
  - 1 utility: `stale-sweep-autoheal-7m`
- Runtime hardening baseline (tmux role runner):
  - `PROMPT_TIMEOUT_SECONDS=180`
  - `RETRY_PROMPT_TIMEOUT_SECONDS=90`
  - `TMUX_ROLE_RECOVERY_THRESHOLD=2`
  - `TMUX_ROLE_NO_DELTA_THRESHOLD=12`
  - `TMUX_ROLE_STALL_ABORT_SECONDS=75`
  - `TMUX_ROLE_AGENT_BIN=codex`
  - `TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk`
  - `TMUX_ROLE_CODEX_EXEC_RESUME=1`
  - `TMUX_ROLE_CODEX_EXEC_FALLBACK=1`
  - `TMUX_ROLE_CODEX_MODEL=gpt-5.3-codex`
  - `thinking=high`
  - `timeoutSeconds=900` (all role jobs, incl. architect)
  - payload policy: runner-only (`bash scripts/cron_tmux_role_runner.sh <role>`)
  - tmux role session naming is codex-first (`codex_<role>_cron`)
  - evidence schema: `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`
  - blocked detection priority: `NO_DELTA` streak gate + delivery-contract invariants + stall traces (not single hard timeout)

## Legacy baseline (core, 10 jobs)
- Historical profile: 8 delivery roles + 2 admin continuity ticks.
- Keep only as fallback troubleshooting; do not treat as active reference.
- Endpoint quality reference for smoke targets:
  - `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`
- Direct role cron methodology (fallback profile, non-active by default):
  - `docs/ops/DIRECT_CRON_METHODOLOGY.md`
- tmux cron runbook (active profile + multi-session protocol):
  - `docs/ops/TMUX_CRON_OPERATIONS.md`
- admin machine-restart checklist:
  - `docs/ops/ADMIN_POST_RESTART_RUNBOOK.md`
- admin codex baseline policy:
  - `docs/ops/ADMIN_CODEX_BASELINE.md`
- admin team workflow (coordination + logs clean + anti-derives payload):
  - `docs/ops/ADMIN_TEAM_CRON_PLAYBOOK.md`
- role model + handoff ownership matrix:
  - `docs/ops/AGENT_ROLE_INTEGRATION_MODEL.md`
- parallel scrum delivery model:
  - `docs/ops/PARALLEL_SCRUM_DELIVERY_MODEL.md`
- complete coordination/orchestration spec in YAML:
  - `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
- admin team shared iteration board:
  - `docs/ops/ADMIN_TEAM_ITERATIONS.md`
- parallel role topology (source config for specialized lanes):
  - `docs/orchestrator-ops/parallel-role-topology.json`
- quickstart runbook for parallel plumbing:
  - `docs/ops/PARALLEL_PLUMBING_QUICKSTART.md`

## Tri-admin execution model
- Operational director model:
  - main agent WhatsApp = directeur operationnel.
  - directives du directeur sont adressees aux admins uniquement.
  - admins convertissent ces directives en process/payload/cadence pour l'equipe livraison.
  - flux montant obligatoire: equipe livraison -> admins -> main.
  - toute demande hors circuit doit etre redirigee vers les admins.
  - reference normative: `docs/ops/OPERATIONAL_GOVERNANCE.md`.
- Active admin names:
  - `adminapp-codex`
  - `admin-agents`
  - `clawsentinel`
- Shared update rule:
  - each iteration must produce 3 signed notes (one per admin) in `docs/ops/ADMIN_TEAM_ITERATIONS.md`.
  - runtime decision summary is then mirrored in `docs/orchestrator-ops/agent-watchdog.md`.
- Single source-of-truth docs:
  - `docs/ops/ADMIN_TEAM_CRON_PLAYBOOK.md`
  - `docs/ops/ADMIN_TEAM_ITERATIONS.md`
  - `docs/orchestrator-ops/agent-watchdog.md`
  - `docs/planning/WORKSTATE.md`

## Recommended operating cadence

### 1) Planning Incremental Loop
- Frequency: every 5–15 minutes (5 for active delivery windows, 15 for normal mode)
- Goal: update planning deltas only, never reset.
- Inputs:
  - `docs/planning/WORKSTATE.md`
  - `docs/planning/mvp-plan.md`
  - `docs/planning/epics.md`
  - `docs/planning/stories.md`
  - `docs/planning/tasks.md`
- Output: delta updates + checkpoint + changelog.

### 2) Health + Smoke Loop
- Frequency: every 30 minutes
- Goal: catch runtime regressions early.
- Checks:
  - `/api/health`
  - minimal endpoint smoke set

### 3) Skill Security + AV Loop
- Frequency: 2 times/day
- Goal: detect malicious drift in installed skills.
- Checks:
  - obfuscation scan
  - AV scan (`scripts/skill_av_scan.sh`)

### 4) Daily Executive Synthesis
- Frequency: once daily (evening)
- Goal: top 3 priorities for next day + top blockers + KPI snapshot.

---

## Guardrails for all cron jobs
- Incremental only (no restart from zero)
- No-op protection (`NO_DELTA` behavior)
- Commit only when real changes exist
- Coordinate edits between concurrent sessions (edit window + backup + forced validation run)
- Structured output required:
  - `STATUS`
  - `DELTA`
  - `EVIDENCE`
  - `RISKS`
  - `NEXT`
  - `VERDICT`
  - `BLOCKER_ID`
  - `NEXT_ACTION_UNIQUE`

---

## Failure handling
- 1st failure: retry next cycle
- 2nd consecutive failure: mark run degraded
- 3rd consecutive failure: open blocker note in planning + require manual inspection
