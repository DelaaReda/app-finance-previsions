# Product Backlog

Source alignment:
- Product vision: `docs/planning/PRODUCT_VISION.md`
- Execution epics: `docs/planning/epics.md` (delta vision-clarifier section)
- Common board (single source for tasks): `docs/planning/tasks.md`
- This file is a product prioritization view; it does not define task breakdown details.

## Prioritization Rule
Order by:
1. User decision impact (time saved + action clarity)
2. Reliability risk reduction
3. Effort/cost efficiency

## Backlog Items (active)

### P0 - Must ship first
- Epic 1: Data freshness foundation (`<=10m` target on key tiles)
- Epic 2: Forecast engine contract (`direction/confidence/action` for MVP universe)
- Epic 3: Multi-model consensus + judge (low-cost providers first)

### P1 - Must follow immediately after P0 baseline
- Epic 4: Decision cockpit frontend (2-3 click daily brief)
- Epic 5: Ask copilot deep analysis (grounded by current data)
- Epic 8: Cost governance/runtime efficiency (free-first + guardrails)

### P2 - After core workflow is stable
- Epic 6: Portfolio adaptation layer (watchlist + risk profile tuning)
- Epic 7: Geopolitical and macro impact radar
- Epic 9: Decision journal and learning loop

## Refinement Checklist
- Clear user value for the personal-investor persona
- Testable acceptance with explicit data freshness and latency constraints
- Dependencies explicit (backend, frontend, data, model orchestration)
- Owner role assigned
- Estimate S/M/L

## Product Metrics (30d targets)
- North star: Daily Decision Brief Completion Rate >= 85%
- KPI 1: Freshness SLA (<=10m) >= 90%
- KPI 2: Coverage SLA (signal available for MVP universe) >= 90%

## Task Decomposition Index (all epics)
- Epic 1: `TV1-FRESH-01..06` + `TV-ADV-03` + `TV-ADV-04`
- Epic 2: `TV2-SIGNAL-01..06`
- Epic 3: `TV3-JUDGE-01..06` + `TV-ADV-02`
- Epic 4: `TV4-UI-01..07` + `TV-ADV-01` + `TV-ADV-07`
- Epic 5: `TV5-ASK-01..06` + `TV-ADV-05`
- Epic 6: `TV6-PORT-01..06`
- Epic 7: `TV7-MACRO-01..06`
- Epic 8: `TV8-COST-01..06`
- Epic 9: `TV9-LOOP-01..06`

Reference:
- `docs/planning/tasks.md` (`Vision Task Pack - Sprint W10`, `Code-Audit Advance Pack`, `Full Epic Decomposition - All Epics`)
