# Finance App Overview

Updated: 2026-02-24

## Scope
- Workspace root: `/Users/venom/Documents/analyse-financiere`
- Main app code: `/Users/venom/Documents/analyse-financiere/copilot-app`
- Note: `finance-app` folder exists but currently almost empty; active implementation is in `copilot-app`.

## Product goal
- Aggregate market data (prices, news, macro, indicators).
- Generate analysis and signals (including LLM judge outputs).
- Expose data through FastAPI endpoints and a static web UI.

## Runtime endpoints
- Backend API: `http://localhost:8050`
- Swagger docs: `http://localhost:8050/docs`
- Frontend static UI: `http://localhost:5173`

## Primary entry points
- Launcher wrapper: `/Users/venom/Documents/analyse-financiere/finance-copilot.sh`
- Main launcher: `/Users/venom/Documents/analyse-financiere/copilot-app/copilot.sh`
- API bootstrap: `/Users/venom/Documents/analyse-financiere/copilot-app/backend/run_api.py`
- API app: `/Users/venom/Documents/analyse-financiere/copilot-app/backend/src/api/main.py`
