# Finance Copilot – Guide rapide (backend + frontend statique)

## Démarrer / arrêter
- (Re)lancer backend + jobs + frontend statique :  
  ```bash
  ./finance-copilot.sh restart
  ```
- Arrêter :  
  ```bash
  ./finance-copilot.sh stop
  ```

## URLs
- Backend : http://localhost:8050  
  Docs : http://localhost:8050/docs
- Frontend statique : http://localhost:5173 (servi depuis `frontend/app`)

## Endpoints utiles (curl)
- Santé :  
  `curl -s http://localhost:8050/api/health`
- Judge (LLM) :  
  `curl -s 'http://localhost:8050/api/judge?limit=1' | jq`

## Logs
- Backend : `copilot-app/backend/api.log`  
  (Inclut les requêtes/réponses LLM : `judge_llm_request`, `judge_llm_raw_response`).
- Frontend statique : `/tmp/frontend.log`

## Structure active
- Code backend : `copilot-app/backend/src/...` (API FastAPI, services, analytics).
- Entrée API unique : `copilot-app/backend/src/api/main.py` (lancement via `copilot-app/backend/run_api.py`).
- Jobs (ingest/news/macro/judge_enrich) : `copilot-app/backend/jobs/` (lancés par le script).
- Données (snapshots) : `copilot-app/backend/data/`.
- Frontend statique : `copilot-app/frontend/app` (fichiers HTML/CSS/JS, pas de build Vite).
- Anciennes variantes archivées : `copilot-app/backend/legacy-archive/`.

## Dépendances / env
- Variables : `copilot-app/backend/.env` (OPEN_ROUTER_API_KEY, clés FRED, etc.).
- Installer manquants (ex : feedparser, duckdb) :
  ```bash
  cd copilot-app/backend
  .venv/bin/pip install feedparser duckdb
  ```

## Tests rapides (manuels)
- Health : `curl -s http://localhost:8050/api/health`
- Judge : `curl -s 'http://localhost:8050/api/judge?limit=1' | jq`

## Notes
- Pas de build frontend : le script sert directement `frontend/app` via `python -m http.server 5173`.
- Les jobs s’exécutent au démarrage (news, sentiment, judge_enrich, macro).***
