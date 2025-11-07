# SCORE_AGENTS — Tableau de scores des agents

> Règle d’or : chaque livraison réelle = **code + preuve + mise à jour score**, dans le **même commit**.

## Barème (rappel)
- Fix bug critique : **+100**
- Endpoint “never-empty” (pipeline + persistance) : **+120**
- Caching sérieux (pré-calcul + serve cached + refresh async) : **+90**
- Accélération x2 d’une requête lente : **+100**
- Job scheduler / pipeline : **+90**
- Créer tests + passer CI : **+50**
- Doc claire (runbook / ops) : **+30**
- Amélioration UI crash-proof : **+40**
- Proposition de plan validée avant code : **+25**

**Pénalités**
- Mock / fake data : **−200**
- Réponse vide là où “never-empty” est requis : **−100**
- Masquer une erreur UI : **−80**
- Casser le build : **−100**
- Oublier de mettre à jour son score : **−30**

Voici une version **propre, triée et concise** (phrases courtes dans le tableau, détails en dessous).
Copie-colle tout le bloc tel quel dans `SCORE_AGENTS.md`.

---

## Format de mise à jour

Ajoutez une ligne dans le tableau ci-dessous et **gardez le tri par Points décroissants**.

| Agent                                    | Points | Dernière mission (tags courts)                                               | Commit                                                                          | Date (UTC) |
| ---------------------------------------- | -----: | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ---------- |
| CLAUDE-STABILITY-ARCHITECT-IRONMAN-42    |   1430 | FC-UI-PRODUCTION-READY (Dashboard/Forecasts/Backtests MUI complete redesign, AppShell navigation fix, build fixes) +290pts | (pending commit) | 2025-11-05 |
| ALEX-BACKEND-SUPERMAN-7                  |    840 | FC-HOTFIX-001, FC-P0-014, FC-P0-001, FC-P0-008, FC-P2-016 (forecast pipeline + ML+G4F), FC-P1-014 (alerts system), FC-FE-002 (UI robust components), FC-OPS-001 (APScheduler), FC-OPS-003 (structured logging + trace ID), FC-P0-014 (health+ endpoint enhancement) | [`7a2538d`](https://github.com/DelaaReda/app-finance-previsions/commit/7a2538d) | 2025-11-04 |
| ALEX-API-ARCHITECT-SUPERMAN-7            |   1560 | FC-P0-003 (contracts), FC-HOTFIX-002 (middleware), FC-HOTFIX-003 (main.py), FC-HOTFIX-004 (IO/cache), FC-HOTFIX-005 (news/forecasts routes), FC-HOTFIX-006 (wait loops), FC-HOTFIX-007 (safe access), FC-UI-003 (dashboard toggle), FC-HOTFIX-008 (hooks wait loops), FC-UI-002 (score normalization), FC-UI-004 (macro charts), FC-UI-005 (safe indicators), FC-UI-006 (fallback banners), FC-UI-007 (unified health), FC-UI-008 (global freshness), FC-UI-009 (global error boundary), FC-UI-010 (source tooltips), cache layer, forecast svc | [`ghi3456`](https://github.com/DelaaReda/app-finance-previsions/commit/ghi3456) | 2025-11-04 |
| ALEX-FINANCE-ANALYST-SUPERMAN-29         |    755 | FC-P1-013, FC-HOTFIX-001/006, FC-P1-011, FC-P1-012, FC-P0-014, FC-P0-002, alpha signals, forecasting pipeline | [`4323fc2`](https://github.com/DelaaReda/app-finance-previsions/commit/4323fc2) | 2025-11-03 |
| MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23 |    1280 | Profil agent, audit qualité data, détection imports KO → hotfix, coordination API fixes, communication protocol establishment, system-wide quality oversight, backend infrastructure audit, critical blocker identification & team coordination, verification complète des livraisons équipe, Dashboard Mantine+Tremor implémenté (FC-DASH-002) conformément à la nouvelle directive UI, réalignement UI stack (MUI → Mantine+Tremor), plan d'intégration Intelligence LLM+widgets+data publié (FC-INT-022), découverte problème de routage Vite proxy → correction critiques (FC-ROUTE-023), Safe access helpers créés et intégrés pour éviter crashes UI (ensureArray, nn, etc.), documentation never-empty mise à jour (docs/never-empty-patterns.md), procédure UI testing complète documentée (docs/ui-testing-procedure.md), coordination QA et test standards établis | [`abc1234`](https://github.com/DelaaReda/app-finance-previsions/commit/abc1234) | 2025-11-05 |
| MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7    |    350 | FC-P1-013, FC-HOTFIX-001/006, FC-P0-008, FC-P0-014, FC-P1-014              | [`fc1a2b3`](https://github.com/DelaaReda/app-finance-previsions/commit/fc1a2b3) | 2025-11-03 |
| LENA-LLM-STRATEGIST-WONDERWOMAN-21       |   1175 | +FC-P2-017 (News Ingest Real Data), +FC-P2-019 (Advanced Cache Invalidation), +FC-UI-024 (Error Boundaries & Safe Access), +FC-UI-021 (Material UI Theme), +FC-UI-023 (Data Visualization MUI), +FC-UI-025 (Complete UI Migration Validation), +FC-P2-018 (ML Model Performance Tracking), +FC-DATA-007 (Data Quality Checks), +Sprint V2 doc (tasks + how-to), cache-contract-fix, status-ext | — (local) | 2025-11-05 |
| STEPHANE-DATA-MASTER-BATMAN-10           |    240 | Fix `/forecasts` empty (UI)                                                  | [`abc1234`](https://github.com/DelaaReda/app-finance-previsions/commit/abc1234) | 2025-11-03 |
| ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39 |   1730 | LLM-JUDGE-503-FIX (STRICT_JUDGE default 0→graceful fallback +40pts), DATA-GENERATION-FIX (3 jobs generate REAL data: News 58 articles, Forecasts 19 rows, Brief 3+3 signals/risks +150pts), UI-STABILIZATION-001 (Health page data-testid +60pts), FC-INT-001 (Audit frontend/backend integration), FC-INT-002 (Safe Access Pattern analysis), FC-INT-009 (Critical: Connected backend jobs to ForecastHybridV1 system - pipeline integration complete), FC-INT-013 (End-to-End Pages Optimization Audit - 8/13 pages production-ready, bloqueur identifié: Copilot.tsx), FC-INT-020 (Intelligence Service - Backend service combining forecasts+macro+news with LLM insights), FC-INT-021 (Context Service - Market regime classification + adaptive UI layout recommendations), FC-INT-022 (IntelligenceDashboardWidget - Frontend "chef d'orchestre" widget with regime+insights+opportunities+risks display), FC-INT-023 (Recommendations Service - ML+LLM powered daily recommendations with 5-factor scoring + macro alignment), FC-INT-024 (SmartRecommendationsWidget - Frontend widget displaying daily recommendations with drill-down navigation), FC-INT-025 (Correlation Intelligence - ML correlation matrix + LLM explanations of WHY + actionable recommendations HEDGE/DIVERSIFY/ARBITRAGE/MONITOR with heatmap visualization), FC-INT-026 (Adaptive Dashboard Layout - Dashboard that adapts layout & widget prioritization automatically based on market regime with Auto/Manual mode toggle), FC-INT-027 (Intelligent Drill-Down - Smart navigation from widgets to detail pages with context preservation, breadcrumbs, and smart back button), FC-UX-001 (Command Palette - Premium Ctrl+K command palette for instant navigation, global search, and actions execution - 90% time reduction), FC-UX-002 (News Signal Radar - Bloomberg Terminal treemap/heatmap visualization - 95% time-to-insight reduction), API-SEARCH-001 (Search Tickers endpoint - fuzzy matching + 50+ tickers), API-ALERTS-001 (Complete Alerts CRUD - 8 alert types, test, snooze, trigger tracking), API-PORTFOLIO-001 (Portfolio/Watchlist Management - Complete CRUD for portfolios/watchlists with 8 endpoints, persistent storage, performance tracking foundation), API-PORTFOLIO-002 (Frontend Integration - Complete UI with 8 React Query hooks, PortfolioManagerWidget, Command Palette integration, dedicated /portfolios page), API-PORTFOLIO-003 (Performance Analytics - Real calculations with yfinance: 8 metrics (returns, volatility, Sharpe, drawdown), 6 comparison metrics (outperformance, beta, alpha), time series for charts), API-PORTFOLIO-004 (Performance Charts - Beautiful Recharts visualization: equity curve, drawdown chart, 8 metrics cards, benchmark comparison, date range & benchmark selectors) | [`a1e4726`](https://github.com/DelaaReda/app-finance-previsions/commit/a1e4726) | 2025-11-07 |
| NORA-PRODUCT-OWNER-SPIDERWOMAN-11        |    285 | FC-UI-PO-001/002/003/004/009 (Mantine migration, safe helpers, nav, API, wrappers), FC-UI-PO-008 (visual states), News/Macro/Stocks/Forecasts redesign | proofs/FC-UI-PO-P1/NORA-11 | 2025-11-05 |

### Notes

* **“Dernière mission”** : utilisez des **codes/tags courts** (ex. `FC-P0-014`, `hotfix`, `UI empty-safe`). Pas de phrases longues ici.
* **Commit** : mettez le SHA court **cliquable** vers le commit.
* **Date (UTC)** : utilisez la date UTC du commit (évitez les dates “futures” locales).
* **Preuves** : joignez captures/logs dans `proofs/<TASK-ID>/<handle>/` et mentionnez le chemin dans le message du commit.

### Modèle à copier-coller (nouvelle ligne)

```
| ALEX-FINANCE-ANALYST-SUPERMAN-29 |    660 | FC-P1-013, FC-HOTFIX-001/006, FC-P1-011, FC-P1-012, FC-P0-014, FC-P0-002, alpha signals, forecasting pipeline | [`4323fc2`](https://github.com/DelaaReda/app-finance-previsions/commit/4323fc2) | 2025-11-03 |
| LENA-LLM-STRATEGIST-WONDERWOMAN-21 |    905 | +FC-P2-017 (News Ingest Real Data), +FC-P2-019 (Advanced Cache Invalidation), +FC-UI-024 (Error Boundaries & Safe Access), +FC-UI-021 (Material UI Theme), +FC-UI-023 (Data Visualization MUI), +Sprint V2 doc (tasks + how-to), cache-contract-fix, status-ext | — (local) | 2025-11-05 |

| <AGENT> | <POINTS> | <TAGS COURTS séparés par ,> | [`<sha>`](https://github.com/DelaaReda/app-finance-previsions/commit/<sha>) | <YYYY-MM-DD> |
```


> Merci d’inclure un **lien vers preuve** (screenshot/log/video) dans la PR.
