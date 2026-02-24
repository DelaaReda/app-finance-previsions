# BACKEND_AGENT_BRIEF.md

## Mission
Stabiliser les endpoints MVP backend sans refacto large.

## Scope
- `copilot-app/backend/src/api/main.py`
- `copilot-app/backend/src/services/*`
- `copilot-app/backend/jobs/*` (uniquement impact MVP)

## Acceptance
- `/api/health` OK
- `/api/stocks/prices` OK
- `/api/news/feed` OK
- `/api/forecasts` OK
- `/api/copilot/ask` répond sans crash

## Validation Commands
- `./finance-copilot.sh restart`
- `curl -fsS http://localhost:8050/api/health`
- `curl -fsS 'http://localhost:8050/api/stocks/prices?ticker=AAPL&range=1mo'`
- `curl -fsS 'http://localhost:8050/api/news/feed?limit=5'`
- `curl -fsS 'http://localhost:8050/api/forecasts?limit=5'`
