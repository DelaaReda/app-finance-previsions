# Finance App Architecture

Updated: 2026-02-24

## High-level components
- Backend (FastAPI): `/Users/venom/Documents/analyse-financiere/copilot-app/backend`
- Frontend (static files): `/Users/venom/Documents/analyse-financiere/copilot-app/frontend/app`
- Data and cache: `/Users/venom/Documents/analyse-financiere/copilot-app/backend/data` and `/Users/venom/Documents/analyse-financiere/copilot-app/data`

## Backend layers
- API routes and wiring: `backend/src/api/`
- Services/business logic: `backend/src/services/`
- Analytics/ML/LLM logic: `backend/src/analytics/` and `backend/src/agents/`
- Jobs (batch refresh): `backend/jobs/`
- Scripts (ingestion helpers): `backend/scripts/`

## Judge subsystem
- Router: `backend/src/api/routes/judge.py`
- Main endpoints:
  - `GET /api/judge`
  - `GET /api/judge/quality`
  - `GET /api/judge/options`
- LLM run endpoint in main API:
  - `POST /api/llm/judge/run`

## Data flow (practical)
- Jobs ingest/refresh market sources (news, macro, prices, indicators).
- Snapshots are written under `backend/data/*`.
- API reads those snapshots and serves normalized responses.
- Judge pipeline enriches forecasts and exposes quality metrics.

## Legacy note
- Old code variants are archived in `backend/legacy-archive/`.
- Active code should stay under `backend/src/` and `backend/jobs/`.
