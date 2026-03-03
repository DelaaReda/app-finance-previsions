# Orchestration Reliability Spec

## Scope
This spec defines the minimum reliability gates before enabling agent automation (cron + tmux loops).

## Failure Modes Observed In Execution Logs
- `signal_unparseable` storms (contract extraction noise from tmux output).
- `session_not_ready` loops (tick attempts while session not healthy).
- `contract_guard_*` hard blocks from formatting drift.
- stale lock accumulation (`.tmp/openclaw-shared-locks`, `role-state/*.run.lock`).
- rate-limit bursts causing repeated blocked ticks.

## Mandatory Gates Before Cron Reactivation
1. `CPU_GATE`
- No stale Chromium worker process older than 1h with renderer/utility profile.
2. `LOCK_GATE`
- No stale lock older than:
- 30 minutes in `.tmp/openclaw-shared-locks/*.lock`
- 20 minutes in `/home/venom/.openclaw/cron/role-state/*.run.lock`
- 20 minutes in `/tmp/fc-agent-locks/*.lock`
3. `CRON_GATE`
- Active tick jobs are read from `crontab -l` (`fc_agent_tick.sh ...`).
- Critical delivery coverage is mandatory on canonical lanes:
  - `planner`
  - `dev`
  - `admin` (when ops/recovery workload exists)
- Recommended stagger (to avoid claim collisions):
  - `planner`: `:00/:22/:44`
  - `dev`: `:06/:28/:50`
  - `admin`: `:12/:34/:56`
- Coverage is evaluated on canonical lanes (not raw role IDs):
  - `planner` lane: `planner|vision-architect-tasks-planner|analyst|architect|po|scrum_master`
  - `dev` lane: `dev|backend_engineer|frontend_engineer|data_analyst|integrator|infra_engineer|tester|qa`
  - `admin` lane: `admin|clawsentinel`
- Minimum ready state: explicit coverage for active canonical lanes (`planner` + `dev`, plus `admin` when lane active).
- `admin` is required when there is active ops workload (`admin` READY/IN_PROGRESS tasks) or incident recovery.
4. `SESSION_GATE`
- tmux sessions up for active canonical lanes:
  - `planner` -> `codex_planner_cron`
  - `dev` -> `codex_dev_cron`
  - `admin` -> `codex_admin_cron` (if lane active)
- No uncontrolled orphan session respawn (`codex_*_cron` not in active lanes, `qwen_*` leftovers).
5. `QUALITY_GATE`
- `signal_unparseable` and `contract_guard_*` trends not increasing after reactivation.
6. `MODEL_GATE`
- Role model must be one of:
- `openai-codex/gpt-5.2`
- `openai-codex/gpt-5.3-codex-spark`
- If invalid/legacy value detected (`gpt-5.3-spark`), auto-normalize before runner execution.
7. `RATE_LIMIT_GATE`
- Enable role/global cooldown caches to avoid retry storms when provider quota is saturated.
- Default backoff window:
- role cooldown ≈ 13 minutes
- global cooldown ≈ 15 minutes
8. `ARCH_PATH_GATE`
- `apps/api/src/runtime/` must not exist (canonical runtime path is `apps/api/runtime/`).
- `apps/api/src/runtime/data/rag/news.jsonl` must not exist (ghost/fake RAG path).
- `domains/judge/application/g4f_client.py` path resolvers must point to:
  - `apps/api/src/platform/legacy/data/llm/models/working.json`
  - `apps/api/runtime/data/llm/models/tested_g4f_models*.json` (legacy fallback `apps/api/src/` allowed temporarily)
9. `REUSE_GATE`
- Before creating a new module, claim evidence must include a reuse check (`rg` or equivalent) and chosen existing module.
- `sys.path.insert(...)` bridge patches are not accepted as final fixes for architecture issues.

## Runtime Contract Policy (Anti-Stall)
- Read-only roles (`planner`, `analyst`, `architect`, `po`, `scrum_master`, `clawsentinel`) must never emit delivery updates (`claim|complete|handoff`).
- If emitted anyway, guard auto-normalizes to `analysis_only` to avoid full-loop stall.
- Delivery roles in `task_update=blocked` are allowed without command-proof in same tick (avoid false `ROLE_EXEC_EVIDENCE_MISSING` on rate-limit blocks).
- Lean contract baseline:
  - required keys remain `STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE`.
  - minimal evidence required: `task_update`, `lock_check`, `run_note` (>=5 words), role artifact.
  - delivery-style evidence is mandatory for execution quality: `root_cause`, `fix_applied`, `verify`.
  - `reuse_check` is mandatory for delivery claims/completes (`module_reused` or `NONE(reason)`).
  - `stream_id/task_id` required for `claim|handoff`.
  - `cmd` + `tests_run` required for `complete`.

## Prompt Delivery Standard (Planner/Dev/Admin)
- Every tick must target one concrete executable action, not broad analysis.
- Mandatory execution loop when READY/IN_PROGRESS exists: `claim -> root-cause -> patch -> test -> complete/handoff`.
- `analysis_only` is forbidden when the role has actionable work in workboard context.
- Active non-closed IDs must stay lean and explicit: `PLAN`, `DEV-01/02/03`, `ADMIN-01`, `GOV-REVIEW` (avoid new active labels `BACKEND/FRONTEND/DATA`).
- `dev` specialization in lean IDs:
  - `DEV-01`: API/contracts/module-load fixes
  - `DEV-02`: runtime-path & integration coherence
  - `DEV-03`: quality/guardrails/spec hardening
- For each `claim` or `complete`, include one short reuse proof:
  - module/component reused,
  - or explicit one-line justification when no reusable module exists.

## Canonical Commands
- Audit-only preflight (no activation): `bash scripts/fc_reactivate_guard.sh --audit-only`
- Reactivation with guardrails (full): `bash scripts/fc_reactivate_guard.sh --kick-planner --full`
- Reactivation with guardrails (canary): `bash scripts/fc_reactivate_guard.sh --kick-planner --canary`
- Health report with reliability metrics: `bash scripts/fc_health_check.sh`
- Canonical runtime monitor (active cron roles + lane coverage): `bash scripts/monitor_agents.sh`

## Ownership
- Runtime owner: `adminapp-codex`
- Delivery governance owner: `admin-agents`
- Quality/safety owner: `clawsentinel`
