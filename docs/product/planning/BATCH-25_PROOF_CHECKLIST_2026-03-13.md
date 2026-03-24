---
status: active_supporting_doc
last_verified: 2026-03-13
batch: BATCH-25
owner_role: planner
---

# BATCH-25 Proof Checklist - 2026-03-13

Purpose: give planner a compact acceptance checklist for `BATCH-25` lane closure and merge decisions.

Scope:
- `DEV-01` scheduled generation / durable artifact
- `DEV-02` action-oriented brief synthesis
- `DEV-03` degraded fallback + contract finish
- `ADMIN-01` runtime proof

Non-negotiables for all lanes:
- stay on the existing brief route and supporting pipeline
- no new parallel brief API or scheduler stack
- keep degradation explicit
- keep proof artifacts clear enough for planner merge without reinterpretation

## Lane closure gates and expected proof

### `BATCH-25-DEV-01`

Closure gates:
- [ ] morning brief generation is tied to a durable scheduled or refreshable path on the existing stack
- [ ] current brief route schema remains the delivery surface
- [ ] freshness/degraded metadata is explicit where generation can age or fail
- [ ] `DEV-02` receives an explicit handoff of additive fields/hooks

Expected evidence:
- exact files changed
- concise note showing where the morning brief artifact is produced or refreshed
- contract summary of any additive metadata
- explicit note that no second brief surface was introduced

Planner merge criteria:
- merge if scheduled generation is materially established on the existing path and the brief schema stays compatible
- no-merge if the lane invents a second brief surface, hides scheduling inside an opaque path, or leaves `DEV-02` with no usable handoff

### `BATCH-25-DEV-02`

Closure gates:
- [ ] the brief now contains action-oriented guidance built from existing forecast/judge context
- [ ] confidence/freshness framing is visible enough for a morning decision pass
- [ ] the implementation reuses current synthesis sources instead of duplicating them
- [ ] any residual degraded/contract edge for `DEV-03` is explicit

Expected evidence:
- exact files changed
- concise note mapping existing source inputs to new brief outputs
- one concrete example of action-oriented brief content
- explicit residual edge for `DEV-03`, or `none`

Planner merge criteria:
- merge if the brief becomes more actionable without adding a new synthesis surface
- no-merge if the lane is still descriptive-only, duplicates synthesis logic, or hands `DEV-03` an ambiguous cleanup scope

### `BATCH-25-DEV-03`

Closure gates:
- [ ] degraded fallback remains explicit and user-usable
- [ ] remaining contract edges from `DEV-02` are closed or retired
- [ ] the current brief route remains backward-compatible
- [ ] scope stays bounded to fallback/finish work

Expected evidence:
- exact files changed
- concise degraded-mode behavior note
- concise contract-compatibility note
- explicit statement that no broad refactor was added

Planner merge criteria:
- merge if degraded behavior is explicit, usable, and bounded
- no-merge if fallback is vague, hidden, or the lane expands into platform redesign

### `BATCH-25-ADMIN-01`

Closure gates:
- [ ] runtime proof shows the morning brief path produces or serves the expected artifact
- [ ] runtime proof shows degraded mode clearly when nominal generation is not available
- [ ] proof is artifact-based, not narrative-only
- [ ] proof is sufficient for planner to close `BATCH-25`

Expected evidence:
- proof artifact path(s)
- concise runtime validation summary for the brief route and generation path
- one concrete proof example of nominal morning brief availability
- one concrete proof example of degraded fallback clarity

Planner merge criteria:
- merge if proof demonstrates both nominal and degraded usability on the current surface
- no-merge if evidence is only descriptive or cannot prove fallback clarity

## Explicit planner merge / no-merge rules

Merge:
- lane result contains exact files changed, a bounded change summary, and lane-specific proof
- architecture remains on the existing brief/judge/forecast path
- handoff to the next lane is explicit where required

No-merge:
- missing proof artifacts or only narrative claims
- hidden degraded behavior
- second brief surface or scheduler stack introduced
- broad scope expansion beyond the morning brief pipeline

## Blocker escalation rules

Escalate to planner immediately when:
- a lane proposes a second brief API, a separate scheduler stack, or a parallel summary surface
- required changes would break the current brief route schema
- degraded mode cannot be made explicit on the current surface
- schedule proof cannot be captured from the existing runtime path
- `DEV-03` expands beyond fallback/contract finish

Escalation action:
- planner either redispatches the same lane with a tighter bounded brief, or reroutes to `admin` if the blocker is runtime/proof drift rather than implementation

## Next planner move after each lane result

- `DEV-01` pass: dispatch `DEV-02` with the additive contract and artifact path attached
- `DEV-01` no-merge/block: redispatch `DEV-01` with the exact scheduling/schema blocker called out
- `DEV-02` pass: dispatch `DEV-03` with the named degraded/contract edge, if any
- `DEV-02` no-merge/block: return to `DEV-02` with the missing action-value proof or synthesis-scope correction
- `DEV-03` pass: dispatch `ADMIN-01` for runtime proof and batch-close evidence
- `DEV-03` no-merge/block: return to `DEV-03` with a strict fallback-only correction
- `ADMIN-01` pass: close `BATCH-25` and let planner advance to the next active batch
- `ADMIN-01` no-merge/block: keep `BATCH-25` active and reroute only the proof/runtime gap unless runtime proof reveals a real implementation regression
