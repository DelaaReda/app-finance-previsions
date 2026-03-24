---
status: working
last_verified: 2026-03-10
---

# Vision-Aligned Delivery Batches - 2026-03-10

Superseded on 2026-03-12 by [VISION_ALIGNED_DELIVERY_BATCHES_2026-03-12.md](/home/venom/analyse-financiere/docs/product/planning/VISION_ALIGNED_DELIVERY_BATCHES_2026-03-12.md).

This file remains the batch-map snapshot that introduced the `VB-*` bridge. It is historical context, not the active dispatch map.

## Purpose
Translate the canonical product vision into executable delivery batches with explicit dev execution guidance.

Canonical references:
- [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md)
- [BACKEND_FIRST_PRODUCT_BACKLOG.md](/home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md)
- [PLANNER_DELIVERY_OPERATING_RULES.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_DELIVERY_OPERATING_RULES.md)
- [PLANNER_GLOBAL_MISSION.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_GLOBAL_MISSION.md)

## Active delivery priority
1. brief that is decision-ready on open
2. deep-dive memo that is actionable on ask
3. personal context injection without breaking no-context usefulness
4. minimal frontend wiring in the current shell

## Planner execution posture for these batches
- planner remains periodic orchestrator, not a passive backlog writer
- planner should use worker subagents as the default delivery lane
- planner-launched subagents should be worker subagents only
- planner should collect results and re-route quickly when a worker returns a blocker
- planner should parallelize independent batches/tasks whenever ownership is disjoint
- planner should update specs/docs/orchestration if those are the real blocker to batch progress
- planner may delegate unblock/doc/batch-maintenance work to `scrum_master` so planner keeps focus on orchestration and final decisions
- planner may delegate runtime/infra/monitoring recovery work to `admin` so delivery workers are not blocked by stale or down operational state
- planner should keep 2-3 independent `dev` workers active in parallel when the active batch map permits it, with a hard cap of 4 concurrent `dev` workers
- planner should keep batches independent and prefer one `dev` worker per active batch when possible

## Batch VB-01 - Daily Brief Contract Lock
Priority:
- P0

Product outcome:
- homepage/opening brief is explainable and usable without frontend invention

Primary surfaces:
- `/api/brief/daily`
- `/api/copilot/start`
- `/api/copilot/context`

Primary files/modules:
- `apps/api/src/domains/forecasts/api/brief.py`
- `apps/api/src/domains/copilot/application/copilot_service.py`
- `apps/api/src/domains/copilot/api/copilot.py`
- `apps/api/src/domains/forecasts/tests/test_brief_route_contract.py`
- `apps/api/src/domains/copilot/tests/test_brief_of_day_feature.py`

Contract target:
- required fields:
  - `summary`
  - `market_regime` or equivalent explicit sentiment/regime field
  - `top_opportunities`
  - `top_risks`
  - `freshness`
  - `sources`
- compatibility fields may remain, but the normalized contract must be deterministic

Worker split:
- Backend worker A:
  - normalize the brief contract at source
  - keep fallback/degraded behavior explicit
- Backend worker B:
  - propagate the normalized brief into copilot start/context surfaces
- QA/proof worker:
  - produce route-level proof for nominal + fallback + scoped modes

Parallelization note:
- Backend worker A and B may run sequentially if contract shape is still moving.
- QA/proof worker should start as soon as the contract is stable enough to freeze assertions.

Execution sequence:
1. lock the route-level brief contract
2. propagate the same shape into copilot start/context
3. add/update proof tests
4. produce API proof artifact

Non-goals:
- no frontend redesign
- no new brief endpoint family

Done gate:
- brief contract stable on all three surfaces
- degraded mode explicit
- proof exists for direct route calls and copilot entry points

## Batch VB-02 - Investment Memo Contract Lock
Priority:
- P0

Product outcome:
- `/api/copilot/ask` returns a structured investment memo, not only a generic assistant blob

Primary surfaces:
- `/api/copilot/ask`
- downstream consumers of ask response

Primary files/modules:
- `apps/api/src/domains/copilot/application/copilot_service.py`
- `apps/api/src/domains/copilot/api/copilot.py`
- `apps/api/src/domains/copilot/tests/test_copilot_service.py`
- route-level ask contract tests

Contract target:
- `memo.verdict`
- `memo.horizon`
- `memo.why`
- `memo.risks`
- `memo.confidence`
- `memo.freshness`
- `memo.sources`
- optional:
  - `memo.next_steps`
  - `memo.invalidation`

Worker split:
- Backend worker A:
  - normalize memo generation in service layer
- Backend worker B:
  - keep API envelope compatibility for current UI consumers
- QA/proof worker:
  - prove nominal and insufficient-source behavior

Parallelization note:
- Service-layer normalization and route-envelope compatibility can run in parallel only if ownership is file-disjoint.

Execution sequence:
1. define canonical memo shape in service output
2. mirror it through route response without breaking compatibility
3. add route and service contract proofs
4. document degraded memo behavior explicitly

Non-goals:
- no LLM-provider redesign
- no frontend shell rewrite

Done gate:
- memo object exists and is deterministic
- insufficient evidence is explicit in payload
- existing consumers remain compatible

## Batch VB-03 - Portfolio Context Injection
Priority:
- P1

Product outcome:
- recommendations become personal when watchlist/portfolio exists, but remain useful without it

Primary surfaces:
- `/api/copilot/context`
- `/api/portfolios`
- `/api/portfolios/{portfolio_id}`
- `/api/portfolios/{portfolio_id}/performance`

Primary files/modules:
- copilot context service
- portfolio services/routes in `market_data`
- relevant portfolio tests

Contract target:
- explicit difference between:
  - market-wide reasoning
  - portfolio-aware reasoning
- payload explains when portfolio context changed prioritization or verdict

Worker split:
- Backend worker A:
  - resolve saved context and inject it deterministically
- Backend worker B:
  - expose context influence markers in response contracts
- QA/proof worker:
  - compare with-context vs without-context outputs

Execution sequence:
1. normalize saved portfolio/watchlist resolution
2. inject context into ask/brief prioritization
3. expose influence markers
4. prove fallback without saved context

## Batch VB-04 - Minimal Frontend Wiring
Priority:
- P1

Product outcome:
- current shell renders backend truth instead of placeholder posture

Primary surfaces:
- current hero brief
- current copilot ask/deep-dive rendering

Primary files/modules:
- `apps/web/src/domains/forecasts/contracts/apiConnector.js`
- `apps/web/src/domains/forecasts/pages/app.js`
- relevant page tests

Execution rule:
- only wiring, mapping, badges, degraded states, memo rendering
- no shell redesign
- no design-token rewrite

Worker split:
- Frontend worker:
  - map normalized brief and memo fields into existing widgets
- QA/proof worker:
  - browser/UI proof under current theme

Parallelization note:
- Frontend worker can run in parallel with QA proof preparation once backend contract lock is explicit.

Execution sequence:
1. consume normalized brief in hero/current entry point
2. consume normalized memo in ask/deep-dive surfaces
3. expose freshness/source/degraded badges
4. produce browser proof

Done gate:
- current theme preserved
- no frontend-only business reconstruction required
- nominal + degraded UI proof exists

## Batch VB-05 - Planning Doc Cleanup For Agents
Priority:
- P0.5

Product outcome:
- agents stop routing through contradictory planning docs

Primary surfaces:
- `docs/product/planning/README.md`
- active planner working docs
- stale planning snapshots that still look active

Planner tasks:
- strengthen canonical start-here index
- mark conflicting docs as historical/reference-only
- create explicit current-cycle execution docs
- remove duplicate active signals from agent-facing paths

Worker split:
- Planner-owned doc batch
- optional doc worker for bounded doc patching only

Execution note:
- this batch should be rerun whenever new contradictory planner docs appear or when agent drift is observed in delivery.

Execution sequence:
1. identify docs that still look active to agents
2. mark or supersede them
3. route agents to the current batch map
4. verify no duplicate active entrypoint remains in planning index

Done gate:
- one canonical planning entrypoint
- one current working batch map
- clear precedence rules for agents

## Recommended immediate dispatch order
1. `VB-05` doc cleanup to reduce agent drift
2. `VB-01` brief contract lock
3. `VB-02` memo contract lock
4. `VB-04` minimal frontend wiring
5. `VB-03` portfolio context injection

## Orchestrator note
When delivery allows it, the planner should dispatch in parallel:
1. `VB-05` planner/doc correction lane
2. `VB-01` backend brief lane
3. `VB-02` backend memo lane

Then, once contracts stabilize:
4. `VB-04` frontend wiring lane
5. `VB-03` context lane

Parallel ownership preference:
- one `dev` worker should own one active implementation batch whenever safe
- `admin` and `scrum_master` should be used to remove blockers around those batches rather than creating extra dependency chains between dev lanes

## Planner note
If new work does not fit one of these batches cleanly, planner should create a new batch only if:
- it is required by the product vision
- it cannot be absorbed into an existing batch without losing ownership clarity
- it has a real proof path
