# ARCHITECTURE_MAP.md

## Source of Truth (Current)
- Backend API entrypoint: `copilot-app/backend/src/api/main.py`
- Backend runner: `copilot-app/backend/run_api.py`
- Frontend app: `copilot-app/frontend/app/`
- Start/stop wrapper: `finance-copilot.sh` -> `copilot-app/copilot.sh`
- Jobs: `copilot-app/backend/jobs/`
- Runtime data snapshots: `copilot-app/backend/data/`

## Hybrid Zones (Needs Guardrails)
- `copilot-app/backend/services/` (historique)
- `copilot-app/backend/src/services/` (cible active)
- `copilot-app/backend/legacy-archive/` (archives existantes)

## Import Policy
- Prioriser `src/` comme racine active
- Éviter nouveaux imports depuis `backend/services` si équivalent existe dans `src/services`
- Toute logique legacy conservée doit être explicitement marquée "LEGACY"

## MVP Endpoints (v1)
- `GET /api/health`
- `GET /api/stocks/prices`
- `GET /api/news/feed`
- `GET /api/forecasts`
- `POST /api/copilot/ask`

## Frontend Integration Rule
- Remplacer mocks seulement pour les vues MVP
- Si fallback mock nécessaire, afficher badge explicite: `Données simulées`
