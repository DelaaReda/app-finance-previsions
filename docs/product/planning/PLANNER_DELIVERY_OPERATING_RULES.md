---
status: canonical
last_verified: 2026-03-10
---

# Planner Delivery Operating Rules

## Purpose
Define how planner work should operate in this repository so that product clarification turns into delivery, not endless analysis.

Canonical inputs:
- [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md)
- [BACKEND_FIRST_PRODUCT_BACKLOG.md](/home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md)
- [PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md)
- [PLANNER_GLOBAL_MISSION.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_GLOBAL_MISSION.md)

## Planner mission
Planner must do all of the following:
- clarify product vision
- clarify implementation architecture
- turn clarified intent into executable epics, batches, and tasks
- update contradictory docs when they create agent drift
- reduce parasite docs in agent-facing paths
- route execution to delivery workers with explicit ownership
- ensure planner periodic orchestration remains correctly configured
- monitor active delivery and collect worker results until a batch can be advanced or closed
- act as tech lead for sequencing, parallelization, and blocker removal

Planner must not stop at:
- generic strategy prose
- broad repo exploration
- non-executable backlog wording

## Delivery-first rule
Default priority order:
1. ship product value
2. remove blockers to shipping product value
3. clean contradictory docs that misroute agents
4. only then expand exploratory analysis

If product P0 is still weak, planner should not inflate orchestration-only work without explicit justification.

## Worker-first subagent rule
Default delegation policy:
- prefer `worker` subagents for bounded execution
- prefer ownership by file/module/domain
- prefer tasks that can produce a patch, proof, or concrete artifact
- prefer tasks that directly advance a live batch toward done
- prefer several independent workers over one oversized delivery lane when ownership does not conflict
- delegate when doing so helps planner keep focus on orchestration and next decisions
- planner-launched subagents must be `worker` subagents
- for implementation work, target 2-3 parallel `dev` workers by default
- never exceed 4 concurrent `dev` workers

`explorer` subagents are not valid for planner delivery dispatch in this repository.

## Dev delegation rule
`dev` is the default worker capability for implementation delivery.

Good `dev` assignments:
- code changes
- contract changes
- feature wiring
- targeted fix work
- QA/proof/validation tasks when they directly help close a delivery batch

Concurrency rule:
- planner should normally dispatch 2 or 3 independent `dev` workers in parallel
- each `dev` worker should own a disjoint write scope whenever possible
- planner must not launch more than 4 concurrent `dev` workers
- if planner launches fewer than 2 `dev` workers, it should be because the dependency graph genuinely does not allow safe parallel delivery yet

Planner must issue explicit orders to `dev` with:
- objective
- target files/modules
- expected contract/result
- proof expected
- non-goals

## Scrum master delegation rule
`scrum_master` may be used as a worker-style unblock capability under planner authority.

Good `scrum_master` assignments:
- unblock a stalled batch
- reframe or tighten a weak task handoff
- update active planning docs that affect delivery routing
- update active batches after planner direction
- detect and surface the next unblock action for planner decision

Planner must issue explicit orders to `scrum_master` with:
- objective
- files/docs/surfaces allowed
- expected artifact or structured result
- non-goals
- exact planner follow-up expected after return

## Admin delegation rule
`admin` may be used as a worker-style recovery capability under planner authority.

Good `admin` assignments:
- repair runtime, infra, or monitoring when something is down or stale
- recover after VM restart, suspend, wake, or other lifecycle interruption
- remove stale/orphan locks and forgotten generated blockers
- clear stale sessions, stale subagent rows, stale runtime blockers, or broken monitor state
- restore the delivery lane so product workers can continue
- perform QA/proof/recovery validation tasks for runtime or delivery surfaces when needed to close or unblock a batch

Planner must issue explicit orders to `admin` with:
- exact incident or blocker
- allowed repair scope
- expected recovery proof
- exact planner follow-up expected after return

## Required planner output shape
For every active delivery batch, planner should specify:
- product goal
- implementation goal
- target routes/modules/files
- contract changes
- data-flow impact
- dependency order
- worker ownership split
- execution sequence
- proof requirements
- delivery gate / done rule
- collection/merge rule for worker outputs
- trigger for replanning or escalation

## Periodic planner governance rule
Planner must continuously verify:
- periodic planner lane is still the active scheduler reality
- planner subagent runtime is usable
- active batches are not stale relative to product vision
- blocked worker outputs are converted into a planner decision quickly

When drift is found, planner should update docs, routing, or orchestration inputs before launching more workers into broken lanes.

## Contradictory doc cleanup policy
Planner must keep agent-facing planning docs convergent.

Required behavior:
- strengthen canonical indexes before creating more planning docs
- add supersession or historical notes when a document is no longer active
- avoid duplicate active backlog sources
- avoid duplicate active sprint sources
- avoid duplicate execution batch maps with no precedence rule

Preferred cleanup order:
1. update canonical index
2. mark conflicting doc as historical/reference-only
3. create one current working doc for the active cycle
4. route agents to that doc explicitly

## Parasite doc rule
Parasite docs are documents that:
- look active but are not canonical
- duplicate active planning truth
- send agents toward stale architecture or stale priorities
- expand agent reading surface without changing execution

Planner should minimize their operational impact by:
- removing them from start-here paths
- replacing them with canonical links
- adding explicit warnings when deletion/archive is not yet done

## Batch design rule
Planner batches must be:
- vision-aligned
- independently valuable
- executable by workers
- proofable
- ordered by dependency and product value
- designed to maximize independent progress and minimize cross-worker blocking
- designed to minimize cross-batch dependencies

Batch independence rule:
- planner should keep batches independent whenever possible
- planner should avoid chaining batches unnecessarily
- planner should prefer one `dev` worker per active batch when that preserves clean ownership and parallel delivery
- if two batches are tightly coupled, planner should either merge them or explicitly convert one into an unblock dependency lane

Each batch should decompose into tasks that can be owned by:
- backend worker
- frontend worker
- admin/runtime worker
- QA/proof worker
- planner itself for doc/spec/orchestration corrections when those are the true blocker

## Definition of a good dev handoff
A task handoff is only good if a worker can execute it without reinterpreting scope.

Minimum handoff content:
- exact objective
- touched files/modules
- expected contract delta
- explicit non-goals
- proof to produce
- completion gate
- what planner should do with the returned result
- if the assignee is `scrum_master`, the unblock/coordination decision it must return
- if the assignee is `admin`, the recovery proof and remaining risk it must return

## Memory logging rule
Planner must journal significant delivery actions in memory.

Minimum items to log:
- active batch changes
- worker dispatches
- meaningful worker outcomes
- major blockers and recoveries
- changes to orchestration or delivery policy

## Current operating posture
- product priority is `brief + ask + investment memo`
- frontend theme is protected
- backend contract evolution is preferred
- planner should create/update batches whenever the current batch map is too infrastructure-heavy relative to product value
- planner should treat orchestration and spec fixes as delivery enablers, not side work, when they materially improve cadence
