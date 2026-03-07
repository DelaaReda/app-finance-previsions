---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md
  - /home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md
---

# Migration Summary (Historical)

This file is retained as migration history, not as current runtime truth.

## What it is
- a record of the transition from older multi-lane orchestration patterns
- a reminder that some compatibility paths still exist in the repo
- a historical narrative for debugging earlier decisions

## What it is not
- not the live scheduler contract
- not the current role topology
- not the current operator entrypoint

## Current truth moved to
- runtime target: [PLANNER_ORCHESTRATOR_TARGET_SPEC.md](/home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md)
- current entrypoints: [CURRENT_ARCHITECTURE_ENTRYPOINTS.md](/home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md)
- workspace/runtime paths: [AGENT_WORKSPACE_INDEX.md](/home/venom/analyse-financiere/docs/ops/AGENT_WORKSPACE_INDEX.md)

## Historical scope kept here
- deprecated lane-era assumptions
- compatibility windows and cutover notes
- removal checkpoints that only matter when reading older incidents

If you are implementing or operating the current system, leave this file and switch to the canonical docs above.
