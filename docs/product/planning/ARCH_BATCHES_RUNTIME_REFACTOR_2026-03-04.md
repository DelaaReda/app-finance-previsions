---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md
  - /home/venom/analyse-financiere/docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md
---

# Architecture Runtime Refactor — 2026-03-04

Superseded for current target architecture.

This file is a historical implementation snapshot from the pre-planner-orchestrator period.
Current canonical execution roadmap is:
- `docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md`
- `docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md`

## Scope delivered in this pass
- Cron integration hardening:
  - runner config validation on cron setup
  - `RUNNER_CONFIG_FILE` + `RUNNER_CONFIG_LOADER` + `RUNNER_CONFIG_FALLBACK_ENV` propagation
  - advisory `po_scrum_master` cron gated by `FC_PO_SCRUM_MASTER_CRON_ENABLED`
- Runner modular architecture:
  - standardized module loading from `platform/automation/runner/main.sh`
  - shared config loading function reused by tick and runner
  - startup trace now includes `config_version`
  - modular test: `platform/automation/tests/test_runner_modules.sh`
- Monitor layered split (incremental):
  - new layered packages under `apps/monitor/src/{collectors,aggregators,api}`
  - doctor API routes moved to router module
  - status freshness + health computation now use layered functions
- API bootstrap split (incremental):
  - extracted `/api/health`, `/api/freshness`, `/api/frontend/config` into `platform/routers/health.py`
  - `create_app()` now includes health router
- placeholder router modules created for progressive extraction (`macro/stocks/news/forecasts/brief/copilot/notes/rag/signals`)
- Start/runtime reliability hardening:
  - `apps/api/runtime/copilot.sh` monitor bootstrap now waits for `/api/status` and `/api/runtime-diagnostics`.
  - stale monitor bind cleanup on `:7779` before wrapper fallback.
  - `FC_MONITOR_REQUIRED=1` default makes monitor startup failure explicit (non-silent).
- Doctor unification:
  - `scripts/fc_doctor.sh` now prefers `platform/automation/fc_doctor.py` (`doctor.v1` schema).
  - legacy doctor is opt-in only via `FC_DOCTOR_LEGACY=1`.

## Verification checklist
- `bash -n scripts/fc_setup_crons.sh`
- `bash -n scripts/fc_agent_tick.sh`
- `bash -n platform/automation/cron_tmux_role_runner.sh`
- `bash platform/automation/tests/test_runner_modules.sh`
- `python3 platform/automation/tests/test_fc_doctor.py`
- `python3 platform/automation/tests/test_doctor_json.py`
- `python3 -m pytest -q apps/monitor/tests/test_layered_collectors.py apps/monitor/tests/test_layered_aggregators.py apps/monitor/tests/test_doctor_router.py`
- `bash scripts/runtime_e2e_gate.sh`

## Next extraction slices
1. Move `status` and `runtime-diagnostics` route bodies into `apps/monitor/src/api` routers.
2. Extract critical API routes (`forecasts/recommendations/stocks-sheet`) into dedicated routers with stable degraded envelope.
3. Keep `platform/main.py` as bootstrap + include_router only.

## Follow-up patch (runtime hardening)
- Launcher status hardening (`apps/api/runtime/copilot.sh`):
  - `status` now resolves service state with endpoint checks first (`/api/health`, `/`, `/api/status` + `/api/runtime-diagnostics`),
  - fallback to port detection with `lsof` or `ss`,
  - fallback to pid liveness (`/tmp/finance_copilot_*.pid`),
  - monitor wrapper now persists `/tmp/finance_copilot_monitor.pid`.
- Runner fatal-noise reduction (`platform/automation/cron_tmux_role_runner.sh`):
  - `trap ERR` no longer emits `fatal_error` for expected non-zero `return` paths inside `prompt_once`/`codex_exec_prompt_once` (these are handled by retry/fallback),
- message-tail prompt guard now uses safe defaults (`${RUNTIME_AGENT_MESSAGES_TAIL:-none}` / `${RUNTIME_AGENT_MESSAGE_IDS:-none}`) to prevent unbound edge cases.

## Follow-up patch (API strangler extraction)
- New critical router module: `apps/api/src/platform/routers/critical.py`
  - `/api/recommendations/daily` moved from `platform/main.py` to dedicated router.
  - `/api/stocks/{ticker}/sheet` moved from `platform/main.py` to dedicated router.
- Router registry updated:
  - `apps/api/src/platform/routers/__init__.py` now exports `create_critical_router`.
  - `apps/api/src/platform/main.py` includes `create_critical_router()` in `create_app()`.
- Inline duplicate handlers removed from `register_routes`:
  - `/api/recommendations/daily` (now router-owned),
  - `/api/stocks/{ticker}/sheet` (now router-owned),
  - `/api/forecasts` compatibility inline wrapper removed; route now served by `domains.forecasts.api` via the existing `platform.routes` namespace.

## Validation snapshot
- `bash -n apps/api/runtime/copilot.sh`
- `bash -n platform/automation/cron_tmux_role_runner.sh`
- `bash platform/automation/tests/test_runner_modules.sh`
- `bash scripts/runtime_e2e_gate.sh`
  - proof: `docs/operations/orchestrator/proofs/runtime-gate/runtime-e2e-20260304T151907Z.log`
  - result: `PASS` on monitor contract + critical endpoints (`forecasts`, `recommendations/daily`, `stocks/{ticker}/sheet`)
- `bash scripts/runtime_e2e_gate.sh`
  - proof: `docs/operations/orchestrator/proofs/runtime-gate/runtime-e2e-20260304T200321Z.log`
  - result: `PASS` after critical-router extraction (`forecasts`, `recommendations/daily`, `stocks/{ticker}/sheet`)
