---
status: working
last_verified: 2026-03-10
---

# Current Execution Focus - 2026-03-10

Superseded on 2026-03-12 by [CURRENT_EXECUTION_FOCUS_2026-03-12.md](/home/venom/analyse-financiere/docs/product/planning/CURRENT_EXECUTION_FOCUS_2026-03-12.md).

This file remains the decision snapshot that introduced the `VB-*` bridge for product clarification. It is no longer the active dispatch document.

## Purpose
Turn the existing codebase into a product-aligned execution plan for the next planner cycle.

Planner posture for this cycle:
- maintain planner as the active periodic orchestrator
- use worker subagents as the primary execution path
- launch planner subagents in worker mode, not explorer mode
- update spec/doc/orchestration blockers immediately when they slow delivery
- prefer independent delivery slices and parallel workers where ownership is disjoint
- delegate unblock/doc/batch-maintenance work to `scrum_master` when that preserves planner focus on sequencing and final decisions
- delegate runtime/infra/monitoring recovery work to `admin` when stale or down operational state blocks delivery
- target 2-3 parallel `dev` workers by default, with a hard cap of 4 concurrent `dev` workers
- keep batches independent and prefer one `dev` worker per active batch when safe
- record planner actions and delivery state changes in memory for continuity

Canonical references:
- [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md)
- [BACKEND_FIRST_PRODUCT_BACKLOG.md](/home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md)
- [PLANNER_ORCHESTRATOR_TARGET_SPEC.md](/home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md)
- [CURRENT_ARCHITECTURE_ENTRYPOINTS.md](/home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md)

## Repo truth observed
### Product-facing surfaces already present
- Backend entrypoint remains thin and delegates to the current platform app factory:
  - [app_factory.py](/home/venom/analyse-financiere/apps/api/src/platform/app_factory.py)
- Brief surface exists:
  - [brief.py](/home/venom/analyse-financiere/apps/api/src/domains/forecasts/api/brief.py)
- Copilot entry surfaces exist:
  - [copilot.py](/home/venom/analyse-financiere/apps/api/src/domains/copilot/api/copilot.py)
  - [copilot_service.py](/home/venom/analyse-financiere/apps/api/src/domains/copilot/application/copilot_service.py)
- Frontend connector for live API already exists:
  - [apiConnector.js](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/contracts/apiConnector.js)
- The protected UI shell and theme are still the active frontend surface:
  - [index.html](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/pages/index.html)
  - [INVARIANTS.md](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/INVARIANTS.md)

### Architectural reality
- The monorepo is already split into `apps/api`, `apps/web`, `apps/monitor`, `packages`, and `platform`.
- The backend contains active domain folders (`copilot`, `forecasts`, `judge`, `market_data`) but still carries a very large `platform/legacy` surface.
- The frontend is not a fresh greenfield app: it is an existing static shell with many widgets and protected visual invariants.
- Planning docs under `docs/product/scrum` are historical; active planning truth is under `docs/product/planning`.

## Main planner diagnosis
### 1. The product direction is clear, but the active contracts are still fallback-first
Observed in:
- [brief.py](/home/venom/analyse-financiere/apps/api/src/domains/forecasts/api/brief.py)
- [copilot.py](/home/venom/analyse-financiere/apps/api/src/domains/copilot/api/copilot.py)
- [copilot_service.py](/home/venom/analyse-financiere/apps/api/src/domains/copilot/application/copilot_service.py)

Current behavior is designed to stay non-empty and resilient, which is useful, but it still reads as a service-hardening layer more than a decision-ready product contract.

Impact:
- good degraded behavior
- unclear guarantee of the canonical product fields required by the vision:
  - regime
  - top opportunities
  - explicit risks
  - explainable memo structure
  - freshness/source semantics consistent across brief and ask

### 2. The frontend already knows how to call the API, but the shell still contains hardcoded product copy and placeholder posture
Observed in:
- [index.html](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/pages/index.html)
- [apiConnector.js](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/contracts/apiConnector.js)

Impact:
- the app shape is present
- the product promise is not yet fully backed by live backend truth on open
- planner should resist a redesign and instead drive contract wiring

### 3. The codebase is rich enough that scope drift is a bigger risk than missing foundations
Observed in:
- backend domain breadth
- legacy tree size
- orchestration/runtime docs and modules already in place

Impact:
- adding new endpoints by reflex is the wrong move
- planner should prefer contract normalization on existing routes
- planner should keep product work close to:
  - `/api/brief/daily`
  - `/api/copilot/start`
  - `/api/copilot/context`
  - `/api/copilot/ask`
  - existing forecasts/news/dashboard consumers

## Recommended execution order
### Slice A - Decision-ready brief normalization
Priority:
- P0

Goal:
- make the homepage brief usable from backend truth alone

Primary files:
- [brief.py](/home/venom/analyse-financiere/apps/api/src/domains/forecasts/api/brief.py)
- [test_brief_route_contract.py](/home/venom/analyse-financiere/apps/api/src/domains/forecasts/tests/test_brief_route_contract.py)
- [test_brief_of_day_feature.py](/home/venom/analyse-financiere/apps/api/src/domains/copilot/tests/test_brief_of_day_feature.py)

Contract target:
- keep current compatibility fields
- guarantee normalized product fields or aliases for:
  - summary
  - market regime/sentiment
  - top opportunities/signals
  - top risks
  - freshness
  - sources

Why first:
- it maps directly to Priority 0 in the canonical backlog
- it upgrades the first screen without a theme rewrite
- it reduces mock dependence across homepage and copilot start

### Slice B - Deep-dive memo normalization on existing ask path
Priority:
- P0

Goal:
- ensure `/api/copilot/ask` returns a deterministic memo object, not only a generic answer payload

Primary files:
- [copilot.py](/home/venom/analyse-financiere/apps/api/src/domains/copilot/api/copilot.py)
- [copilot_service.py](/home/venom/analyse-financiere/apps/api/src/domains/copilot/application/copilot_service.py)

Contract target:
- structured memo with:
  - verdict
  - horizon
  - why
  - risks
  - confidence
  - freshness
  - sources
- keep legacy answer compatibility if still required by current UI

Why second:
- it completes the brief + ask rhythm defined in the product vision
- it is a backend-first improvement with direct product payoff

### Slice C - Minimal frontend adaptation to live truth
Priority:
- P1 after A and B contracts are locked

Goal:
- wire the current hero and copilot entry points to backend truth with minimal structural changes

Primary files:
- [apiConnector.js](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/contracts/apiConnector.js)
- [index.html](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/pages/index.html)

Rule:
- no shell redesign
- no token or palette rewrite
- only mapping, badges, degraded states, and memo rendering blocks

## Explicit non-goals for this cycle
- no frontend redesign
- no new parallel planning source outside `docs/product/planning`
- no new endpoint family if existing routes can be extended
- no legacy-path expansion under `platform/legacy`
- no orchestration-only work inflation while product P0 remains partially delivered

## Definition of done for the next planner pass
- brief contract fields are normalized and explainable
- ask contract exposes a structured memo
- frontend can display backend truth with minor adaptations only
- proof path is defined for API, degraded mode, and browser/UI rendering

## Immediate next move
Start with Slice A.

Reason:
- it is the shortest path from current code to visible product value
- it preserves the protected frontend
- it creates the canonical payload that both homepage and copilot flows can reuse
