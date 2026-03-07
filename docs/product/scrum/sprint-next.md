---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/product/planning/README.md
  - /home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md
---

# Sprint Next (Vision Clarifier Baseline)

Historical note:
- This file is an old sprint planning snapshot.
- It remains useful for historical trace only.
- Do not use it as the current planning or execution source of truth.

## Sprint Meta
- Sprint ID: SPRINT-2026-W10
- Start: 2026-03-02
- End: 2026-03-08
- Goal: Deliver the first reliable daily decision cockpit flow for personal investing.

## Sprint Objective
User can open the app and, in 2-3 clicks, get:
- actionable signal per MVP asset/sector
- confidence and risk context
- freshness <= 10 minutes on core data surfaces

## Committed Scope
1. Epic 1 slice: freshness and cache reliability on core feeds
2. Epic 2 slice: stable decision contract (`direction/confidence/action`)
3. Epic 4 slice: frontend decision cards for MVP universe

## Committed Task IDs (W10)
- Source of truth unique:
  - `docs/planning/tasks.md` (section `Vision Task Pack - Sprint W10 (P0-first)`)
- This sprint doc does not define tasks; it only references the common board.

## Advance Queue (pre-refined, post-W10)
- Source of truth unique:
  - `docs/planning/tasks.md` (section `Code-Audit Advance Pack (pre-W11)`)
- This sprint doc does not define tasks; it only references the common board.

## UI-First Execution Order (post-W10)
- Execution order is maintained in:
  - `docs/planning/tasks.md` (`UI Fast-Lane Priority` and `UI-first dispatch lane`)

## Full Ahead Queue (W11+)
- Source of truth unique:
  - `docs/planning/tasks.md` (`Full Epic Decomposition - All Epics (UI-first acceleration)`)
- This sprint doc does not define tasks; it only references the common board.

## Definition of Done (Sprint-level)
- End-to-end flow works from backend to frontend for MVP universe cards
- Freshness SLA and coverage SLA are measured and reported
- Decision cards show action/confidence/why/updated timestamp
- No hidden fallback behavior (degraded mode clearly visible)

## Exit Metrics
- Daily brief completion test: <= 10 minutes and <= 3 clicks
- Freshness SLA >= 90%
- Coverage SLA >= 90%

## Risks to Watch
- Free model/provider instability (g4f variability)
- Data source drift and schema changes
- Frontend latency if cache keys are not tuned

## Changelog
- 2026-02-26 America/New_York - Initial next-sprint baseline generated from clarified product vision.
- 2026-02-26 America/New_York - Added committed W10 task IDs aligned to clarified P0/P1 vision priorities.
- 2026-02-26 America/New_York - Added pre-refined post-W10 advance queue from direct code audit findings.
- 2026-02-26 America/New_York - Added explicit UI-first execution order for concrete visible user outcomes.
- 2026-02-26 America/New_York - Added full-ahead queue for Epic 3 to Epic 6 based on complete task decomposition.
- 2026-02-26 America/New_York - Re-aligned sprint doc to single-board rule: task definitions and ordering now live only in `docs/planning/tasks.md`.
- 2026-02-26 America/New_York - Board reference now includes expansion epics 7/8/9 through the single source `docs/planning/tasks.md`.
- 2026-02-26 America/New_York - Board reference expanded to include epic tracks 10/11/12/13/14 for basic-ready delivery loop.
- 2026-02-26 America/New_York - Board reference includes Epic 15 data-driven forecasting core track in the common tasks board.
