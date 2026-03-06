# Planner Agent Hardening Plan (2026-03-03)

## Objective
Stabilize planner autonomy so it can continuously:
- detect architecture/runtime delivery gaps,
- dispatch actionable work to delivery lanes,
- avoid contract drift loops (HANDOFF/BATCH blockers),
- produce monitor-visible evidence that maps to real progress.

## Current Failure Modes
- Soft planner blockers still appear in runtime snapshots (`HANDOFF_TO_MISSING`, `PLANNER_BATCH_ID_INVALID`).
- Planner outputs sometimes degrade to passive updates while lane context is active.
- Evidence quality is inconsistent across retries/fallbacks, which hurts monitor trust.
- Guardian issues repeat (`ready_but_none_task_update`, `runway_short_without_batch_creation`).

## Phase 1 (Now) — Contract Reliability
1. Harden contract guard normalization for planner soft blockers.
2. Auto-normalize planner handoff target when omitted or placeholder.
3. Ensure guard-generated blocked payloads use role-specific artifact markers.
4. Add dedicated regression tests for planner handoff placeholders and guard output shape.

Exit criteria:
- No new `BLOCKER_ID=HANDOFF_TO_MISSING` caused by contract formatting alone.
- No new `BLOCKER_ID=PLANNER_BATCH_ID_INVALID` caused by malformed placeholder tokens alone.

## Phase 2 — Planner Delivery Behavior
1. Tighten planner prompt contract to force explicit handoff target fallback (`handoff_to=dev`).
2. Require planner to output dispatch-ready evidence when READY/IN_PROGRESS exists.
3. Add monitor-facing summary fields that clearly distinguish passive wait vs actionable dispatch.

Exit criteria:
- Guardian `ready_but_none_task_update` streak <= 1 over rolling 6 ticks.
- Planner produces at least one dispatch-ready action whenever READY exists.

## Phase 3 — Autonomy Feedback Loop
1. Use planner guardian streaks as automatic feedback input for planner prompt tuning.
2. Emit corrective directives only when issue fingerprints persist across >=3 ticks.
3. Keep planner timeline/audit bundle as the single source of truth for tuning decisions.

Exit criteria:
- Low-score streaks trend down week-over-week.
- Contract guard blocks become rare and explainable (real runtime blockers only).

## KPIs
- `planner_guard_blocked_count_24h`
- `planner_ready_idle_streak_max_24h`
- `planner_soft_blocker_normalized_count_24h`
- `planner_dispatch_actions_count_24h`
- `planner_contract_parse_failure_count_24h`

## Non-Goals
- No broad refactor of all role prompts in this cycle.
- No new role creation or monitor architecture rewrite in this cycle.
- No unsafe bypass of contract validation.

