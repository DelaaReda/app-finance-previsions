# BATCH-89 Analysis Architecture Audit

## Scope

- Batch: BATCH-89
- Task: BATCH-89-ANALYSIS
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`; `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`; `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`; `docs/product/PRODUCT_VISION.md#One sentence`
- Vision target: daily brief first, ranked portfolio or watchlist action second, investment memo open path third, all inside the existing copilot surfaces

## Root Cause

`BATCH-89` was auto-created and claimed to keep the planner lane non-passive, but the stream had no planner-owned architecture proof. That left `BATCH-89-ANALYSIS` in progress with `proof_count=0`, no `architecture_plan_ref`, and no `architecture_audit`, which matches the guardian failure mode on this tick.

## Canonical implementation surfaces

- `apps/api/src/domains/copilot/api/copilot.py`
  Product-facing route boundary for `start/context/ask/open`. Keep this layer thin: parsing, cache, singleflight, HTTP envelope, delegation.
- `apps/api/src/domains/copilot/application/copilot_service.py`
  Primary application surface for brief shaping, ranking logic input, degraded fallback, and memo-open payload preparation.
- `apps/api/src/domains/judge/application/judge_endpoint_service.py`
  Reuse target for Judge-like endpoint/service separation and public payload normalization.
- `apps/api/runtime/copilot.sh`
  Existing runtime entrypoint for backend/frontend/monitor orchestration around the copilot slice; reuse instead of inventing a second runtime path.
- `apps/web/src/domains/forecasts/pages/personal-finance-start.html`
  Existing personal-finance page that already rewrites start/open targets and loads the copilot panel dynamically.
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`
  Existing ask/open widget surface; keep integration incremental.
- `platform/automation/runtime/planner/planner_runtime_actions.py`
  Runtime lifecycle boundary for planner claim/complete transitions only; product logic must not move here.
- `platform/automation/planner_subagent_manager.py`
  Only dispatch path if later delivery work must be delegated after `ARCH`; not part of product logic.

## Architecture decision

- `BATCH-89-ARCH` must close the contract and route/service split before any dev dispatch.
- The personal-finance brief stays inside the current `copilot` domain and borrows Judge parity patterns where they remove route-owned shaping.
- UI work reuses current widgets and page wiring; no new frontend subtree and no monitor-led work enters this stream.
- Runtime/orchestration changes are limited to canonical task progression and proof capture.

## Dependency policy

`BATCH-89` remains the single canonical top-level stream. Planner closes `ANALYSIS`, then resumes `ARCH`, then allows downstream `DEV-01..03`, then `ADMIN-01`, then `GOV_REVIEW`. No duplicate stream, no relaunch of `ANALYSIS`, and no direct `dev` run before `ARCH`.

## Verification

- before: `parallel_workstream.py context --role planner --limit 5` reported `ready=0 in_progress=1` with `in_progress_tasks=BATCH-89-ANALYSIS`
- after: `BATCH-89` has planner proof tying the stream to concrete `apps/api`, `apps/web`, `apps/api/runtime`, and `platform/automation` surfaces with strict dependency order
- test: re-run planner context after `complete` and confirm `BATCH-89-ANALYSIS` closes while `BATCH-89-ARCH` becomes the next canonical planner step

## Vision alignment

- batch: BATCH-89
- target: daily brief surfaces the top portfolio or watchlist action and opens an investment memo in one click
- impact: unlocks the architecture step with explicit reuse boundaries, preventing another planner quality loop or duplicate batch creation
