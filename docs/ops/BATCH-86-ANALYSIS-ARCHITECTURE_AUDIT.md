# BATCH-86 Analysis Architecture Audit

## Scope

- Batch: BATCH-86
- Task: BATCH-86-ANALYSIS
- Architecture plan ref: docs/ops/ACTIVE_DOCS_INDEX.md; docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md; docs/product/PRODUCT_VISION.md#One sentence
- Vision target: personal finance copilot with brief of the day, immediate ask/open entry, explainable memo output, and existing frontend theme preserved

## Root Cause

`BATCH-86` was created and claimed fast enough to keep the planner lane non-passive, but the task had no committed architecture audit tying the new stream to canonical implementation surfaces. That left the active analysis proof incomplete and kept guardian feedback red on `missing_architecture_plan_ref` and `missing_architecture_audit`.

## Canonical implementation surfaces

- `apps/api/src/domains/copilot/api/copilot.py`
  Thin product-facing route surface for start/context/ask. Keep route orchestration limited to input parsing, cache/singleflight, response envelope, and service delegation.
- `apps/api/src/domains/copilot/application/copilot_service.py`
  Primary application layer for brief payload normalization, fallback behavior, context shaping, and memo-oriented output assembly.
- `apps/api/src/domains/judge/application/judge_endpoint_service.py`
  Reuse target for Judge-parity endpoint service patterns when the stream hardens ask/open or shared memo contracts.
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`
  Existing UI integration surface for brief, ask, and open actions. UI changes stay wiring-focused and must preserve the current theme.

## Architecture decision

- Backend-first delivery remains mandatory.
- `BATCH-86-ARCH` should define the minimal shared contract or endpoint-service extraction needed for the personal-finance brief/start/open flow without cloning new route-owned logic.
- Downstream dev work stays inside `apps/api/src/domains/*`, `apps/api/runtime/`, and `apps/web/src`.
- No duplicate decision engine outside the existing `judge` and `copilot` service stack.

## Anti-regression guardrails

- Forbidden: `copilot-app/*`
- Forbidden: `backend/src/backend/src/*`
- Forbidden: legacy `src.*` imports
- No frontend-led redesign or theme rewrite
- No duplicate backend helper tree when the existing `copilot` or `judge` stack can be reused

## Dependency policy

`BATCH-86` remains the single canonical top-level stream. Planner closes analysis with this audit, then progresses to `BATCH-86-ARCH`; implementation and validation continue inside the same stream with no duplicate batch creation.

## Verification

- before: `BATCH-86-ANALYSIS` was `IN_PROGRESS` with `proof_count=0` and no committed architecture audit
- after: `BATCH-86` has a planner-owned architecture audit tied to `apps/api` and `apps/web` plus explicit anti-regression boundaries
- test: planner runtime completion proof plus `parallel_workstream.py context --role planner --limit 5`

## Vision alignment

- batch: BATCH-86
- target: personal finance copilot that starts from a daily brief and moves directly into ask/open with memo-quality output
- impact: unlocks the canonical `ARCH` step with clear reuse boundaries so downstream delivery can stay product-visible and avoid another planner churn loop
