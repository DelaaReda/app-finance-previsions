```markdown
📌 Today — Sprint-12: MIGRATION COMPLÈTE STREAMLIT → DASH ! 🎉

Small fixes (today)
- Streamlit canonique confirmé sur `5555` via `src/apps/agent_app.py` + scripts `ui_*`.
- Correction duplicate Streamlit widget id (clé explicite `ticker_input_sidebar`) dans `src/apps/stock_analysis_app.py` (port 5557). Conseillé: `make streamlit-stock-restart` ou `make apps-full-restart`.
- Docs mises à jour: junior-dev, README (ajout `make apps-full-restart`).

Delivered:
- ✅ **MIGRATION 100% COMPLÈTE**: Toutes les 28 pages Streamlit migrées vers Dash (13 nouvelles pages + 15 existantes)
- ✅ **36 pages Dash totales** maintenant disponibles (vs 23 avant la migration)

**Nouvelles Pages Critiques:**
- ✅ **Alerts** (`alerts.py`): Qualité données + mouvements macro/watchlist + earnings avec exports CSV
- ✅ **Watchlist** (`watchlist.py`): Gestion liste de surveillance, édition, export commande shell
- ✅ **Settings** (`settings.py`): Configuration presets tilt macro + seuils alertes
- ✅ **Memos** (`memos.py`): Investment memos par ticker avec accordéons JSON
- ✅ **Notes** (`notes.py`): Journal personnel markdown quotidien avec aperçu temps réel

**Nouvelles Pages Informatives:**
- ✅ **Home** (`home.py`): Page d'accueil avec liens vers toutes sections
- ✅ **Events** (`events.py`): Calendrier événements macro à venir
- ✅ **LLM Models** (`llm_models.py`): Liste modèles LLM fonctionnels (g4f)

**Nouvelles Pages Avancées:**
- ✅ **Changes** (`changes.py`): Changements depuis veille (régime/risque/top-N/brief)
- ✅ **Earnings** (`earnings.py`): Calendrier publications résultats avec filtre
- ✅ **Reports** (`reports.py`): Rapports d'analyse générés
- ✅ **Advisor** (`advisor.py`): Assistant IA (placeholder future implémentation)

**Architecture & Code Quality:**
- ✅ Respect des bonnes pratiques (`/docs/dev/engineering_rules.md`)
- ✅ Empty states FR systématiques sur toutes pages
- ✅ Loaders dédiés via `dash_app.data.loader`
- ✅ Callbacks propres avec Input/Output/State
- ✅ Export CSV pour données tabulaires
- ✅ Gestion erreurs propre avec try/except
- ✅ Composants Bootstrap (Cards, Alerts, Tables)

**Modifications app.py:**
- ✅ Sidebar reorganisée avec 23 liens Analyse & Prévisions
- ✅ Page registry étendu avec 13 nouvelles routes
- ✅ Imports optimisés et groupés logiquement

**Documentation:**
- ✅ Guide complet: `/docs/architecture/MIGRATION_COMPLETE.md`
- ✅ Résumé des 36 pages avec fonctionnalités clés
- ✅ Instructions tests et déploiement

Next:
- Tests manuels sur toutes nouvelles pages
- `make dash-smoke` et `make ui-health`
- Décommission Streamlit (archivage src/apps/)
- Tests E2E avec Playwright pour nouvelles pages
- Polish UI et UX si nécessaire

How to run:
- Start Dash: `make dash-restart-bg`
- Check status: `make dash-status`
- Test imports: `PYTHONPATH=src python3 -c "from dash_app.app import app; print('OK')"`

⸻

**ANCIENNES NOTES (PRE-MIGRATION)**

📌 Sprint-11 (Migration Streamlit → Dash: 4 pages)

Delivered:
- ✅ **Page Alerts** (`src/dash_app/pages/alerts.py`): Migration complète
  - Section Qualité: issues avec tri par sévérité, export CSV
  - Section Mouvements: macro + watchlist avec slider seuil, export CSV
  - Section Earnings: calendrier avec slider fenêtre, export CSV

- ✅ **Page Watchlist** (`src/dash_app/pages/watchlist.py`): Gestion liste surveillance
  - Affichage watchlist actuelle, édition, sauvegarde, génération commande export

- ✅ **Page Memos** (`src/dash_app/pages/memos.py`): Investment Memos
  - Sélecteurs date/ticker, affichage markdown, accordéons JSON

- ✅ **Page Notes** (`src/dash_app/pages/notes.py`): Journal personnel
  - Édition markdown, aperçu temps réel, création automatique aujourd'hui

- Data loaders (Dash): `src/dash_app/data/{loader.py,paths.py}` pour lecture robuste
- Quality (bug fix): guards type-safe sur freshness/report
- Tests: unit + intégration + E2E
- Deep Dive: comparateur multi-tickers + overlay prévisions
- Risk/Regimes: lecture parquet avec fallback macro_forecast
- LLM Summary: page + orchestrateur + scheduler
- Orchestrateur: pipeline séquentiel best-effort

🎯 SPRINT-7 : AGENT COMMODITIES + STABILISATION ! 🚀

- ✅ Agent Commodities: prévisions 5 matières premières
- ✅ Intégration Dashboard: Top Commodities
- ✅ Page Forecasts: support multi-actifs
- ✅ Tests smoke: inclut /backtests et /evaluation

Progress & Roadmap (Investor App)

Recent (UI/Ops)
- UI canonical port 5555; single instance policy
- Top-nav sticky + footer; Home/sidebar reorganized
- Safer UI copy: removed script prompts from user pages
- Scoreboard CSV export; Observability hides sensitive keys
- SearXNG local stack; Security & CI (pip-audit/safety/bandit)

Status (done)
- Data + Freshness: Harvester, Macro FRED, Quality scanner, Alerts
- LLM models: Dynamic watcher, Scoreboard page
- Forecasting: Baseline + ML + LLM ensemble + arbiter
- Fusion: final_score (rule 0.65 + ML 0.25 + LLM 0.10)
- Risk Monitor, Macro Regime, Investment Memos
- Investor UI: Dashboard, Signals, Portfolio, Watchlist, Alerts, Settings, Changes, Notes
- Automation: Makefile targets

---

Update — Streamlit unified skeleton (Sprint-codex-1)

- New skeleton created under `src/apps/streamlit/` with core modules and 5 pages (Dashboard, Signals, Deep Dive, Forecasts, Observability).
- Added `make streamlit-run` (default port 5566) to try it without touching canonical 5555.
- Loader uses existing `src/tools/parquet_io.py` helpers; UI shows clean empty-states if partitions are missing.
- Next: wire charts/KPIs, polars/duckdb acceleration, smoke tests and screenshots.
