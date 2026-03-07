---
status: canonical
last_verified: 2026-03-07
canonical_replaces:
  - docs/product/planning/PRODUCT_VISION.md (legacy long-form duplicate)
---

# Product Vision Planning Companion

This file is the planning companion for the canonical product vision.

- Canonical product vision: [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md)
- Canonical runtime target: [PLANNER_ORCHESTRATOR_TARGET_SPEC.md](/home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md)
- Canonical execution order: [PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md)

## Planning use
Use this document when translating vision into delivery batches, not when redefining the vision itself.

## Planning rules
- Do not duplicate the full product vision here.
- Planning work must stay aligned with:
  - explainable-first outputs
  - proof-first delivery
  - freshness as a correctness requirement
  - personal-use and low-cost runtime constraints
- If a planning document conflicts with the canonical vision, the canonical vision wins.

## What belongs here
- Batch sequencing
- Scope cuts
- Delivery gates
- Dependencies between product milestones
- Rollout and proof expectations

## What does not belong here
- A second long-form product manifesto
- Legacy architecture assumptions based on autonomous lanes
- Historical migration notes unless explicitly linked from a current batch/spec
