---
status: canonical
last_verified: 2026-03-13
---

# Vision-Aligned Delivery Batches - 2026-03-13

## Purpose
Define the current dispatch window from the live `BATCH-*` runtime namespace after `BATCH-23` completion, while preserving older cycle docs as historical context only.

Canonical references:
- [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md)
- [CURRENT_EXECUTION_FOCUS_2026-03-13.md](/home/venom/analyse-financiere/docs/product/planning/CURRENT_EXECUTION_FOCUS_2026-03-13.md)
- [PLANNER_GLOBAL_MISSION.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_GLOBAL_MISSION.md)
- [PLANNER_DELIVERY_OPERATING_RULES.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_DELIVERY_OPERATING_RULES.md)

## Namespace rule
- Active dispatch namespace: `BATCH`
- Historical bridge namespace: `VB-*`
- Planner, monitor, doctor, and worker handoffs must treat `VB-*` as non-dispatchable historical context for this cycle

## Active runtime window
### BATCH-23 - Tax, Fees, and Slippage Awareness
Status:
- `DONE`

Role in current cycle:
- immediate previous completion
- proof-bearing reference for the current runtime window
- dependency already satisfied for `BATCH-24`

### BATCH-24 - Alerting Intelligence V2
Status:
- `READY_DEV`

Current next action:
- claim `BATCH-24-DEV-01`

Product outcome:
- prioritize alerts according to real decision impact
- reduce noise through dedupe and fatigue control
- preserve a clear urgent top queue for action-worthy events

Implementation architecture:
- iterate on existing monitor and alert channels; preserve the current single ingestion and dispatch pipeline
- keep contract changes backward-compatible with the current monitor dashboard cards
- extend existing alert payloads with prioritization, dedupe, and suppression metadata instead of introducing a parallel alert surface
- use a default `15 minute` rolling suppression window on the same alert fingerprint unless the existing cadence requires a smaller equivalent implementation
- allow urgent/escalated alerts to bypass suppression when severity increases
- primary reuse targets for the current batch:
  - `apps/monitor/server.py`
  - `scripts/monitor_agents.sh`
  - `scripts/fc_health_check.sh`
  - `apps/api/src/platform/legacy/jobs/market_brief.py`
  - `apps/web/src/domains/forecasts/components/*` and `apps/web/src/platform/*` for the `DEV-02` visible surfacing lane

Execution sequence:
1. `BATCH-24-DEV-01`: implement the first delivery slice on the existing alerting pipeline with priority ordering, duplicate suppression, and suppression-window/fatigue controls.
2. `BATCH-24-DEV-02`: wire the alert center and urgency tiers through existing widgets and shared frontend plumbing.
3. `BATCH-24-DEV-03`: close the batch with regression-safe helper cleanup and any minimal contract adjustments still required on the same path.
4. `BATCH-24-ADMIN-01`: capture runtime proof, dedupe-rate evidence, and monitor/API regression proof after the dev chain.

Completion gates:
- duplicate alerts are materially reduced
- critical alerts surface in under one minute, proven from generation timestamp to surfaced timestamp on the canonical monitor/API path
- current monitor/dashboard consumers stay backward-compatible
- delivery leaves proof artifacts clear enough for planner merge and GOV review

### BATCH-25 - Autonomous Morning Brief Pipeline
Status:
- `WAITING_DEP`

Dependency:
- `BATCH-24`

Planner rule:
- do not dispatch while `BATCH-24` remains the active batch

## Execution guidance
- dispatch from `BATCH-24` first
- keep `BATCH-23` as the recent completed reference, not as active work
- if a lane reports `running` without an active worker, reroute or redispatch explicitly instead of assuming progress
- treat `BATCH-25` as downstream queue truth only
- if a worker or doc still proposes `BATCH-23` as the active batch, correct the doc/handoff before dispatching more work

## Done gate for cycle alignment
- queue and workboard point to the same `active_cycle`
- this document and [CURRENT_EXECUTION_FOCUS_2026-03-13.md](/home/venom/analyse-financiere/docs/product/planning/CURRENT_EXECUTION_FOCUS_2026-03-13.md) are the only cycle docs surfaced by the planning index as current
- planner observability exposes `BATCH-24` as the active runtime window instead of a stale `BATCH-23` reference

## Runtime pivot update - 2026-03-13T10:43:18Z
- `BATCH-25-PLAN` passed the hard planner delivery proof gate after canonical KV evidence was attached on the workboard node.
- Remaining planner work is low-severity quality backfill before or alongside downstream BATCH-25 execution.

## Runtime pivot update - 2026-03-13T10:54:51Z
- BATCH-25 is now in active execution, with planner dispatch reaching `BATCH-25-DEV-01` running state.
- The execution path has transitioned from planner proof normalization to delivery supervision on the brief-generation implementation stream.
