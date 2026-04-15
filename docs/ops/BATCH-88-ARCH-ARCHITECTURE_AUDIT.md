# BATCH-88 ARCH Architecture Audit

## Scope

- Batch: BATCH-88
- Task: BATCH-88-ARCH
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`; `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`; `docs/product/PRODUCT_VISION.md#One sentence`
- Vision target: daily brief first, ranked portfolio or watchlist action second, memo-open path third, all on the existing personal-finance page and copilot widgets

## Root cause

`BATCH-88-ARCH` was the only active planner task after `BATCH-88-ANALYSIS`, but it still had `proof_count=0` and no planner-owned architecture artifact. The active copilot stack already exposes usable backend and UI surfaces, yet the stream still lacked the explicit architecture contract that tells `dev` what to harden first and what not to redesign.

## Observed current-state gaps

- `packages/contracts/copilot_v1.py`
  Still a placeholder, so the public start/brief shape is not canonical or typed.
- `apps/api/src/domains/copilot/api/copilot.py`
  Still owns too much endpoint-specific shaping, cache wiring, namespace rewriting, and response normalization for a product-critical route.
- `apps/api/src/domains/copilot/application/copilot_service.py`
  Already concentrates most business logic and is the correct reuse target for ranking, degraded payloads, and memo-open preparation.
- `apps/web/src/domains/forecasts/pages/personal-finance-start.html`
  Already acts as the stream's page entrypoint and loads the copilot panel dynamically.
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`
  Already renders brief, portfolio, ask, and open surfaces; it should consume a stable backend contract rather than a route-owned JSON shape.
- `apps/web/src/domains/forecasts/components/widgets/portfolio-health.html`
  Provides an existing home for portfolio risk context that can explain the ranked action without a new UI subtree.

## Canonical implementation surfaces

- `apps/api/src/domains/copilot/api/copilot.py`
  Keep this as the thin HTTP adapter only: parsing, simple validation, cache/singleflight orchestration, namespace handling, delegation.
- `apps/api/src/domains/copilot/application/copilot_service.py`
  Reuse for brief shaping, action ranking inputs, fallback semantics, memo-open preparation, and domain logic.
- `apps/api/src/domains/copilot/application/copilot_endpoint_service.py`
  Preferred extraction target for payload assembly and metadata parity if route ownership stays too heavy.
- `packages/contracts/copilot_v1.py`
  Canonical shared contract target for the portfolio-first public payload.
- `apps/api/src/domains/judge/application/judge_endpoint_service.py`
  Reference only for Judge-parity route/service separation and metadata/fallback conventions.

## Architecture decision

- Freeze `BATCH-88` around one portfolio-first public contract rather than another route-local JSON shape.
- Keep business logic in `application/*`; if a new endpoint facade is added, it stays inside the `copilot` domain and delegates to `copilot_service.py`.
- Reuse `personal-finance-start.html`, `copilot-panel.html`, and `portfolio-health.html`; no new frontend subtree and no redesign is required to ship the stream.
- Downstream work order remains strict: `ARCH -> DEV-01 -> DEV-02 -> DEV-03 -> ADMIN-01 -> GOV_REVIEW`.

## Validation targets for downstream delivery

- Route delegation tests prove `copilot.py` no longer owns deep product logic.
- Contract tests prove `copilot_v1` shape for brief, ranked action, ask/open, and degraded payloads.
- Fallback tests prove never-empty responses with explicit `source[]`, `warnings[]`, and `fallback_used`.
- UI wiring tests prove the existing page and widgets can consume the stabilized payload without a structural rewrite.

## Verification

- before: `python3 platform/automation/compat/projections/parallel_workstream.py context --role planner --limit 5` reported `ready=0 in_progress=1` with `in_progress_tasks=BATCH-88-ARCH`
- after: planner owns an explicit `ARCH` artifact naming the shared contract, endpoint-service split, existing page/widget reuse, and downstream validation scope
- test: `git diff --check -- docs/operations/orchestrator/proofs/BATCH-88/BATCH-88-ARCH.md docs/ops/BATCH-88-ARCH-ARCHITECTURE_AUDIT.md`

## Vision alignment

- batch: BATCH-88
- target: daily brief surfaces the top portfolio or watchlist action and opens an investment memo in one click
- impact: unblocks `DEV-01` with a concrete contract-first/backend-first plan instead of another planner analysis loop
