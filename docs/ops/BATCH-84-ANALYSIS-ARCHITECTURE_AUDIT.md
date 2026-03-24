# BATCH-84 Analysis Architecture Audit

## Scope

- Batch: BATCH-84
- Task: BATCH-84-ANALYSIS
- Architecture plan ref: docs/ops/BATCH-84-ANALYSIS-ARCHITECTURE_AUDIT.md
- Vision target: personal finance copilot with daily brief, analysis access, and downstream admin/runtime handoff

## Root Cause

The planner stream kept `BATCH-84-ANALYSIS` in progress without a committed architecture proof linking the batch to canonical implementation surfaces. That gap left dependency policy feedback unresolved and created repeated planner/admin route mismatch signals.

## Fix Applied

This audit anchors the batch to the allowed implementation surfaces:

- `apps/api/src/domains/*` for business logic and data contracts
- `apps/api/runtime/` for runtime orchestration and delivery wiring
- `apps/web/src` for existing UI integration only, with no theme refactor

It also records the anti-regression boundaries that must stay intact:

- no `copilot-app/*`
- no `backend/src/backend/src/*`
- no legacy `src.*` imports

## Dependency Policy

`BATCH-84` remains the single canonical top-level stream. Planner-owned analysis closes at this audit stage, admin work continues on `BATCH-84-ADMIN-01`, and any follow-up implementation must stay intra-stream instead of recreating parallel backlog scopes.

## Verification

- before: planner analysis had no committed architecture audit artifact and guardian feedback still flagged missing architecture references
- after: the batch has a committed planner artifact tying the work to `apps/api` and `apps/web` with explicit anti-regression rules
- test: artifact review plus runtime completion proof on `BATCH-84-ANALYSIS`

## Vision Alignment

- batch: BATCH-84
- target: unblock real delivery of the finance copilot through canonical runtime orchestration
- impact: clears planner analysis proof so the batch can continue on concrete admin/runtime execution
