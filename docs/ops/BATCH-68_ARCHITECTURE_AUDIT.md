# BATCH-68 Architecture Audit

Status: ready for GOV_REVIEW
Batch: BATCH-68
Task: BATCH-68-ARCH
Architecture plan ref: docs/ops/ACTIVE_DOCS_INDEX.md; docs/ops/PLANE_BACKLOG_INTEGRATION_SPEC.md; docs/product/PRODUCT_VISION.md

## Objective
Deliver the personal finance copilot flow defined in the product vision without breaking the existing frontend theme.

## Scope anchors
- Backend domain surface: `apps/api/src/domains/*`
- Frontend integration surface: `apps/web/src`
- Runtime surface: `apps/api/runtime/`

## Continuity and anti-regression guards
- Do not create or reuse `copilot-app/*`.
- Do not introduce nested backend paths such as `backend/src/backend/src/*`.
- Do not reintroduce legacy `src.*` imports.
- Preserve the current frontend theme; only wiring or rendering adjustments are allowed when backend value requires it.

## Implementation tracks
1. Enrich backend domain contracts for brief, ticker/theme deep dive, and memo output.
2. Reuse the existing frontend shell in `apps/web/src` and limit changes to data wiring or memo rendering.
3. Keep runtime orchestration aligned with planner-only scheduling and Plane-backed backlog truth.

## Integration reuse
- Reuse existing domain modules in `apps/api/src/domains/*` instead of creating parallel app surfaces.
- Reuse existing web shell and route structure in `apps/web/src`.
- Reuse runtime projections only as compatibility views; runtime truth stays in the canonical planner/runtime flow.

## Acceptance gate
- Architecture references point to the active docs index, Plane integration spec, and product vision.
- The delivery path is backend-first and theme-preserving.
- `apps/api` and `apps/web` ownership boundaries are explicit.
- Anti-regression guards are stated before GOV_REVIEW.

## Audit verdict
The BATCH-68 architecture step is sufficiently framed to advance to GOV_REVIEW. Downstream waiting items are expected because they depend on this planner closure, not because of an unresolved blocker on the current task.
