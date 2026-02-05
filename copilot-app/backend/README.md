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
- Jobs de génération (news, macro, judge_enrich…) : `copilot-app/backend/jobs/` (appelés par le script).
- Données (snapshots) : `copilot-app/backend/data/`.
- Anciennes variantes/compat : `copilot-app/backend/legacy-archive/`.

## Tests rapides (manuels)
- Health : `curl -s http://localhost:8050/api/health`
- Judge : `curl -s 'http://localhost:8050/api/judge?limit=1'`

## Notes
- Variables env : `.env` à la racine backend (inclut OPEN_ROUTER_API_KEY, clés FRED, etc.).
- Si un module manque (feedparser, duckdb…), installe dans `.venv` :
  ```bash
  cd copilot-app/backend
  .venv/bin/pip install feedparser duckdb
  ```
