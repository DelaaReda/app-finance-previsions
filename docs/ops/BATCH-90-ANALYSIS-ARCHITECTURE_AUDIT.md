# BATCH-90 Analysis Architecture Audit

## Scope

- Batch: BATCH-90
- Task: BATCH-90-ANALYSIS
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`; `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`; `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`; `docs/product/PRODUCT_VISION.md#One sentence`
- Vision target: daily brief first, immediate ask/open second, explainable memo path third, all inside the existing personal-finance copilot surfaces

## Root Cause

`BATCH-90` was auto-created to keep the planner lane non-passive while the queue runway was short, but `BATCH-90-ANALYSIS` had no planner proof. That left the stream in `IN_PROGRESS` with `proof_count=0` and no explicit architecture traceability for the next canonical step.

## Canonical implementation surfaces

- `apps/api/src/domains/copilot/api/copilot.py`
  Thin route boundary for `start/ask/open`: parsing, HTTP envelope, cache, delegation only.
- `apps/api/src/domains/copilot/application/copilot_service.py`
  Application layer for brief shaping, action ranking inputs, degraded fallbacks, and memo-open payload preparation.
- `apps/api/src/domains/judge/application/judge_endpoint_service.py`
  Judge-parity reuse target for separating public payload normalization from the route.
- `apps/api/runtime/copilot.sh`
  Existing runtime entrypoint for the copilot slice; reuse instead of creating a parallel runtime path.
- `apps/web/src/domains/forecasts/pages/personal-finance-start.html`
  Existing host page for the brief-first personal-finance experience.
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`
  Existing ask/open surface to keep incremental frontend integration inside the current theme.
- `platform/automation/runtime/planner/planner_runtime_actions.py`
  Canonical planner lifecycle boundary for claim and complete only.
- `platform/automation/planner_subagent_manager.py`
  Sole dispatch path if `ARCH` later needs a delivery subagent; not a product logic surface.

## Architecture decision

- `BATCH-90-ARCH` must formalize the public contract and route/service split before any downstream dev work.
- The batch stays inside the current `copilot` domain and reuses Judge-parity patterns only where they reduce route-owned shaping.
- UI work is reuse-first on current HTML/widget surfaces; no new subtree, no `copilot-app/*`, no orchestration-only detour as product scope.
- Runtime changes stay limited to canonical task progression and proof capture.

## Dependency policy

`BATCH-90` remains the single canonical top-level stream. Planner closes `ANALYSIS`, then resumes `ARCH`, then allows `DEV-01..03`, `ADMIN-01`, and `GOV_REVIEW`. No duplicate batch, no redispatch of `ANALYSIS`, and no direct `dev` launch before `ARCH`.

## Verification

- before: `parallel_workstream.py context --role planner --limit 5` reported `ready=0 in_progress=1` with `in_progress_tasks=BATCH-90-ANALYSIS`
- after: `BATCH-90` has planner proof binding the stream to concrete `apps/api`, `apps/web`, `apps/api/runtime`, and `platform/automation` surfaces with strict dependency order
- test: re-run planner context after `complete` and confirm `BATCH-90-ANALYSIS` closes while `BATCH-90-ARCH` becomes the next canonical planner step

## Vision alignment

- batch: BATCH-90
- target: daily brief with the top portfolio or watchlist action, then ask/open and memo continuation without breaking the existing frontend theme
- impact: unblocks the architecture step with explicit reuse boundaries and avoids another planner quality loop on an empty proof set
