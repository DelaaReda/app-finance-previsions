# Architecture React + FastAPI + Lakehouse

Dernière mise à jour : 2025-11-02

## Vue d'ensemble

L'application migre vers React (frontend) + FastAPI (backend) + Lakehouse (data) pour un copilote financier scalable.

## Frontend (React)

- **Framework**: React + Vite + TypeScript strict
- **State**: React Query (SWR) pour cache/api calls
- **Routing**: React Router
- **Components**: Atoms/Molecules/Organisms dans `webapp/src/components/`
- **Services**: `webapp/src/services/` pour appels API
- **Hooks**: `webapp/src/hooks/` pour logique data
- **Types**: `webapp/src/types/` TS strict matching Pydantic
- **Build**: `npm run build`, `tsc`, `eslint`

Pages clés:
- Dashboard: Overview TopSignals/TopRisks
- Macro: Régime GRW/INF/POL/USD/CMD
- Stocks: Indicateurs techniques par ticker
- News: Feed + features agrégées
- MarketBrief: Scoring 40/40/20 + picks
- TickerSheet: Vue 360° ticker

## Backend (FastAPI)

- **API**: `src/api/main_v2.py`, Swagger `/api/docs`
- **Schemas**: Pydantic dans `src/api/schemas.py`
- **Services**: `src/core/` pour logique métier
- **Data**: Lakehouse parquet bronze/silver/gold
- **Tests**: pytest, mypy, ruff

Endpoints principaux:
- `/api/health`
- `/api/macro/snapshot`
- `/api/stocks/indicators`
- `/api/news/feed`
- `/api/brief`
- `/api/rag/search`

## Data (Lakehouse)

- **Bronze**: Raw data (news JSONL, etc.)
- **Silver**: Cleaned/enriched
- **Gold**: Aggregated features
- **Partitions**: `dt=YYYY-MM-DD/`
- **Read-only**: Une fois écrits
- **Historique**: 5+ ans

## RAG & LLM

- **Index**: News silver pour retrieval
- **Search**: BM25 ou embeddings
- **Copilot**: Q&A justifié par sources

## QA Gates

- Backend: ruff check, mypy, pytest
- Frontend: tsc, eslint, build
- E2E: Playwright smoke 5 pages
- Merge: QA verte uniquement

## Déploiement

- **Local**: uvicorn port 8050, npm dev port 5173
- **Env**: .env pour API keys, paths
- **CI**: GitHub Actions pour tests/build
