---
status: active_supporting_doc
last_verified: 2026-03-13
batch: BATCH-24
---

# BATCH-24 Execution Handoff - 2026-03-13

## Goal
Deliver `Alerting Intelligence V2` on the existing alerting and monitor pipeline without creating a second alert system.

Primary user value:
- urgent, action-worthy alerts must rise to the top
- duplicate/noisy alerts must be suppressed before they fatigue the user
- current monitor/dashboard consumers must keep working

## Runtime truth at handoff time
- Active batch: `BATCH-24`
- Immediate lane: `BATCH-24-DEV-01`
- Recent completed dependency reference: `BATCH-23`
- `BATCH-24-DEV-01` previously appeared as `running` in runtime with no active subagent attached, so planner explicitly relaunched a bounded dev worker from the main session

## Mandatory architecture constraints
- Reuse the current pipeline; do not add a new daemon, queue, or alert microservice
- Keep backward compatibility with the current monitor/dashboard card contract
- Prefer extending existing payloads with prioritization/dedupe metadata over introducing parallel schemas
- Keep changes minimal and local to the alerting path

## Preferred module scope
Primary targets:
- `apps/monitor/server.py`
- `scripts/monitor_agents.sh`
- `scripts/fc_health_check.sh`
- `apps/api/src/platform/legacy/jobs/market_brief.py`

DEV-02 frontend/monitor surfacing targets:
- `apps/web/src/domains/forecasts/components/*`
- `apps/web/src/platform/*`
- if the visible urgency/top-queue behavior is rendered directly from monitor output, `apps/monitor/server.py` remains an allowed surfacing target before inventing new frontend plumbing

Secondary rule:
- if a slice can be completed inside one of these paths, do not spill into adjacent domains

## Fixed operating assumptions for this batch
- default duplicate/fatigue suppression window: `15 minutes` rolling for the same alert fingerprint on the current active path
- urgent or escalated alerts may bypass suppression when severity meaningfully increases
- admin SLA proof method for the urgent path: compare generation timestamp to surfaced timestamp on the canonical monitor/API path and capture at least one proof showing `<= 60 seconds`
- if an existing runtime cadence forces a smaller internal window, the implementation may choose a shorter mechanism, but planner proof must still show materially reduced duplicate noise over the same practical user session window

## Delivery lanes
### BATCH-24-DEV-01
Mission:
- implement the first useful backend/runtime slice for alert prioritization plus duplicate suppression and fatigue-window behavior

Expected code shape:
- add ranking/prioritization metadata on top of the existing alert output
- suppress obvious duplicate events across the default `15 minute` rolling window unless the existing path requires a smaller internal cadence to achieve the same user-visible behavior
- add explicit suppression/fatigue reason fields when an alert is withheld

Contract expectations:
- existing alert consumers must still parse the payload
- any new fields must be additive
- urgent alerts must remain visible even when suppression is active for lower-priority duplicates

Completion evidence:
- clear artifact summary of the prioritization/dedupe behavior added
- exact files changed
- note for `DEV-02` describing which fields/UI hooks are now available

Current planner-delivered additive contract for `DEV-02` consumption:
- per emitted risk item:
  - `priority`
  - `priority_score`
  - `horizon`
  - `alert_fingerprint`
  - `suppression_window_minutes`
  - `suppressed`
  - `suppression_reason`
  - `duplicate_count`
  - `urgent_bypass`
  - `priority_rank`
- batch-level:
  - `suppressed_risks`
  - `alerting_metadata`

### BATCH-24-DEV-02
Mission:
- expose urgency tiers and the new prioritization state through the existing frontend/monitor surface

Dependency:
- `BATCH-24-DEV-01`

Expected scope:
- reuse existing widgets/shared UI wiring
- no net-new frontend subsystem
- consume additive fields created by `DEV-01`

Completion evidence:
- user-visible urgency tiers/top queue behavior
- exact files changed
- explicit note on any remaining contract edge for `DEV-03`

### BATCH-24-DEV-03
Mission:
- finish minimal contract cleanup/regression-safe helpers on the same path and close the batch implementation lane

Dependency:
- `BATCH-24-DEV-02`

Expected scope:
- no duplicate helpers
- tighten minimal contract edges still open after `DEV-02`
- keep patch bounded and mergeable

### BATCH-24-ADMIN-01
Mission:
- validate runtime truth and capture proof after the dev chain lands

Dependency:
- `BATCH-24-DEV-03`

Required proof:
- monitor/API regression proof
- evidence that duplicate/noise reduction is active
- evidence that urgent alerts still surface correctly
- at least one urgent alert trace proving generation-to-surfacing latency `<= 60 seconds` on the canonical path

## Planner merge criteria
- `DEV-01` must unblock `DEV-02` with additive fields and no schema break
- `DEV-02` must show clear user-visible alert ordering/urgency improvement
- `DEV-03` must not balloon scope beyond cleanup and safe contract finishing
- `ADMIN-01` must leave explicit proof artifacts, not only narrative claims

## Anti-drift rules
- do not reframe `BATCH-24` as a brand new alerting platform
- do not reopen `BATCH-23`
- do not dispatch `BATCH-25` while `BATCH-24` is still active
- if runtime says `running` but no worker is alive, planner must redispatch explicitly
