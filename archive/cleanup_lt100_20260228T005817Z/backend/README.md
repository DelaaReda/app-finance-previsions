# Finance Copilot – Backend Quick Guide

## Lancer / arrêter
- Démarrer ou redémarrer tout (backend + jobs + frontend statique) :
  ```bash
  ./finance-copilot.sh restart
  ```
- Arrêter :
  ```bash
  ./finance-copilot.sh stop
  ```

## Endpoints clés
- Santé backend :
  ```bash
  curl -s http://localhost:8050/api/health
  ```
- Judge (LLM) avec 1 verdict :
  ```bash
  curl -s 'http://localhost:8050/api/judge?limit=1' | jq
  ```
- Historique qualité judge (snapshots quotidiens) :
  ```bash
  curl -s 'http://localhost:8050/api/judge/quality/history?horizon_days=5&min_samples=20&limit=30' | jq
  ```
- Docs API :
  - http://localhost:8050/docs

## Appels LLM (standard projet)
- Entrypoint unique backend: `src/services/g4f_client.py::call_llm(...)`
- Modes:
  - `mode=\"fastest\"` pour latence minimale en tests dev
  - `mode=\"dev\"` pour tests rapides
  - `mode=\"best\"` pour meilleure qualité + fallback chain
- Config rapide:
  - `LLM_MODEL_MODE=best|dev|fastest`
  - `LLM_FASTEST_MODE=1` (optionnel pour forcer fastest par défaut)
  - `LLM_FASTEST_MODELS`, `LLM_FASTEST_TIMEOUT_SECONDS`, `LLM_FASTEST_MAX_ATTEMPTS`
  - `LLM_DEV_MODELS`, `LLM_DEV_TIMEOUT_SECONDS`, `LLM_DEV_MAX_ATTEMPTS`
  - `LLM_BEST_TIMEOUT_SECONDS`, `LLM_BEST_MAX_ATTEMPTS`
  - Pour Judge uniquement: `LLM_JUDGE_MODE=fastest` (legacy compatible: `JUDGE_LLM_MODE`)
  - Timeouts Judge: `JUDGE_ROW_TIMEOUT_SECONDS`, `JUDGE_ANALYZE_TIMEOUT_SECONDS(_FASTEST)`, `JUDGE_G4F_TIMEOUT_SECONDS(_FASTEST)`
  - Fastest flags: `JUDGE_FASTEST_SKIP_ECON_AGENT`, `JUDGE_FASTEST_DISABLE_PAID_FALLBACKS`, `JUDGE_FASTEST_SKIP_JSON_REPAIR`
  - Debug Judge: `JUDGE_ALLOW_DEBUG_FULL=1` active le debug complet; si `JUDGE_DEBUG_ADMIN_TOKEN` est défini, fournir `X-Debug-Token` pour `debug_full=true`.

## Logs
- Backend : `copilot-app/backend/api.log`
  - Inclut les requêtes/réponses LLM (`judge_llm_request`, `judge_llm_raw_response`).
- Frontend statique : `/tmp/frontend.log`

## Frontend (statique)
- Servi depuis `copilot-app/frontend/app` via `python -m http.server 5173` (script gère tout).
- URL : http://localhost:5173

## Où est le code actif
- Backend : `copilot-app/backend/src/...` (API FastAPI, services, analytics).
- Entrée API unique : `copilot-app/backend/src/api/main.py` (appelée par `copilot-app/backend/run_api.py`).
- Jobs de génération (news, macro, data_quality_gate, judge_enrich…) : `copilot-app/backend/jobs/` (appelés par le script).
- Données (snapshots) : `copilot-app/backend/data/`.
- Anciennes variantes/compat : `copilot-app/backend/legacy-archive/`.

## Référence exemple (bonnes pratiques endpoint)
- Guide standard endpoint/API (contrat, cache, fallback, observabilité, tests):
  - `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`

## Tests rapides (manuels)
- Health : `curl -s http://localhost:8050/api/health`
- Judge : `curl -s 'http://localhost:8050/api/judge?limit=1'`
- Judge quality history : `curl -s 'http://localhost:8050/api/judge/quality/history?horizon_days=5&min_samples=20&limit=30'`

## Notes
- Variables env : `.env` à la racine backend (inclut OPEN_ROUTER_API_KEY, clés FRED, etc.).
- Contrat de normalisation ticker (source unique) : `src/core/ticker_normalization.py`
  - Canonique: `ABC` ou `ABC.X` (ex: `BRK.B`)
  - Variantes acceptées: `BRK-B`, `BRK/B`, `NYSE:BRK.B`, `AAPL.US`, `$AAPL`
- Massive.com (prix historiques via API) : définir `MASSIVE_API_KEY` pour activer la source Massive.
- Sentry (FastAPI) : définir `SENTRY_DSN` pour activer la capture erreurs/traces.
  - Optionnel : `SENTRY_SEND_DEFAULT_PII` (défaut `true`), `SENTRY_ENABLE_LOGS` (défaut `true`), `SENTRY_TRACES_SAMPLE_RATE` (défaut `1.0` en debug / `0.2` hors debug), `SENTRY_PROFILE_SESSION_SAMPLE_RATE` (défaut `0.2` en debug / `0.0` hors debug), `SENTRY_PROFILE_LIFECYCLE` (défaut `trace`).
  - Vérification en dev : `GET /sentry-debug` (route active en mode debug).
  - Frontend statique : `GET /api/frontend/config` expose un payload public (DSN + sampling) consommé par `frontend/app/js/sentry-init.js`.
    - Variables frontend dédiées : `FRONTEND_SENTRY_DSN`, `FRONTEND_SENTRY_TRACES_SAMPLE_RATE`, `FRONTEND_SENTRY_REPLAYS_SESSION_SAMPLE_RATE`, `FRONTEND_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE`.
    - Fallback DSN : `FRONTEND_SENTRY_DSN` -> `SENTRY_DSN`.
    - Propagation traces frontend->backend activée via `trace_propagation_targets`.
  - Jobs backend (ex: `news_ingest`, `news_sentiment`, `macro_series_snapshot`, `stocks_prices_refresh`, `judge_enrich`, `judge_quality_report`, `validate_and_generate_data`) taggent `job.name` et envoient les exceptions vers Sentry.
  - Runbook debug : `docs/2026-02/SENTRY_DEBUG_RUNBOOK.md`
- Si un module manque (feedparser, duckdb…), installe dans `.venv` :
  ```bash
  cd copilot-app/backend
  .venv/bin/pip install feedparser duckdb
  ```
