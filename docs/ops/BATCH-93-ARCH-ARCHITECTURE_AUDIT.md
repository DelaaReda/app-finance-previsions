# BATCH-93 ARCH Architecture Audit

## Scope

- Batch: BATCH-93
- Task: BATCH-93-ARCH
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`; `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`; `docs/ops/EC2_APP_RUNTIME_QUICK_REFERENCE.md`; `docs/product/PRODUCT_VISION.md#One sentence`
- Vision target: personal finance copilot with a brief of the day first, immediate ask/open entry second, and memo-quality output on the existing frontend surfaces

## Root cause

`BATCH-93-ARCH` became the only active planner task after `BATCH-93-ANALYSIS`, but it still had no planner-owned architecture artifact. The stream already has the canonical reuse surfaces, yet `dev` was blocked because the runtime had no committed architecture handoff tying the public contract, backend service boundary, frontend reuse, and EC2 validation scope into one delivery-ready instruction.

## Observed current-state gaps

- `packages/contracts/copilot_v1.py`
  Must become the stable public contract for the brief/start payload instead of leaving the frontend coupled to route-local JSON assumptions.
- `apps/api/src/domains/copilot/api/copilot.py`
  Must stay thin and delegate payload assembly, degraded-mode semantics, and ask/open orchestration to the application layer.
- `apps/api/src/domains/copilot/application/copilot_service.py`
  Already holds the core business logic and should remain the main reuse target for normalization, memo shaping, and never-empty fallback behavior.
- `apps/api/src/domains/judge/application/judge_endpoint_service.py`
  Is the parity reference for metadata, fallback semantics, and service-backed endpoint structure; reuse its patterns without copying a second decision engine.
- `apps/web/src/domains/forecasts/contracts/apiConnector.js`
  Must consume the shared backend contract and preserve backend freshness/source/warnings metadata.
- `apps/web/src/domains/forecasts/pages/personal-finance-start.html`
  Stays the canonical page entrypoint; no redesign or parallel shell.
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`
  Stays the canonical UI surface for brief, ask, and open actions.

## Canonical implementation surfaces

- `packages/contracts/copilot_v1.py`
  Canonical shared contract target for the public starter payload.
- `apps/api/src/domains/copilot/api/copilot.py`
  Thin route adapter only: parsing, simple validation, response envelope, endpoint-specific cache/singleflight.
- `apps/api/src/domains/copilot/application/copilot_service.py`
  Canonical business-logic layer for brief payload shaping, ask/open preparation, fallback semantics, and memo-oriented responses.
- `apps/api/src/domains/copilot/application/copilot_endpoint_service.py`
  Preferred extraction target if route-level payload assembly still remains too heavy.
- `apps/web/src/domains/forecasts/contracts/apiConnector.js`
  Frontend integration point for the shared contract and metadata-aware UI consumption.
- `apps/web/src/domains/forecasts/pages/personal-finance-start.html`
  Existing personal-finance page to wire, not replace.
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`
  Existing widget surface to harden around the stabilized payload.

## Architecture decision

- Keep `BATCH-93` inside one single-batch dependency chain: `ANALYSIS -> ARCH -> DEV-01 -> DEV-02 -> DEV-03 -> ADMIN-01 -> GOV_REVIEW`.
- Stabilize the public contract first in `packages/contracts/copilot_v1.py`, then finish route/service split inside `apps/api/src/domains/copilot/application/*`.
- Reuse the existing frontend page and widget surfaces; do not create `copilot-app/*`, `backend/src/backend/src/*`, or legacy `src.*` imports.
- Public product validation must use the EC2 endpoints only: `http://3.98.20.77/`, `http://3.98.20.77/api/...`, `http://3.98.20.77:8080/...`.

## Validation targets for downstream delivery

- Contract tests prove a stable start payload for brief, ask/open entry, metadata, and degraded mode.
- Route/service tests prove `copilot.py` delegates core payload logic to `application/*`.
- Fallback tests prove never-empty behavior with explicit `source[]`, `warnings[]`, and `fallback_used`.
- Frontend wiring tests prove `apiConnector.js`, `personal-finance-start.html`, and `copilot-panel.html` consume the stabilized contract without a structural rewrite.

## Verification

- before: `python3 platform/automation/compat/projections/parallel_workstream.py context --role planner --limit 5` reported `ready=0 in_progress=1` with `in_progress_tasks=BATCH-93-ARCH`
- after: planner owns a committed `ARCH` artifact that binds the stream to the shared contract, service boundary, frontend reuse points, dependency order, and EC2 validation scope
- test: `git diff --check -- docs/ops/BATCH-93-ARCH-ARCHITECTURE_AUDIT.md`

## Vision alignment

- batch: BATCH-93
- target: portfolio-first brief with ranked actions, immediate ask/open entry, and memo-quality output on the current personal-finance surfaces
- impact: unblocks `DEV-01` with a contract-first/backend-first handoff and removes the empty `ARCH` proof gap from the active stream
