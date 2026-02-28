# API Endpoints (source de vérité frontend/backend)

## Endpoints actifs (2026-02-28)

- `GET /api/health`
  - Objectif: health + status global de l’application
  - Usage: `platform/startup`, checks monitoring
- `GET /api/forecasts`
  - Params: `limit`, `min_confidence`, `symbols`, `horizon`
  - Usage: cartes de prévisions / trade ideas / opportunités
- `GET /api/news/feed`
  - Params: `limit`, `symbols`, `since`, `score_min`, `category`
  - Usage: bloc actualités du dashboard
- `GET /api/stocks/top`
  - Params: `limit`, `sector`, `order_by`, `ascending`
  - Usage: top movers, heatmaps, sector map
- `GET /api/dashboard/kpis`
  - Params: `symbols`, `horizon`, `include_history`, `include_components`
  - Usage: indicateurs KPI + backtest + qualité de signal

## Contrat runtime attendu

- Les réponses doivent être en mode `ok + data`.
- Champs utiles à lire côté frontend:
  - `data.tradeIdeas`
  - `data.newsItems`
  - `data.topStocks`
  - `data.marketDrivers`
  - `data.marketCalendar`
  - `data.sectorPerformance`
  - `data.kpis`
  - `data.newsImpact`
  - `meta.generatedAt`, `meta.sources`, `meta.modelVersions`, `meta.warnings`

## Référence frontend (frontend forecasts)

- Connector: `apps/web/src/domains/forecasts/contracts/apiConnector.js`
- Initialisation: `window.initLiveData()` (polling 120s)
- Écouteur d’update: `financecopilot:live-dashboard-updated`
- Fallback: données locales de secours intégrées dans le frontend (`FALLBACK_*` dans `app.js`) si l’API est indisponible

## Gouvernance docs

- Source opérationnelle: `docs/ops/`
- Archive documentaire de migration: `docs/operations/` (lecture seule, contexte historique)
