# Architecture Blueprint - Forecast Board (Free Data, Multi-Layer)

Updated: 2026-03-02
Positioning: analysis and forecasting tool, no buy/sell execution workflows.
Execution mode: parallel batches, no hard dependencies between batches.

## 1) Current architecture diagnosis (from codebase)

## Strengths already in place

- Domain structure exists and is usable:
- `apps/api/src/domains/forecasts`
- `apps/api/src/domains/market_data`
- `apps/api/src/domains/judge`
- `apps/api/src/domains/copilot`
- Forecast route is orchestrator-only and delegates logic to service:
- `apps/api/src/domains/forecasts/api/forecasts.py`
- Forecast service already has cache, freshness, fallback, provider-chain metadata:
- `apps/api/src/domains/forecasts/application/forecasts_service.py`
- Ingestion building blocks already exist for macro/news/stocks/ownership:
- `apps/api/src/platform/legacy/jobs/macro_ingest.py`
- `apps/api/src/platform/legacy/jobs/news_ingest.py`
- `apps/api/src/platform/legacy/jobs/stocks_prices_refresh.py`
- `apps/api/src/platform/legacy/ingestion/financials_ownership_client.py`

## Friction points to address

- API entrypoint still overloaded and mixes many legacy/new paths:
- `apps/api/src/platform/main.py`
- Data ingestion implementation is split across legacy jobs with inconsistent contracts.
- Free-data source governance is not centralized (source, license, auth, rate-limit, fallback).
- Frontend connector still carries mock-era patterns and UI randomness:
- `apps/web/src/domains/forecasts/contracts/apiConnector.js`
- Market data adapter layer depends on mixed providers and implicit fallbacks:
- `apps/api/src/platform/legacy/core/market_data.py`

## Architecture conclusion

Keep current stack and codebase organization, but enforce:
- one canonical data contract per layer,
- one source registry with compliance metadata,
- one ingestion mesh with explicit freshness and provenance,
- one forecast fusion pipeline with per-layer attribution and uncertainty.

## 2) What to use (target stack)

## API and domain orchestration

- Keep `FastAPI` as single API edge.
- Keep domain routers and move route registration out of monolith progressively.
- Keep "never-empty + degraded mode explicit" behavior as contract rule.

## Data processing and storage

- Bronze layer (raw): append-only JSON/CSV pulls, source-native fields.
- Silver layer (normalized): Parquet partitioned by `source/date`.
- Gold layer (forecast-ready): Parquet tables for features, forecasts, attribution, quality metrics.
- Query engine: DuckDB for local analytical joins and feature views.
- Cache layer: existing JSON response cache for low-latency API responses.

## Scheduler and runtime

- Keep current cron runner approach (already in place).
- One collector job per source family with independent TTL and retry policy.
- Explicit cooldown and backoff for rate-limited sources.

## Forecast engine structure

- Stage 1: layer-specific scorers:
- macro
- geopolitical/conflict
- law/regulation
- insider behavior
- supply-chain/commodity shocks
- sector/company technical context
- Stage 2: fusion engine with weighted attribution by layer.
- Stage 3: uncertainty calibration and confidence interval output.
- Stage 4: narrative generation strictly grounded on attribution payload.

## 3) Free/public data source catalog (recommended)

## A) Macro and economic (country/continent/world)

- FRED API (macro US series, broad baseline).
- URL: `https://fred.stlouisfed.org/docs/api/fred/`
- Note: API key model documented.
- World Bank Indicators API v2 (country/global development indicators).
- URL: `https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation`
- ECB Data Portal API (rates/financial series, SDMX style).
- URL: `https://data.ecb.europa.eu/help/api/data`
- OECD API (SDMX, free with rate limits).
- URL: `https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html`
- IMF Data APIs (SDMX 2.1/3.0).
- URL: `https://data.imf.org/en/Resource-Pages/IMF-API`
- EIA API (energy datasets, free with key/rate controls).
- URL: `https://www.eia.gov/opendata/documentation.php`
- Eurostat API (EU statistical datasets).
- URL: `https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction`

## B) Geopolitics and conflict

- GDELT datasets/APIs (news-derived global events and GKG, frequent updates).
- URL: `https://www.gdeltproject.org/data.html`
- UCDP API (conflict events datasets, explicit paging and quotas).
- URL: `https://ucdp.uu.se/apidocs/index.html`
- ACLED API (conflict events, authenticated access model).
- URL: `https://acleddata.com/acled-api-documentation`

## C) Law and policy change

- Regulations.gov API (US federal regulatory workflow; api.data.gov key).
- URL: `https://open.gsa.gov/api/regulationsgov/`
- Congress.gov API (US legislative data; public API with key signup).
- URL: `https://www.congress.gov/help/using-data-offsite`
- GovInfo API (federal documents and metadata).
- URL: `https://www.govinfo.gov/features/api`
- EU Publications SPARQL endpoint (EU legal/publication metadata access).
- URL: `https://publications.europa.eu/webapi/rdf/sparql`

## D) Company, insider, ownership

- SEC EDGAR APIs (`data.sec.gov`) for submissions and XBRL company facts.
- URL: `https://www.sec.gov/edgar/sec-api-documentation`
- Existing in-repo insider/13F parser baseline:
- `apps/api/src/platform/legacy/ingestion/financials_ownership_client.py`

## E) Market prices and broad market context

- Existing code supports:
- Stooq CSV fallback
- Yahoo chart fallback
- optional Finnhub key path
- Source logic currently in:
- `apps/api/src/platform/legacy/jobs/stocks_prices_refresh.py`
- `apps/api/src/platform/legacy/core/market_data.py`

## Source governance rule

Every source must declare:
- `source_id`
- `layer`
- `free_tier_status`
- `auth_mode`
- `license_or_terms_url`
- `rate_limit_notes`
- `freshness_expected`
- `fallback_source_ids`

No source enters nominal runtime without this metadata.

Reference matrix:
- `docs/product/planning/FREE_DATA_SOURCE_KEY_MATRIX.md`

## 4) Canonical contracts to implement

## 4.1 Raw ingest contract (`raw_event`)

- `source_id`
- `ingested_at`
- `event_time`
- `payload_raw`
- `provenance_url`
- `license_tag`

## 4.2 Normalized signal contract (`normalized_signal`)

- `signal_id`
- `layer` (macro/geopolitical/policy/insider/supply_chain/sector/company)
- `entity_type` (company/sector/country/continent/world)
- `entity_id`
- `horizon` (1d/1w/1m)
- `direction`
- `score`
- `confidence`
- `uncertainty_class`
- `source_ids`
- `generated_at`
- `freshness_status`

## 4.3 Fused forecast contract (`fused_forecast`)

- `forecast_id`
- `entity_id`
- `horizon`
- `direction`
- `confidence`
- `p10`
- `p50`
- `p90`
- `layer_attribution` (weights by layer)
- `top_positive_drivers`
- `top_negative_drivers`
- `provenance_bundle`
- `degraded_mode`

## 5) Detailed task pack (parallel, no dependency)

## Lane L1 - Source governance and ingestion foundation

- `ARCH-L1-01` (`data_analyst`) Build `source_registry` for all selected free sources.
- Done: registry contains auth/terms/rate/freshness/fallback for each source.
- `ARCH-L1-02` (`backend_engineer`) Implement registry loader and validation.
- Done: runtime fails fast on invalid source metadata.
- `ARCH-L1-03` (`infra_engineer`) Standard collector template (retry, cooldown, jitter, timeout).
- Done: template used by macro/news/law/geopolitics collectors.
- `ARCH-L1-04` (`backend_engineer`) Normalize raw ingest to `raw_event` contract.
- Done: at least 5 source families produce valid `raw_event`.
- `ARCH-L1-05` (`qa`) Add schema checks for `raw_event`.
- Done: contract pass rate 100 percent.
- `ARCH-L1-06` (`planner`) Publish free-data compliance gate.
- Done: any non-compliant source blocks nominal path.

## Lane L2 - Layer-specific signal builders

- `ARCH-L2-01` (`data_analyst`) Macro signal builder (country/continent/world).
- `ARCH-L2-02` (`data_analyst`) Geopolitical/conflict signal builder.
- `ARCH-L2-03` (`data_analyst`) Law/regulation impact signal builder.
- `ARCH-L2-04` (`data_analyst`) Insider behavior signal builder.
- `ARCH-L2-05` (`data_analyst`) Supply-chain/commodity shock signal builder.
- `ARCH-L2-06` (`backend_engineer`) Standardize all outputs to `normalized_signal`.
- Done criteria for L2:
- all 6 signal builders output valid normalized contract,
- confidence and freshness fields present,
- provenance non-empty.

## Lane L3 - Fusion, calibration, and uncertainty

- `ARCH-L3-01` (`backend_engineer`) Implement fusion core combining all layers.
- `ARCH-L3-02` (`data_analyst`) Define and calibrate layer weights per horizon.
- `ARCH-L3-03` (`data_analyst`) Add calibration dashboard metrics (Brier-like, reliability bins).
- `ARCH-L3-04` (`backend_engineer`) Add uncertainty intervals (`p10/p50/p90`) to forecasts.
- `ARCH-L3-05` (`qa`) Perturbation stability tests for attribution.
- `ARCH-L3-06` (`planner`) Define confidence downgrade rules under missing/stale layers.
- Done criteria for L3:
- fused contract valid on all core entities,
- interval coverage report produced,
- degraded behavior explicit and tested.

## Lane L4 - API and UI forecast board

- `ARCH-L4-01` (`backend_engineer`) Add endpoints for hierarchical forecasts:
- `/api/forecast/world`
- `/api/forecast/continent/{id}`
- `/api/forecast/country/{id}`
- `/api/forecast/sector/{id}`
- `/api/forecast/company/{ticker}`
- `ARCH-L4-02` (`backend_engineer`) Add endpoint for attribution and provenance bundle.
- `ARCH-L4-03` (`frontend_engineer`) Build multi-layer board view with drilldown in <=3 clicks.
- `ARCH-L4-04` (`frontend_engineer`) Build uncertainty and attribution panels.
- `ARCH-L4-05` (`frontend_engineer`) Add policy/law/geopolitical timeline cards.
- `ARCH-L4-06` (`qa`) Browser proof for nominal and degraded flows.
- Done criteria for L4:
- one path from world signal to company forecast evidence in <=3 clicks,
- no mock in nominal path,
- source/provenance visible from UI.

## Lane L5 - Ops, QA, and release governance

- `ARCH-L5-01` (`infra_engineer`) Ingestion mesh health endpoint with per-source status.
- `ARCH-L5-02` (`infra_engineer`) SLA checks on freshness and collector success rate.
- `ARCH-L5-03` (`qa`) End-to-end suite by layer and horizon.
- `ARCH-L5-04` (`data_analyst`) Quality trend report per layer (weekly rolling).
- `ARCH-L5-05` (`planner`) Forecast-only release gate (no trade execution behaviors).
- `ARCH-L5-06` (`planner`) Parallel dispatch governance by lane and wave.
- Done criteria for L5:
- all P0 quality gates pass,
- no blocker on provenance, uncertainty, or free-data compliance.

## 6) First implementation cut (fast path for dev)

## Sprint slice S1 (high leverage)

- Build source registry and validation (`ARCH-L1-01/02`).
- Ship geopolitical + policy + insider normalized signals (`ARCH-L2-02/03/04`).
- Ship fusion v1 with attribution payload (`ARCH-L3-01/02`).
- Expose world->company drilldown API (`ARCH-L4-01/02`).

## Sprint slice S2

- Uncertainty intervals and calibration metrics (`ARCH-L3-03/04`).
- Layered UI with attribution and timeline cards (`ARCH-L4-03/04/05`).
- SLA + E2E + release gate hardening (`ARCH-L5-*`).

## 7) Explicit non-goals

- No brokerage integration.
- No order execution.
- No auto-trading.
- No buy/sell action automation.

The product remains a forecast and analysis board with multi-layer impact reasoning.
