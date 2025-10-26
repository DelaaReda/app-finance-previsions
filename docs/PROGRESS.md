```markdown
🎯 SPRINT-7 : AGENT COMMODITIES + STABILISATION ! 🚀

Livré:
- ✅ Agent Commodities: prévisions pour 5 matières premières (Or, Pétrole, Argent, Cuivre, Maïs)
- ✅ Intégration Dashboard: section Top Commodities avec prix et confiance
- ✅ Page Forecasts: support multi-actifs (Actions + Commodities)
- ✅ Tests smoke: inclut /backtests et /evaluation
- ✅ Données corrigées: dates historiques alignées avec prix disponibles

Prochaines étapes:
- Enrichissement macro: PMI/ISM, VIX, spreads de crédit
- Page Qualité: anomalies détectées par data_quality
- Tests UI automatisés: dash.testing + Playwright

⸻

🎯 SPRINT-5 : 2/5 PAGES COMPLÈTEMENT FONCTIONNELLES ! 🚀

Pages migrées selon plan ATLAS :
- ✅ News/Aggregation : Filtres, synthèse IA, table actualités
- ✅ Deep Dive : Analyse ticker complète avec graphiques et données

Prochaines étapes (priorités ATLAS) :
- Forecasts multi-ticker - DataTable avec filtres par horizon/ticker
- Backtests/Evaluation - Agents + pages pour métriques de performance
- Quality dashboard - Anomalies détectées par data_quality

L'application Dash compte maintenant 10 pages fonctionnelles !

⸻

Progress & Roadmap (Investor App)
Progress & Roadmap (Investor App)

Recent (UI/Ops)
- UI canonical port 5555; single instance policy with `make ui-start/stop/restart` and watcher `make ui-watch`.
- Top‑nav sticky + footer added; Home/sidebar reorganized (Prévisions vs Administration).
- Safer UI copy: removed "lancez scripts/make" prompts from user pages; guidance moved to Admin/Docs.
- Scoreboard page uses header/footer and CSV export; Observability hides sensitive key names.
- SearXNG local stack added (ops/web/searxng-local) and probe script; web navigator prefers local.
- Security & CI: pip‑audit/safety/bandit/secret‑scan; UI smoke (Playwright MCP) added.

ATLAS feedback captured
- UI/Code directions recorded under docs/atlas/
- Backlog extended with F4F agents EPICs
- Next: implement in‑page dates/empty states across pages

Status (done)
- Data + Freshness
  - Harvester: news/macro/prices/fundamentals (watchlist override via data/watchlist.json)
  - Macro FRED parquet; prices parquet; Data Quality scanner + freshness; Alerts page
- LLM models (text-only, reasoning-first)
  - Dynamic watcher (verified + official sources), working.json with provider/latency/source
  - Local API probing and merge; Scoreboard page (uses, avg_agreement, provider, latency, source)
- Forecasting & Analytics
  - Baseline rules + ML; LLM ensemble + arbiter (Investigations/Topics)
  - Fusion final_score (rule 0.65 + ML 0.25 + LLM 0.10)
  - Risk Monitor; Macro Regime; Investment Memos per ticker
- Investor UI
  - Dashboard (Final Top‑5, regime badge, 90‑day metrics, alerts mini‑summary)
  - Signals (weight sliders, CSV); Portfolio (tilt presets, rebalance simulator, exports)
  - Watchlist manager; Alerts (thresholds + CSV); Settings (tilt & alert thresholds)
  - Changes (regime/risk/top‑N/brief deltas); Notes (journal)
- Automation
  - Makefile: factory-run, refresh/probe, risk, memos, fuse, backfill-prices

Recent additions
- Official models source in watcher (G4F_SOURCE=official|verified|both) and Makefile target
- Settings page; Alerts reads alert thresholds; Portfolio tilt reads presets
- LLM Scoreboard shows provider/latency/source; CSV export
- Backfill script for 5y prices; Data Quality coverage check ≥5 years
- Recession Risk agent + page; Makefile target `recession`
- Earnings Calendar agent and UI page; Makefile target `earnings`
- Agents Status dashboard page (freshness of forecasts, regime, risk, earnings, memos, quality)
- Fix: add `import os` in data_quality to avoid NameError in env var read
- LLM agents runner now writes to `data/forecast/dt=YYYYMMDD/llm_agents.json` (consistent with UI)
- Alerts page: section "Earnings à venir" (fenêtre configurable + export CSV)
- Align `agent_daily.py` outputs to `data/forecast/dt=YYYYMMDD` (so Alerts finds `brief.json`)
- Security posture: prefer official MCP servers; disable non‑official Puppeteer MCP by default; add `ops/security/security_scan.sh` and Makefile `sec-audit` to run pip-audit/safety (+ optional semgrep/trivy)
- MCP UI smoke (best‑effort): `ops/ui/mcp_ui_smoke.mjs` + `make ui-smoke-mcp` to navigate/screenshot via @playwright/mcp
- Network observability (scan‑only):
  - `ops/net/net_observe.py` + `make net-observe` — journalise connexions TCP par processus (JSONL sous artifacts/net)
  - `ops/net/tls_sni_log.sh` + `make net-sni-log` — journalise SNI TLS et IP (tshark requis; pas de blocage)
  - Découplé de l’app (répertoire ops/net) pour éviter toute confusion
- Legacy cleanup
  - Déplacement du shim `searxng-local/finnews.py` et de son test sous `ops/legacy/` (exclus de pytest via `norecursedirs=ops`)
 - CI: `.github/workflows/ci.yml` exécute `make test`, UI smoke et `sec-audit`, publie les artifacts
 - SearXNG local: `ops/web/searxng-local/` + Make (`searx-up`, `searx-down`, `searx-logs`), `SEARXNG_LOCAL_URL` prioritaire dans `web_navigator`

Sprint-5: Migration completion and advanced features
Objectives
- Migrate remaining Streamlit pages: News/Aggregation, Deep Dive analysis, Forecasts multi-ticker, Backtests/Evaluation, Reports, Quality dashboard, LLM Scoreboard, Notes & Memos.
- Implement backtest_agent.py and evaluation_agent.py with Dash pages for performance curves and metrics (MAE, RMSE).
- Enhance macro series: add PMI/ISM, LEI, VIX, commodity baskets; quality coverage checks ≥5 years.
- Advanced UX: beginner mode with tooltips, alerts badge in navbar, "Why" explanations for Portfolio tilts.
- MCP integration: fix web-eval-agent connection, integrate automated UX testing in CI pipeline.
- Documentation: create docs/architecture/dash_overview.md, update README with new pages and MCP usage.
- Tests: comprehensive smoke and MCP tests on all new pages; manual validation with fresh data.
Delivered (in progress)
- ✅ News page: data loading from news partitions or JSONL, sector filtering, search, AI summary placeholder, table display with fallbacks.
- ✅ Deep Dive page: ticker input with analysis, 5-year price charts with SMAs, forecasts table, news section, basic statistics.
- ✅ Forecasts page: multi-ticker data loading from final.parquet, horizon/ticker filtering, sorting by score/ticker/horizon, summary statistics.
- ✅ Integration: /news, /deep_dive, /forecasts routes added to sidebar navigation in Analyse & Prévisions section.
- ✅ Tests: smoke 200 on all routes including new pages; MCP script corrected for error visibility.

Next (nice to have)
- Beginner mode (tooltips + simplified fields across pages)
- Alerts badge in navbar + count
- “Why” tooltips on Portfolio tilt choices (from Regime/Risk agents)
- Official models auto-fetch with richer parsing when network permits

How to run
- Factory run: `make factory-run`
- Keep models fresh: `make g4f-refresh` or `make g4f-refresh-official`
- Backfill 5y prices: `make backfill-prices`
- UI: `PYTHONPATH=src streamlit run src/apps/agent_app.py`
- Forecast agents: `make equity-forecast` then `make forecast-aggregate`
- Macro & freshness: `make macro-forecast` and `make update-monitor`
Dash migration
- Plan: `docs/architecture/dash_migration.md`
Sprint‑3 livré
- Charts Plotly adaptés aux données réelles (inflation/yield/unemployment/recession_prob), badge global sidebar, filtre watchli corrigé.
- MCP web-eval-agent intégré (script + Makefile), potentielles corrections rapportées.
- Docs workflow dev mis à jour avec step MCP avant push.

Sprint-4: Finale macro et observability
Objectives
- Finalize macro pages: Regimes/Risk/Recession with full Plotly graphs, trend badges, recent data tables; fallbacks for missing columns.
- Fix Dashboard watchlist: ensure Top-10 filtering works for entered tickers, show Alert if none found.
- MCP tests: run dash-mcp-test on all routes, analyze report and fix issues.
- Observability: badge global (green=OK recent data, yellow=data stale, red=server down), 30s auto-refresh, link to Agents Status.
- Docs: Sprint-4 section in PROGRESS.md, update README with dash-mcp-test usage.
- Tests: smoke 200 on all routes; manual checks with fresh data.
Delivered (completed)
- ✅ Sidebar multipage + thème Bootstrap sombre (Cyborg).
- ✅ Dashboard: sélecteur de date (dt=YYYYMMDD), Top‑10 Final (1m) avec états vides FR, KPIs Macro (CPI YoY, pente 10Y‑2Y, prob. récession).
- ✅ Signals: DataTable triable/filtrable/exportable, filtre d’horizon (1w/1m/1y), surbrillance WATCHLIST.
- ✅ Portfolio: contrôles Top‑N et pondération (égalitaire vs proportionnelle), états vides robustes.
- ✅ Observability: ping HTTP Dash + log live; scripts dash start/stop/restart fiables (Makefile).
- ✅ Agents Status: page dédiée listant dernières partitions forecasts/final/macro + freshness.json.
- ✅ Macro pages: Regimes/Risk/Recession with Plotly charts, trend badges, data tables; robust fallbacks.
- ✅ Watchlist filter: callback corrected, dynamic headers, error handling for empty results.
- ✅ MCP script: stdio fixed for error visibility, screenshot save enabled.
- ✅ Data cleanup: all generated files removed from git tracking, .gitignore updated.
- ✅ API operative.sh: configured and functional for web-eval-agent MCP.
- ✅ Tests: smoke 200 on all routes; manual validation with fresh data.

How to validate Dash quickly
- Générer données: `make equity-forecast && make forecast-aggregate && make macro-forecast && make update-monitor`.
- Redémarrer UI: `make dash-restart-bg`; statut: `make dash-status`; logs: `make dash-logs`.
- Smoke HTTP: `make dash-smoke` (200 sur routes clés, incl. /agents).
Planned/Started (agents)
- Equity forecast agent: generates dt=YYYYMMDD/forecasts.parquet with baseline (momentum/vol) for 1w/1m/1y.
- Forecast aggregator: reads latest forecasts.parquet, computes final_score, writes dt=YYYYMMDD/final.parquet.
- Makefile targets: `make equity-forecast`, `make forecast-aggregate`.
Phase 2 (in progress)
- Macro forecast agent: writes `data/macro/forecast/dt=YYYYMMDD/macro_forecast.{json,parquet}` with CPI YoY, yield curve slope, unemployment and a crude recession probability across horizons (1m/3m/12m). Target: `make macro-forecast`.
- Update monitor agent: writes `data/quality/dt=YYYYMMDD/freshness.json` with latest partition dates and coverage checks; target: `make update-monitor`. Observability reads and displays the summary.
