---
status: active
last_verified: 2026-04-15
---

# Judge-Parity Endpoint Architecture

## Purpose
Define the target backend endpoint architecture for Finance Copilot and use `judge` as the best current reference implementation.

`judge` is the best current model, not a perfect template. Reuse its strong patterns. Do not clone its accidental monoliths.

## When Agents Must Read This
- when creating or refactoring a non-trivial backend endpoint
- when adding a new product-facing API contract
- when moving logic out of a fat route
- when trying to make an endpoint "complete" rather than merely "responding"

If an endpoint affects `brief`, `ask/open`, `portfolio`, `personal-finance`, `copilot`, or decision quality, this doc is mandatory.

## Target Architecture
Every non-trivial endpoint should converge toward these layers.

### 1. Shared contract
- Public response shapes belong in `packages/contracts/*` when the endpoint is product-critical or reused by multiple consumers.
- Local schema aliases may exist, but they must not diverge from the shared contract.
- Frontend code must not depend on an ad hoc route-owned JSON shape.

### 2. Application layer
- Business logic lives in `apps/api/src/domains/<domain>/application/*`.
- This includes scoring, aggregation, normalization, payload building, provider orchestration, quality checks, and fallback decisions.
- Routes must not hold deep business logic.

### 3. Endpoint service layer
- Non-trivial endpoints should expose a reusable endpoint service layer in the same domain.
- This layer owns:
  - payload assembly
  - standard metadata
  - degraded mode / fallback semantics
  - reusable projections for other surfaces
- Route code should delegate here.

### 4. Thin API route
- Route code should do:
  - input parsing
  - simple validation
  - auth/permissions if needed
  - cache/singleflight orchestration if truly endpoint-specific
  - service call
  - response envelope
- Route code should not become the product engine.

### 5. Standard metadata
The target response contract should expose the standard backend metadata whenever relevant:
- `ok`
- `data`
- `generated_at`
- `freshness` and/or `timestamp` and/or `last_update`
- `source[]`
- `warnings[]`
- `filters_applied`
- `stats`
- `fallback_used` when degraded logic is meaningful

### 6. Never-empty / degraded mode
- Product-facing endpoints should prefer never-empty degraded responses over breaking 500s on internal failures.
- Degradation must be explicit and machine-readable:
  - `source[]` includes fallback provenance
  - `warnings[]` explains the degraded state
  - `fallback_used` is exposed if useful
- Invalid client input can still return proper 4xx.

### 7. Cache / debug / fallback
- Expensive or aggregating endpoints should use deterministic cache keys and TTL from config/env.
- `debug=true` may bypass cache and expose traces when operationally justified.
- If the endpoint depends on fragile providers, fallback must preserve the public contract.

### 8. Test matrix
The target endpoint should have:
- route orchestration tests
- contract shape tests
- fallback/degraded tests
- metadata parity tests
- service-layer tests for non-trivial business logic

## Judge as the Reference Example
The current best reference is:
- route: [/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/judge.py](/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/judge.py)
- application pipeline: [/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_pipeline.py](/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_pipeline.py)
- typed builder: [/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_builder.py](/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_builder.py)
- endpoint service: [/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_endpoint_service.py](/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_endpoint_service.py)
- shared contract: [/Users/venom/Documents/analyse-financiere/packages/contracts/judge_v1.py](/Users/venom/Documents/analyse-financiere/packages/contracts/judge_v1.py)
- invariants: [/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/INVARIANTS.md](/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/INVARIANTS.md)

## What Makes Judge the Best Current Model
`judge` already combines most of the production-ready pieces that other endpoints are missing:
- shared typed contract
- route orchestration with cache and singleflight
- provider fallback chain
- strict payload parsing/validation
- explicit provenance
- reusable endpoint services
- decision journal / feedback / playbooks / quality-style projections

Invariants explicitly documented in `judge`:
- never-empty nominal path
- ranked provider selection with fallback chain
- contract aligned with `packages/contracts/judge_v1.py`
- cache keys include provider/model audit metadata

## What Other Endpoints Must Copy from Judge
Copy these patterns.

### Contract parity
- define or reuse a stable contract
- avoid route-local one-off shapes
- keep backward compatibility with aliases only when necessary

### Route thinness
- route is adapter/orchestrator only
- service/application layer owns real behavior

### Metadata parity
- always expose usable freshness/provenance/degraded signals
- frontend should not guess whether data is stale or fallback

### Never-empty parity
- preserve a usable `data` payload on internal failures when the endpoint is part of a core user flow

### Testing parity
- test contract first, then content
- prove degraded behavior and route delegation

## What Other Endpoints Must Not Copy from Judge
Do not blindly replicate these aspects.

### Do not clone the route monolith
- `judge.py` is the strongest route, but it is still large.
- New endpoints should reuse its patterns without repeating its size.
- Prefer smaller route files plus service/application extraction.

### Do not duplicate decision logic outside judge
- `copilot`, `portfolio`, `personal-finance`, and dashboard-oriented endpoints should consume `judge` or its services.
- They should not implement a second decision engine.

### Do not invent parallel contracts
- Reuse shared contracts or create a new shared contract in `packages/contracts/*`.
- Do not create a "judge-like" local shape that slowly drifts.

### Do not use weak judge-adjacent routes as the reference
These are useful files, but not the canonical model to clone:
- [/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/intelligence.py](/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/intelligence.py)
- [/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/quality.py](/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/quality.py)

They show compatibility or narrower route patterns, not the full target architecture.

## File-Level Guidance for Agents
Use these rules when changing backend endpoints.

### If you are changing business logic
Touch:
- `apps/api/src/domains/<domain>/application/*`

Do not start in:
- route files
- frontend adapters

### If you are changing the public payload
Start in:
- `packages/contracts/*`
- then update local schema aliases only if needed
- then update builder/service

### If you are adding a new product-facing endpoint
Prefer this structure:
- `apps/api/src/domains/<domain>/api/<endpoint>.py`
- `apps/api/src/domains/<domain>/application/<endpoint>_service.py`
- `packages/contracts/<contract>.py` if shared/public
- matching tests under `apps/api/src/domains/<domain>/tests/`

### If you are wiring a UI surface
- consume a service-backed endpoint
- do not move missing backend logic into the frontend
- show backend metadata (`source[]`, `warnings[]`, `freshness`) instead of hiding degraded states

## Judge-Parity Checklist
Before calling an endpoint "complete", answer yes to most of these:
- shared or stable contract exists
- route is thin
- business logic is in `application/*`
- reusable endpoint service exists
- metadata parity exists
- never-empty degraded mode exists
- fallback path preserves contract
- tests cover route delegation, contract, fallback, metadata

## Recommended Priority Order for Refactors
When upgrading an endpoint toward Judge-parity, use this order:
1. stabilize public contract
2. extract business logic out of route
3. add or tighten endpoint service layer
4. add metadata parity
5. add degraded mode / never-empty behavior
6. add cache/debug/fallback only if justified
7. add tests

## Good Agent Guidance
When another agent asks "what should I implement and where?", the answer should look like:
- contract file
- application/service files
- route file
- tests
- metadata/fallback expectations
- explicit non-goals

Never answer only "make it like judge". Answer which part of judge to copy, and which part not to copy.

## Non-Goals
- This doc does not claim that every endpoint needs the full complexity of `judge`.
- This doc does not make `judge` itself final or frozen.
- This doc does not require cache/singleflight/debug on trivial endpoints.
- This doc does not move product logic into monitor or frontend.
