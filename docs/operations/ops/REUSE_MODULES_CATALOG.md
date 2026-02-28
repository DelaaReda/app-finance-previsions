# Module Reuse Catalog (Avoid Rebuilding What Exists)

Note d’alignement chemin: ce document contient des références historiques `copilot-app/...`.
Le chemin actif est `apps/api/src` (backend) et `apps/web/src` (frontend).  
Les entrées historiques sont encore utiles pour retrouver les modules, en remplaçant:
- `copilot-app/backend` → `apps/api`
- `copilot-app/frontend` → `apps/web`

Objectif: aider l’equipe a **reutiliser** les modules deja presents (helpers, services, schemas, widgets) au lieu de recreer des variantes.

Checklist (reuse-first marker):
- `docs/ops/INTEGRATION_APP_ENGINEER_RECOMMENDATIONS.md`

## Index des gros modules (>=400 lignes)

Pour rendre la reutilisation visible rapidement (sans chercher fichier par fichier), utiliser:

- Index auto-genere: `docs/ops/LARGE_MODULE_REUSE_INDEX.md`
- Generateur: `scripts/generate_large_module_reuse_index.py`

Commande de regeneration:

```bash
python3 scripts/generate_large_module_reuse_index.py
```

Regle: avant de creer un nouveau module "large", verifier d'abord cet index et etendre un module existant si possible.

## Facades de reutilisation (imports stables)

Pour simplifier le dev des agents moins experimentes, utiliser en premier:

- `copilot-app/backend/src/reuse/llm.py`
- `copilot-app/backend/src/reuse/forecasting.py`
- `copilot-app/backend/src/reuse/judge.py`
- `copilot-app/backend/src/reuse/data.py`

Ces facades exposent les points d'entree canoniques (LLM, previsions, template judge, data quality) avec imports stables.

Règle: avant d'ajouter un nouveau fichier, faire:

```bash
rg -n "<mot-cle>" copilot-app/backend/src copilot-app/backend/services copilot-app/backend/storage copilot-app/backend/models copilot-app/backend/jobs copilot-app/frontend/app
```

## Canonical Reference: Judge API Stack

Le squelette "endpoint robuste" de reference est `/api/judge` (cache + debug + validation + fallback multi-provider + contrat typé).

Modules canon a reutiliser:
- Template utilitaires Judge-like (cache/single-flight/source tags): `copilot-app/backend/src/api/templates/judge_like_endpoint.py`
- Standard de services reutilisables (timestamps, casts, unwrap `data/payload`, envelope, source tags): `copilot-app/backend/src/services/service_standard.py`
- Route: `copilot-app/backend/src/api/routes/judge.py`
- Route d'exemple template applique (non-LLM): `copilot-app/backend/src/api/routes/forecasts.py`
- Pipeline + validation/parsing: `copilot-app/backend/src/services/judge_pipeline.py`
- Verdict typé (schema canon): `copilot-app/backend/src/services/judge_builder.py` + `copilot-app/backend/src/schemas/judge.py`
- LLM fallbacks:
  - entrypoint canonique: `copilot-app/backend/src/services/g4f_client.py::call_llm`
  - g4f low-level (interne): `copilot-app/backend/src/services/g4f_client.py::call_g4f`
  - Codestral: `copilot-app/backend/src/services/codestral_client.py`
  - Groq (fallback + JSON repair): `copilot-app/backend/src/services/groq_client.py`
- Provider working list (g4f): `copilot-app/backend/src/agents/g4f_model_watcher.py`
- LLM primary agent (OpenRouter/free providers): `copilot-app/backend/src/analytics/econ_llm_agent.py`
- ML prior (optionnel, utilisé par Judge): `copilot-app/backend/src/analytics/ml_baseline.py`
- Phase blocks adapter (optionnel, utilisé par Judge): `copilot-app/backend/src/analytics/phases_adapter.py`
- Context pack builder (optionnel, complet): `copilot-app/backend/src/analytics/market_intel.py`
- Quality/metrics: `copilot-app/backend/src/services/judge_quality.py` + `copilot-app/backend/src/services/judge_quality_tracking.py`

## Backend Building Blocks (Reutilisation Prioritaire)

### Response envelope + erreurs
- Envelope standard: `copilot-app/backend/src/core/response.py` (`ok`, `err`).
- Gestion d'erreur structurée (utile pour never-empty): `copilot-app/backend/src/core/error_handler.py`.

### Storage snapshots (JSON) + resolution de paths
Le projet contient **plusieurs** couches; reutiliser plutot que re-implémenter:
- Storage "secure key -> JSON": `copilot-app/backend/storage/io.py` (`load_json`, `save_json`, sanitization, path traversal guard).
- Storage legacy (filename-based): `copilot-app/backend/storage/base.py` (utilise `data/*.json`).
- Adapter de lecture unique (evite `load_json("x") or load_json("x.json")`): `copilot-app/backend/src/services/snapshot_loader.py`.
- TTL/freshness helpers: `copilot-app/backend/storage/ttl.py`.
- Resolver de repertoire data/logs (robuste uvicorn/cwd): `copilot-app/backend/src/core/path_resolver.py`.

Recommandation d'usage:
- Lecture endpoint: **preferer** `src/services/snapshot_loader.load_snapshot(...)` avec `aliases=[...]`.
- Ecriture job/snapshot: **preferer** `storage/io.save_json(key, payload, source=[...])`.

### Footguns d'import (a eviter)
Il existe des doublons historiques:
- `copilot-app/backend/src/services/*` **et** `copilot-app/backend/services/*`
- `copilot-app/backend/src/storage/*` (quasi vide) **et** `copilot-app/backend/storage/*` (effectif)

Le runtime FastAPI (`copilot-app/backend/src/api/main.py`) force `backend/src` en tete de `sys.path`, donc:
- les imports `core.*` et `services.*` pointent **d'abord** vers `copilot-app/backend/src/*`,
- puis retombent sur `copilot-app/backend/*` uniquement en fallback.

Conseil:
- pour du nouveau code backend: preferer les modules `copilot-app/backend/src/...` et reutiliser `storage/io.py` via `snapshot_loader` (adapter) pour la lecture.
- ne pas creer un "troisieme" emplacement de service; si un module manque, l'ajouter dans la couche canon (souvent `src/core` ou `src/services`).

### Cache (memoire + persistent)
Selon besoin:
- Cache memoire simple TTL: `copilot-app/backend/src/core/cache.py` (`TTLCache`, decorateur `ttl_cache`).
- Cache memoire LRU + invalidation par mtime fichiers: `copilot-app/backend/src/core/memory_cache.py`.
- Cache persistent load-or-compute (via storage): `copilot-app/backend/services/cache_layer.py` (`CacheLayerService.load_or_compute`).
- Cache per-route (helpers deja en place): `copilot-app/backend/src/api/main.py` (`_response_cache_key/_get/_set`, `_downsample_points`).

### Normalisation tickers + shaping time series
- Normalisation tickers canonique: `copilot-app/backend/src/core/ticker_normalization.py`.
- Downsampling UI: `copilot-app/backend/src/core/downsample.py` (LTTB).
- Acces marche (prices/fundamentals/FRED): `copilot-app/backend/src/core/market_data.py`.

### Forecast engine / analytics (modules "complets" deja presents)
Avant de créer un nouveau moteur, vérifier ces briques:
- Modèle hybrid v1 (offline-friendly, utilisé par jobs/services): `copilot-app/backend/models/forecast_hybrid_v1.py`
- Job de génération forecasts: `copilot-app/backend/jobs/forecasts.py`
- Forecaster baseline (SMA + sentiment blend): `copilot-app/backend/src/analytics/forecaster.py`
- ML prior léger (utilisé par Judge): `copilot-app/backend/src/analytics/ml_baseline.py`
- Phase 1 (fondamental/DCF): `copilot-app/backend/src/analytics/phase1_fundamental.py` (dépendances yfinance)
- Phase 2 (technical/backtests): `copilot-app/backend/src/analytics/phase2_technical.py` (dépendances ta)
- Phase 3 (macro bundle + régimes): `copilot-app/backend/src/analytics/phase3_macro.py`
- Phase 4 (sentiment/news NLP): `copilot-app/backend/src/analytics/phase4_sentiment.py` (VADER/HF optionnels)
- Phase 5 (fusion scoring): `copilot-app/backend/src/analytics/phase5_fusion.py` (attention: imports "script-style" à normaliser si wiring API)
- Adapter lightweight des phases (déjà utilisé par `/api/judge`): `copilot-app/backend/src/analytics/phases_adapter.py`
- Orchestrateur "market intel" (news + ownership + macro derivs, compatible econ_llm_agent): `copilot-app/backend/src/analytics/market_intel.py`

### News lakehouse pipeline (bronze/silver/gold) + taxonomy
Pipeline ingestion déjà présent (éviter de recréer des schemas et dedupe):
- Schemas dataclass: `copilot-app/backend/src/ingestion/news_schemas.py`
- Bronze ingestion (RSS + canonical URL): `copilot-app/backend/src/ingestion/bronze_pipeline.py`
- Silver transform (clean text + tickers + secteurs/events + sentiment): `copilot-app/backend/src/ingestion/silver_pipeline.py`
- Gold features (daily par ticker): `copilot-app/backend/src/ingestion/gold_features_pipeline.py`
- Taxonomy/lexiques (pure python, fast): `copilot-app/backend/src/taxonomy/news_taxonomy.py`
- Pipelines news additionnels: `copilot-app/backend/src/pipelines/news/*` (extract events, to_silver, features v2)

### News (monolithic finnews) + NLP enrichment (si besoin rapide)
Modules existants, déjà "end-to-end":
- RSS multi-régions + enrich + search + features: `copilot-app/backend/src/ingestion/finnews.py`
- NLP enrich (summarize/sentiment/entities, zero deps): `copilot-app/backend/src/research/nlp_enrich.py`
- Impact analysis endpoint: `copilot-app/backend/src/api/routes/news_impact.py`
- Backtest news→prices (event study): `copilot-app/backend/src/analytics/backtest_news_impact.py`

### Ownership + macro/derivatives clients (snapshots riches)
- Fundamentals/insiders/13F/options (Yahoo + SEC EDGAR): `copilot-app/backend/src/ingestion/financials_ownership_client.py`
- Macro + dérivés (FRED/TE/CBOE/CFTC + cache): `copilot-app/backend/src/ingestion/macro_derivatives_client.py`
- Finviz (company snapshot/options/futures): `copilot-app/backend/src/ingestion/finviz_client.py`

### Shared data access helpers (eviter duplication)
Utile quand vous manipulez des `DataFrame`/Parquet, backtests, pipelines:
- Helpers de chargement déjà factorisés: `copilot-app/backend/src/core/data_access.py`
- Loader générique (json/csv/parquet + "latest"): `copilot-app/backend/src/core/data_loader.py`
- Parquet + DuckDB helpers: `copilot-app/backend/src/core/data_store.py`
- JSONL/cache/artifacts helpers (utilisé par backtests): `copilot-app/backend/src/core/io_utils.py`
- Stock/ticker heuristics: `copilot-app/backend/src/core/stock_utils.py`

### Quality gates / audits data
- Audit qualite snapshots (presence, volume minimal, timestamps): `copilot-app/backend/src/core/data_quality.py`.
- Quality judge (calibration/hit-rate) exploite forecasts + prices: `copilot-app/backend/src/services/judge_quality.py`.

## Backend Domain Services (Deja Present)

### UI data assembly (backend -> widgets)
Services "pure Python" reutilisables (pas de FastAPI import):
- Dashboard helpers: `copilot-app/backend/src/api/services/dashboard_ui_service.py`
- Macro facade: `copilot-app/backend/src/api/services/macro_service.py`
- News facade: `copilot-app/backend/src/api/services/news_service.py` (attention: imports dynamiques; preferer refactor vers `snapshot_loader` si possible)
- Forecast facade: `copilot-app/backend/src/api/services/forecast_service.py` (attention: imports legacy; preferer refactor vers modules `src/*`)
- Composite scoring (40/40/20, phase2/phase3 + finnews): `copilot-app/backend/src/api/services/scoring_service.py`

### Portfolio / Watchlists
Endpoints re-utilisent des services legacy via import dynamique:
- Routes: `copilot-app/backend/src/api/routes/portfolios.py`
- Services legacy: `copilot-app/backend/services/portfolio_service.py`, `copilot-app/backend/services/portfolio_performance_service.py`

### Alerts
- Routes: `copilot-app/backend/src/api/routes/alerts.py`
- Rules + services: `copilot-app/backend/src/services/alert_rules.py` et/ou `copilot-app/backend/services/alert_rules.py`

### Ask / RAG (Copilot)
- RAG store: `copilot-app/backend/src/research/rag_store.py`
- LLM client (OpenAI -> g4f -> fallback): `copilot-app/backend/src/research/llm_client.py`
- Web/nav helpers: `copilot-app/backend/src/research/web_navigator.py`
- Peers finder (Finnhub + yfinance): `copilot-app/backend/src/research/peers_finder.py`
- Routes: `copilot-app/backend/src/api/routes/copilot.py`

### Quality / monitoring / backtests / search (déjà présents)
- Quality monitor (runtime probes): `copilot-app/backend/src/quality/monitor.py` + `copilot-app/backend/src/api/routes/quality.py`
- Backtests routes/agent: `copilot-app/backend/src/api/routes/backtests.py` + `copilot-app/backend/src/agents/backtest_agent.py`
- Search endpoints: `copilot-app/backend/src/api/routes/search.py`, `copilot-app/backend/src/api/routes/universal_search.py`
- News impact analysis: `copilot-app/backend/src/api/routes/news_impact.py` + `copilot-app/backend/src/analytics/backtest_news_impact.py`

## Frontend Reuse (Widgets + Utils)

Widgets existants (a brancher sur APIs reelles avant d'en creer de nouveaux):
- `copilot-app/frontend/app/components/widgets/llm-judge.html`
- `copilot-app/frontend/app/components/widgets/forecast-scenarios.html`
- `copilot-app/frontend/app/components/widgets/news-feed.html`
- `copilot-app/frontend/app/components/widgets/kpi-cards-pro.html`
- `copilot-app/frontend/app/components/widgets/market-drivers.html`

Loaders/utilitaires:
- Chargement HTML: `copilot-app/frontend/app/js/utils/componentLoader.js`
- Sentry runtime config: `copilot-app/frontend/app/js/sentry-init.js`

Code UI existant a reutiliser (wiring + etats):
- `copilot-app/frontend/app/app.js` (renderers + navigation; ajouter un adaptateur `fetchJson` commun au lieu de dupliquer `fetch` par widget).
- `copilot-app/frontend/app/mockData.js` (uniquement comme fallback visible, jamais en nominal).

## Anti-duplication Checklist (a copier dans les PRs)

- [ ] J'ai cherche un helper existant (`rg`) avant de creer un nouveau module.
- [ ] Je charge les snapshots via `src/services/snapshot_loader.py` (pas de `load_json("x") or load_json("x.json")`).
- [ ] Je normalise les tickers via `src/core/ticker_normalization.py`.
- [ ] Je re-utilise les caches existants (TTLCache / `_response_cache_*` / cache_layer) au lieu d'introduire un cache ad-hoc.
- [ ] Pour endpoints LLM: je copie le pattern Judge (debug bypass cache + JSON strict + Pydantic + fallback chain).
- [ ] Pour appels LLM: j'utilise `services.g4f_client.call_llm(mode=\"dev|best\")` (pas de provider inline).
- [ ] Pour UI: je rebranche des widgets existants avant d'en creer de nouveaux.
