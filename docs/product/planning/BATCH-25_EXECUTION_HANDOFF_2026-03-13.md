---
status: active_supporting_doc
last_verified: 2026-03-13
batch: BATCH-25
---

# BATCH-25 Execution Handoff - 2026-03-13

## Goal
Deliver `Autonomous Morning Brief Pipeline` as a scheduled, failure-tolerant brief generation flow using the existing brief, forecast, judge, and monitor stack.

Primary user value:
- a usable morning brief exists before the configured hour
- the brief is action oriented, not only descriptive
- if generation degrades or fails, the user still receives an explicit degraded brief rather than silence

## Mandatory architecture constraints
- reuse the current brief-generation path; do not create a separate pipeline stack
- compose from existing forecast, judge, and monitor sources
- preserve the current brief route schema as the primary delivery surface
- embed degradation metadata explicitly instead of hiding partial failures

## Preferred module scope
Primary targets:
- `scripts/generate_brief.py`
- `apps/api/src/domains/forecasts/api/brief.py`
- `apps/api/src/platform/legacy/research/llm_client.py`
- `apps/api/src/domains/judge/application/intelligence_service.py`

Secondary rule:
- if a slice can complete inside one of these paths, do not spill into parallel orchestration surfaces

## Delivery lanes
### BATCH-25-DEV-01
Mission:
- implement the minimal scheduled/digest generation slice on top of the existing brief path

Expected code shape:
- keep the current brief schema
- ensure the generation path can emit a durable morning brief artifact before the configured hour
- add explicit freshness/degraded metadata where needed

Completion evidence:
- exact files changed
- one concise note explaining where the scheduled brief artifact is produced or refreshed
- explicit additive fields/hooks available for `DEV-02`

### BATCH-25-DEV-02
Mission:
- make the brief action-oriented using existing judge/forecast context

Expected code shape:
- reuse current judge/forecast outputs for top actions, main risks, and confidence/freshness framing
- avoid a second synthesis surface

Completion evidence:
- exact files changed
- concise note describing the action-oriented additions now visible in the morning brief contract
- explicit residual edge, if any, for `DEV-03`

### BATCH-25-DEV-03
Mission:
- finish degraded-mode handling and final contract cleanup for the morning brief path

Expected code shape:
- explicit degraded brief when source freshness or model synthesis is insufficient
- bounded cleanup only; no platform rewrite

Completion evidence:
- exact files changed
- concise note on degraded fallback behavior
- explicit statement that the route schema stayed compatible

### BATCH-25-ADMIN-01
Mission:
- capture runtime proof for scheduled generation, degraded fallback, and user-visible usability

Required proof:
- evidence that the brief is generated before the configured hour or simulated scheduler cutoff
- evidence that degraded mode remains explicit and usable
- evidence that the current brief route continues to serve the intended payload

## Planner merge criteria
- `DEV-01` must leave a durable scheduled-generation hook or artifact path without changing the brief surface
- `DEV-02` must make the brief more actionable using existing judge/forecast context
- `DEV-03` must close degraded fallback and contract edges without expanding scope
- `ADMIN-01` must leave artifact-based proof for schedule, usability, and degraded behavior

## Anti-drift rules
- do not create a second brief API or parallel morning-brief product surface
- do not duplicate synthesis logic already present in brief/judge/forecast paths
- do not hide degraded generation behind nominal success wording
- keep `BATCH-25` bounded to the morning brief pipeline, not broader briefing/product redesign
