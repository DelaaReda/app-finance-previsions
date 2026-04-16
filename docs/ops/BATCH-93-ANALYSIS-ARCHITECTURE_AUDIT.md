# BATCH-93 Analysis Architecture Audit

## Scope

- Batch: BATCH-93
- Task: BATCH-93-ANALYSIS
- Architecture plan ref: docs/ops/ACTIVE_DOCS_INDEX.md; docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md; docs/ops/API_ENDPOINT_BEST_PRACTICES.md; docs/product/PRODUCT_VISION.md#One sentence
- Vision target: personal finance copilot with a daily brief, immediate ask/open entry, explainable memo output, and preserved frontend theme

## Root Cause

`BATCH-93` was auto-created to keep the planner lane active, but the claimed analysis task still lacked a committed architecture audit tied to the canonical implementation surfaces in `apps/api`, `packages/contracts`, and `apps/web`. That left the active planner proof incomplete and kept guardian feedback red on missing architecture and vision references.

## Canonical implementation surfaces

- `packages/contracts/copilot_v1.py`
  Shared starter payload contract for the public personal-finance/copilot bootstrap shape.
- `apps/api/src/domains/copilot/api/copilot.py`
  Thin product-facing route surface for `/api/copilot/start`, `/api/personal-finance/start`, `/api/copilot/context`, and ask/open entry orchestration.
- `apps/api/src/domains/copilot/application/copilot_service.py`
  Main application layer for brief payload normalization, never-empty fallback behavior, context shaping, and memo-oriented response assembly.
- `apps/api/src/domains/judge/application/judge_endpoint_service.py`
  Judge-parity reuse target for endpoint-service patterns, metadata parity, and degraded-but-usable outputs when the stream hardens start/ask/open quality.
- `apps/web/src/domains/forecasts/contracts/apiConnector.js`
  Existing frontend API connector surface that should consume richer backend contracts instead of inventing route-local JSON assumptions.
- `apps/web/src/domains/forecasts/pages/personal-finance-start.html`
  Entry page for the personal-finance namespace; frontend work must stay wiring-focused and keep the current theme intact.
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`
  Existing UI surface for brief, ask, and open actions; downstream changes should reuse it instead of creating a parallel shell.

## Architecture decision

- Backend-first delivery remains mandatory.
- `BATCH-93-ARCH` should lock the minimal shared contract and endpoint-service boundary needed to make the public starter flow converge toward Judge-parity without cloning a second decision engine.
- Downstream implementation stays inside `apps/api/src/domains/*`, `packages/contracts/*`, and `apps/web/src/domains/forecasts/*`.
- Public validation must target EC2 public endpoints, while orchestration truth remains on the VM/runtime state.

## Anti-regression guardrails

- Forbidden: `copilot-app/*`
- Forbidden: `backend/src/backend/src/*`
- Forbidden: legacy `src.*` imports
- No frontend-led redesign or theme rewrite
- No duplicate decision engine outside the existing `judge` and `copilot` service stack

## Dependency policy

`BATCH-93` remains the single canonical top-level stream. Planner closes analysis with this audit, then advances to `BATCH-93-ARCH`; implementation, runtime validation, and governance stay in the same stream with no duplicate batch creation.

## Verification

- before: `BATCH-93-ANALYSIS` was `IN_PROGRESS` with no committed architecture audit and guardian feedback missing `architecture_plan_ref`, `architecture_audit`, and `vision_alignment`
- after: `BATCH-93` has a planner-owned analysis audit tied to `apps/api`, `packages/contracts`, and `apps/web`, with explicit reuse boundaries for the brief + ask/open flow
- test: `python3 platform/automation/compat/projections/parallel_workstream.py context --role planner --limit 5`

## Vision alignment

- batch: BATCH-93
- target: portfolio-first brief with ranked actions, immediate ask/open entry, and memo-quality output
- impact: unlocks the canonical `ARCH` step with explicit reuse boundaries so downstream delivery can harden the public starter path without another planner evidence gap
