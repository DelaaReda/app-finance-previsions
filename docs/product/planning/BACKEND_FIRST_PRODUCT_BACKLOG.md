---
status: canonical
last_verified: 2026-03-07
---

# Backend-First Product Backlog

## Purpose
Translate the current product vision into a delivery backlog that improves the product through backend contract evolution first, while preserving the existing frontend theme and shell.

Canonical inputs:
- [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md)
- [PLANNER_ORCHESTRATOR_TARGET_SPEC.md](/home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md)

## Locked product rules
- The product is a **deep-dive assistant**, not a passive dashboard.
- The default journey is **brief + ask**.
- The standard answer shape is an **investment memo**.
- Watchlist and portfolio context improve the answer but are not required for usefulness.
- Backend contract evolution is preferred over frontend redesign.
- The existing frontend theme, tokens, palette, and shell are protected.

## Protected frontend surfaces
Do not redesign these by default:
- [design-tokens.css](/home/venom/analyse-financiere/apps/web/src/platform/design-tokens.css)
- [style.css](/home/venom/analyse-financiere/apps/web/src/platform/style.css)
- [index.html](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/pages/index.html)

Frontend invariants already in repo:
- [INVARIANTS.md](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/INVARIANTS.md)
- [OWNERS.yaml](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/OWNERS.yaml)
- live connector contract: [apiConnector.js](/home/venom/analyse-financiere/apps/web/src/domains/forecasts/contracts/apiConnector.js)

Allowed frontend changes:
- wire existing components to richer backend payloads
- add loading, degraded, stale, and empty states
- add memo rendering blocks inside existing shells
- adjust text, labels, and field mapping

Disallowed by default:
- redesigning navigation or shell layout
- changing design tokens or palette to compensate for weak backend output
- moving business logic from backend into frontend widgets

## Priority 0 — Decision-ready brief
Goal:
- make the app useful on open, before any deep dive starts

Backend surfaces to evolve first:
- `/api/brief/daily`
- `/api/dashboard/kpis`
- `/api/news/feed`
- `/api/forecasts`

Required contract outcome:
- daily brief returns:
  - market regime
  - top opportunities
  - top risks
  - freshness
  - sources
- KPI/forecast/news payloads expose enough metadata for the brief to be explainable and degradable

Acceptance:
- the homepage can show a usable daily brief without inventing frontend-only logic
- degraded data is explicit
- the brief can be consumed in the current shell with minor rendering changes only

## Priority 1 — Deep-dive memo contract
Goal:
- answer a ticker/theme/question with a structured recommendation instead of a vague assistant response

Backend surfaces to evolve:
- `/api/copilot/ask`
- `/api/search/universal`
- `/api/forecasts`
- `/api/recommendations/daily`

Preferred rule:
- extend existing endpoints before introducing any new endpoint

Required memo contract:
- `verdict`
- `horizon`
- `why`
- `risks`
- `confidence`
- `freshness`
- `sources`
- optional `next_steps` or `invalidation`

Compatibility rule:
- keep any legacy `answer` field if needed, but backend should also return a structured memo object that frontend can render deterministically

Acceptance:
- a deep-dive request can be rendered from backend fields alone
- frontend does not need to reconstruct the recommendation from raw fragments
- memo output stays compatible with current theme and widget structure

## Priority 2 — Portfolio and watchlist context
Goal:
- make recommendations personal without making the product unusable when portfolio data is absent

Backend surfaces to evolve:
- `/api/copilot/context`
- `/api/portfolios`
- `/api/portfolios/{portfolio_id}`
- `/api/portfolios/{portfolio_id}/performance`

Required behavior:
- portfolio/watchlist context is optional input into brief and memo generation
- backend should explain when portfolio context changed the recommendation
- absence of saved context must fall back cleanly to market-wide reasoning

Acceptance:
- the same question can be answered with or without portfolio context
- the difference is explicit, not implicit
- current frontend can surface this with minor additions only

## Priority 3 — Forecast-first contract hardening
Goal:
- make forecasts decision-grade, not just data-grade

Backend surfaces to evolve:
- `/api/forecasts`
- any downstream consumer that turns forecasts into dashboard or memo output

Required forecast fields:
- `direction` or `action`
- `confidence`
- `horizon`
- `why`
- `risk_flag`
- `generated_at`
- `freshness_status`

Required rule:
- nominal mode must use real current data/model-backed logic
- degraded/fallback mode must be explicit

Acceptance:
- forecasts can feed both the brief and the memo contract directly
- frontend nominal mode never depends on mock reconstruction
- forecast payloads remain explainable and freshness-aware

## Priority 4 — Minimal frontend adaptation backlog
Goal:
- connect the product value without touching the theme architecture

Frontend scope allowed after backend contracts are stable:
- map brief payload to existing homepage surfaces
- map memo payload into current deep-dive/search flows
- show degraded/freshness/source badges
- preserve `forecast_card_always_visible` and `degraded_badge_visible`

Frontend scope not allowed in this backlog:
- redesign of the hero shell
- new design system
- major component reshuffle
- replacing the forecasts domain page architecture

Acceptance:
- current components display backend truth with minimal structural edits
- no nominal mock path remains
- theme continuity is preserved visually

## Priority 5 — Proof and release discipline
Goal:
- block fake product progress

Required proof path for each shipped product slice:
- backend contract proof
- browser/UI proof in current theme
- degraded-mode proof
- freshness/source proof

Canonical validation assets:
- [FORECAST_PIPELINE_PROOF_RUNBOOK.md](/home/venom/analyse-financiere/docs/ops/FORECAST_PIPELINE_PROOF_RUNBOOK.md)
- browser smoke helper in `platform/automation/browser_smoke.py`

Acceptance:
- a product slice is not done if it only works in API isolation
- a product slice is not done if the UI proof required a theme-breaking workaround

## Delivery order
1. Decision-ready brief
2. Deep-dive memo contract
3. Portfolio/watchlist context
4. Forecast-first contract hardening
5. Minimal frontend adaptation
6. Proof and release gate

## Merged legacy batch map
The older batch packs remain useful as detailed archives, but they are now merged into this canonical backlog.

### Stream A — Core decision foundation
Merged from:
- `BATCH-11` to `BATCH-14`

What survives:
- ingestion health and freshness
- portfolio state and risk profile core
- decision journal and outcome loop
- robustness drills and final go/no-go discipline

Backend-first interpretation:
- stabilize ingestion, freshness, portfolio context, and journaling contracts first
- only add minimal UI surfaces needed to expose those contracts inside the existing shell

### Stream B — Decision intelligence expansion
Merged from:
- `BATCH-15` to `BATCH-19`

What survives:
- strategy playbooks
- scenarios and stress tests
- regime and drift detection
- event-aware recommendations
- explainability graph and source traceability

Backend-first interpretation:
- add these as memo and brief enrichments first
- only expose lightweight selectors, badges, and trace panels in the current UI

### Stream C — Personal risk and execution discipline
Merged from:
- `BATCH-20` to `BATCH-23`

What survives:
- personal policy guardrails
- paper trading and execution journal
- rebalance optimization
- fees, taxes, and slippage awareness

Backend-first interpretation:
- build policy and execution contracts first
- keep frontend additions limited to panels/cards inside current portfolio and copilot surfaces

### Stream D — Routine automation and reliability
Merged from:
- `BATCH-24` to `BATCH-28`

What survives:
- alerting intelligence
- autonomous morning brief pipeline
- weekly investment committee mode
- reliability drills
- final release/adoption gate

Backend-first interpretation:
- deliver jobs, storage, telemetry, and gate logic first
- only then wire brief/alerts/committee views into the current theme

### Stream E — Forecast research and model governance
Merged from:
- `BATCH-29` to `BATCH-40`

What survives:
- forecast calibration
- multi-horizon decomposition
- correlation/regime mapping
- ensemble governance
- uncertainty and provenance
- predictive research gate

Backend-first interpretation:
- treat these as forecast contract and quality-layer work first
- expose only compact visual affordances that fit the current forecasts shell

### Stream F — Global multi-layer intelligence
Merged from:
- `BATCH-41` to `BATCH-50`

What survives:
- geopolitical and policy impact layers
- insider/supply chain/global regime layers
- event horizon matrices
- multi-layer attribution and global forecast gate

Backend-first interpretation:
- these are advanced analytical layers that must not force a UI rewrite
- they enter the product as deeper memo/context enrichments before any major visual expansion

## Legacy batch packs status
These older specs are now detailed historical references, not competing backlog sources:
- `BATCHES_11_14_EXEC_SPEC.md`
- `BATCHES_15_28_EXEC_SPEC.md`
- `BATCHES_29_40_FORECAST_EXEC_SPEC.md`
- `BATCHES_41_50_GLOBAL_FORECAST_SPEC.md`

## Out of scope for this backlog
- full frontend redesign
- theme rewrite
- a new multi-page UX architecture
- lane-based product planning that assumes autonomous frontend/backend agents
- moving core product reasoning into frontend code
