---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md
  - /home/venom/analyse-financiere/docs/ops/AGENT_WORKSPACE_INDEX.md
---

# Historical Operations Index

This tree is no longer the primary source of truth for architecture or day-to-day operational entrypoints.

Use it for:
- migration history
- incident reports
- archived runbooks
- legacy coordination references
- human-facing orchestration evidence

Do not use it as the default starting point for implementation or operator decisions.

## Start here instead
- current entrypoints: [CURRENT_ARCHITECTURE_ENTRYPOINTS.md](/home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md)
- workspace/path truth: [AGENT_WORKSPACE_INDEX.md](/home/venom/analyse-financiere/docs/ops/AGENT_WORKSPACE_INDEX.md)
- product vision: [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md)
- runtime target: [PLANNER_ORCHESTRATOR_TARGET_SPEC.md](/home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md)

## How to read this tree
### `docs/operations/*.md`
Mostly migration notes, incident reports, and superseded guidance from earlier orchestration phases.

### `docs/operations/ops/*`
Historical or compatibility copies of operational docs. The canonical operational set lives under `docs/ops/`.

### `docs/operations/orchestrator/*`
Mixed human-facing evidence, archived plans/checklists, and runtime-generated artifacts. See the local boundary note in [orchestrator/README.md](/home/venom/analyse-financiere/docs/operations/orchestrator/README.md).

### `docs/operations/safety/*`
Historical safety and audit material. Read only when the current canonical docs point here explicitly.

## Editing rule
- Update `docs/ops/*` for current policy.
- Update `docs/operations/*` only when archiving, annotating history, or preserving a past incident.
