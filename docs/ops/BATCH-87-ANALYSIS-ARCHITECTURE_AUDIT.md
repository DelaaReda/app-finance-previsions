# BATCH-87 Analysis Architecture Audit

## Scope

- Batch: BATCH-87
- Task: BATCH-87-ANALYSIS
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`; `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`; `docs/product/PRODUCT_VISION.md#One sentence`
- Vision target: daily brief first, ranked portfolio or watchlist action second, investment memo open path third, all inside the existing copilot surfaces

## Root Cause

`BATCH-87` was auto-created and claimed to keep the planner lane non-passive, but the stream had no planner-owned architecture proof. That left `BATCH-87-ANALYSIS` in progress with `proof_count=0`, no `architecture_plan_ref`, and no `architecture_audit`, which is exactly the guardian failure mode flagged on this tick.

## Canonical implementation surfaces

- `apps/api/src/domains/copilot/api/copilot.py`
  Product-facing route boundary for start/context/ask/open. Keep this layer thin: parsing, cache, singleflight, HTTP envelope, delegation.
- `apps/api/src/domains/copilot/application/copilot_service.py`
  Primary application surface for brief shaping, ranking logic input, degraded fallback, and memo-open payload preparation.
- `apps/api/src/domains/judge/application/judge_endpoint_service.py`
  Reuse target for Judge-like endpoint/service separation and public payload normalization.
- `apps/api/runtime/copilot.sh`
  Existing runtime entrypoint for copilot operations; reuse instead of inventing a second runtime path.
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`
  Existing ask/open widget surface; keep integration incremental.
- `apps/web/src/domains/forecasts/components/widgets/portfolio-health.html`
  Existing portfolio-focused surface that can host ranked action context without redesign.
- `platform/automation/runtime/planner/planner_runtime_actions.py`
  Runtime lifecycle boundary for planner claim/complete transitions only; product logic must not move here.

## Architecture decision

- `BATCH-87-ARCH` must close the contract and route/service split before any dev dispatch.
- The portfolio-first brief stays inside the current `copilot` domain and borrows Judge parity patterns where they remove route-owned shaping.
- UI work reuses current widgets and domain boundaries; no new frontend subtree and no monitor-led work enters this stream.
- Runtime/orchestration changes are limited to canonical task progression and proof capture.

## Dependency policy

`BATCH-87` remains the single canonical top-level stream. Planner closes `ANALYSIS`, then resumes `ARCH`, then allows downstream `DEV-01..03`, then `ADMIN-01`, then `GOV_REVIEW`. No duplicate stream, no relaunch of `ANALYSIS`, and no direct `dev` run before `ARCH`.

## Verification

- before: `parallel_workstream.py context --role planner --limit 5` reported `ready=0 in_progress=1` with `in_progress_tasks=BATCH-87-ANALYSIS`
- after: `BATCH-87` has committed planner proof tying the stream to concrete `apps/api`, `apps/web`, and `platform/automation` surfaces with strict dependency order
- test: re-run planner context after `complete` and confirm `BATCH-87-ANALYSIS` closes while `BATCH-87-ARCH` becomes the next canonical planner step

## Vision alignment

- batch: BATCH-87
- target: daily brief surfaces the top portfolio or watchlist action and opens an investment memo in one click
- impact: unlocks the architecture step with explicit reuse boundaries, preventing another planner quality loop or duplicate batch creation
