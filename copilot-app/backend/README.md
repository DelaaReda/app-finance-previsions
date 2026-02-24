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
