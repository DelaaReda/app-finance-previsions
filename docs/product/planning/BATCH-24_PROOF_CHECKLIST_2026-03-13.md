---
status: active_supporting_doc
last_verified: 2026-03-13
batch: BATCH-24
owner_role: scrum_master
---

# BATCH-24 Proof Checklist - 2026-03-13

Purpose: give planner a compact acceptance checklist for `BATCH-24` lane closure and merge decisions.

Scope:
- `DEV-01` prioritization + duplicate suppression + fatigue window behavior
- `DEV-02` monitor/frontend urgency surfacing
- `DEV-03` bounded cleanup + contract finishing
- `ADMIN-01` runtime proof and batch-close evidence

Batch defaults used for acceptance:
- duplicate/fatigue suppression target window: `15 minutes` rolling on the same alert fingerprint
- urgent/escalated alerts may bypass suppression when severity increases
- canonical urgent-path SLA proof: generation timestamp to surfaced timestamp on monitor/API proof artifact, with target `<= 60 seconds`
- `DEV-02` preferred visible surfacing targets: existing monitor output plus existing frontend/shared UI paths under `apps/web/src/domains/forecasts/components/*` and `apps/web/src/platform/*`

Non-negotiables for all lanes:
- stay on the existing alerting/monitor pipeline
- no new daemon, queue, microservice, or parallel alert surface
- keep current monitor/dashboard consumers backward-compatible
- keep proofs explicit enough for planner merge without reinterpretation

## Lane closure gates and expected proof

### `BATCH-24-DEV-01`

Closure gates:
- [ ] additive prioritization metadata exists on the current alert payload path
- [ ] duplicate suppression works across a short rolling window on the existing pipeline
- [ ] duplicate suppression works against the batch default `15 minute` rolling window, or a clearly justified equivalent implementation
- [ ] suppression/fatigue reason is explicit when an alert is withheld
- [ ] urgent/high-priority alerts still surface even while lower-priority duplicates are suppressed
- [ ] `DEV-02` receives an explicit handoff of new fields/UI hooks

Expected evidence:
- exact files changed
- concise field contract summary: added fields, no removed/renamed required fields
- one concrete proof example showing:
  - alert prioritized
  - duplicate suppressed
  - suppression/fatigue reason emitted
- explicit note that no parallel alert subsystem was introduced

Planner merge criteria:
- merge if the payload stays additive, urgent visibility is preserved, and `DEV-02` can consume the new fields without schema rework
- no-merge if there is any schema break, hidden suppression with no reason field, missing `DEV-02` contract handoff, or architecture spill into a second alert path

### `BATCH-24-DEV-02`

Closure gates:
- [ ] urgency tiers/top queue are visible through existing monitor/frontend surfaces
- [ ] existing widgets/shared UI plumbing are reused
- [ ] `DEV-01` additive fields are consumed without introducing a second frontend subsystem
- [ ] user-facing ordering clearly favors urgent/action-worthy alerts
- [ ] any remaining contract edge for `DEV-03` is named explicitly

Expected evidence:
- exact files changed
- concise UI wiring summary from backend field to visible widget/card behavior
- one proof artifact showing urgency tiers or top-queue ordering on the existing surface
- explicit note of any residual edge handed to `DEV-03`, or `none`

Planner merge criteria:
- merge if the improvement is user-visible on the current surface and the implementation stays on shared frontend/monitor plumbing
- no-merge if urgency is not visible, the lane invents a separate UI path, or `DEV-03` receives an ambiguous cleanup/contract handoff

### `BATCH-24-DEV-03`

Closure gates:
- [ ] remaining contract edges from `DEV-02` are closed or explicitly retired
- [ ] helper cleanup stays regression-safe and bounded to the same alerting path
- [ ] no duplicate helper logic remains on the active path
- [ ] scope stays cleanup/finishing only and does not reopen product shape

Expected evidence:
- exact files changed
- concise note of the contract edge(s) closed
- concise note of helper cleanup performed and why it is safe
- explicit statement that no new user-facing subsystem or broad refactor was added

Planner merge criteria:
- merge if the lane is clearly bounded cleanup/finishing work and leaves the batch implementation path coherent for proof
- no-merge if the lane balloons into refactor/platform work, reopens `DEV-01` or `DEV-02` scope, or leaves unresolved contract ambiguity for `ADMIN-01`

### `BATCH-24-ADMIN-01`

Closure gates:
- [ ] live monitor/API regression proof is captured on the current runtime path
- [ ] proof shows duplicate/noise reduction is active
- [ ] proof shows urgent alerts still surface correctly
- [ ] proof is artifact-based, not narrative-only
- [ ] proof is sufficient for planner to close `BATCH-24` and unblock `BATCH-25`

Expected evidence:
- proof artifact path(s)
- concise runtime validation summary for monitor/API behavior
- one concrete proof example that dedupe/suppression is active
- one concrete proof example that urgent alerts remain surfaced
- one concrete proof example that urgent alerts surfaced in `<= 60 seconds` on the canonical path
- explicit note that current consumers stayed backward-compatible

Planner merge criteria:
- merge if proof artifacts demonstrate regression-safe runtime behavior plus the intended prioritization/dedupe outcome
- no-merge if evidence is only descriptive, does not show live behavior, or cannot prove both noise reduction and urgent-alert visibility

## Explicit planner merge / no-merge rules

Merge:
- lane result contains exact files changed, a bounded change summary, and lane-specific proof listed above
- architecture remains on the existing alerting + monitor pipeline
- handoff to the next lane is explicit where required

No-merge:
- missing proof artifacts or only narrative claims
- backward-compatibility risk is unresolved
- lane introduces a second pipeline/surface or cross-batch scope
- runtime says `running` but there is no active worker and no fresh artifact trail

## Blocker escalation rules

Escalate to planner immediately when:
- a lane proposes a new daemon, queue, microservice, or parallel alert UI
- a required field/contract change would break existing monitor/dashboard consumers
- runtime/workboard says `running` but there is no active worker or fresh result artifact
- a lane cannot show explicit proof for dedupe, urgency, or backward compatibility
- `DEV-03` expands beyond cleanup/contract finishing
- `ADMIN-01` cannot capture live runtime proof on the canonical path

Escalation action:
- planner either redispatches the same lane with a tighter bounded brief, or reroutes to `admin` / `scrum_master` if the blocker is runtime/proof/doc drift rather than implementation

## Next planner move after each lane result

- `DEV-01` pass: dispatch `DEV-02` with the additive field contract and proof note attached
- `DEV-01` no-merge/block: redispatch `DEV-01` with the exact schema/architecture blocker called out
- `DEV-02` pass: dispatch `DEV-03` with the named residual contract edge, if any
- `DEV-02` no-merge/block: return to `DEV-02` with the missing visible urgency proof or UI-scope correction
- `DEV-03` pass: dispatch `ADMIN-01` for runtime proof and batch-close evidence
- `DEV-03` no-merge/block: return to `DEV-03` with a strict cleanup-only correction
- `ADMIN-01` pass: close `BATCH-24`, mark batch proof-complete, and allow planner to advance to `BATCH-25`
- `ADMIN-01` no-merge/block: keep `BATCH-24` active and reroute only the proof/runtime gap without reopening finished dev scope unless runtime evidence proves a real regression
