---
status: canonical
last_verified: 2026-03-07
---

# Product Planning Map

Use this index before reading any planning file in this directory.

## Start here
- Canonical product vision: [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md)
- Canonical product backlog: [BACKEND_FIRST_PRODUCT_BACKLOG.md](/home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md)
- Canonical execution order: [PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md)
- Current architecture entrypoints: [CURRENT_ARCHITECTURE_ENTRYPOINTS.md](/home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md)

## Canonical docs
- [BACKEND_FIRST_PRODUCT_BACKLOG.md](/home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md)
- [PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md)

## Companion / reference docs
- [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/planning/PRODUCT_VISION.md)
- [FORECAST_LAYER_COVERAGE_MATRIX.md](/home/venom/analyse-financiere/docs/product/planning/FORECAST_LAYER_COVERAGE_MATRIX.md)
- [FREE_DATA_SOURCE_KEY_MATRIX.md](/home/venom/analyse-financiere/docs/product/planning/FREE_DATA_SOURCE_KEY_MATRIX.md)
- [ARCHITECTURE_FORECAST_FREE_DATA_BLUEPRINT.md](/home/venom/analyse-financiere/docs/product/planning/ARCHITECTURE_FORECAST_FREE_DATA_BLUEPRINT.md)

## Historical / non-canonical docs
These remain useful for background, audit, or recovery of intent, but must not be treated as the active backlog source of truth.

- Batch packs:
  - [BATCHES_11_14_EXEC_SPEC.md](/home/venom/analyse-financiere/docs/product/planning/BATCHES_11_14_EXEC_SPEC.md)
  - [BATCHES_15_28_EXEC_SPEC.md](/home/venom/analyse-financiere/docs/product/planning/BATCHES_15_28_EXEC_SPEC.md)
  - [BATCHES_29_40_FORECAST_EXEC_SPEC.md](/home/venom/analyse-financiere/docs/product/planning/BATCHES_29_40_FORECAST_EXEC_SPEC.md)
  - [BATCHES_41_50_GLOBAL_FORECAST_SPEC.md](/home/venom/analyse-financiere/docs/product/planning/BATCHES_41_50_GLOBAL_FORECAST_SPEC.md)
- Legacy planning snapshots:
  - [WORKSTATE.md](/home/venom/analyse-financiere/docs/product/planning/WORKSTATE.md)
  - [PROJECT_BOARD.md](/home/venom/analyse-financiere/docs/product/planning/PROJECT_BOARD.md)
  - [tasks.md](/home/venom/analyse-financiere/docs/product/planning/tasks.md)
  - [epics.md](/home/venom/analyse-financiere/docs/product/planning/epics.md)
  - [stories.md](/home/venom/analyse-financiere/docs/product/planning/stories.md)
  - [mvp-plan.md](/home/venom/analyse-financiere/docs/product/planning/mvp-plan.md)
  - [MVP_SCOPE.md](/home/venom/analyse-financiere/docs/product/planning/MVP_SCOPE.md)
- Historical architecture batches and audits:
  - `ARCH_BATCHES_*`
  - `ARCH_MIGRATION_PERF_AUDIT_*`
- Historical scrum snapshots:
  - [docs/product/scrum/README.md](/home/venom/analyse-financiere/docs/product/scrum/README.md)
  - [docs/product/scrum/product-backlog.md](/home/venom/analyse-financiere/docs/product/scrum/product-backlog.md)
  - [docs/product/scrum/sprint-current.md](/home/venom/analyse-financiere/docs/product/scrum/sprint-current.md)
  - [docs/product/scrum/sprint-next.md](/home/venom/analyse-financiere/docs/product/scrum/sprint-next.md)

## Rule for agents
If documents conflict:
1. `docs/product/PRODUCT_VISION.md` wins for product intent.
2. `BACKEND_FIRST_PRODUCT_BACKLOG.md` wins for product priorities.
3. `PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md` wins for implementation order.
4. Historical files are background only.
