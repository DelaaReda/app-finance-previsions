# Module Index — App Finance Prévisions (réutilisation rapide)

But: permettre à un dev (KILO inclus) d’identifier rapidement où réutiliser, sans créer de doublons.

Notation: `module: function()` (résumé bref). Liste non exhaustive mais centrée sur le cœur.

## src/core

- io_utils.py
  - `setup_logging(name)` — logger standard.
  - `ensure_dir(path)` — crée dossier.
  - `read_jsonl(path)` / `write_jsonl(data, path)` — IO JSONL.
  - `read_parquet(path)` / `write_parquet(df, path)` — IO Parquet.
  - `Cache` — petit cache en mémoire.
  - `get_artifacts_dir(name)` — répertoire artefacts.
  - `ensure_utc(dt)` / `parse_iso_date(s)` — dates utilitaires.
- market_data.py
  - `get_price_history(ticker, start=None, end=None, interval="1d")` — prix via yfinance.
  - `get_fundamentals(symbol)` — fondamentaux (source interne/à compléter).
  - `get_fred_series(series_id, start=None)` — série FRED.
- models.py
  - `FinancialMetric`, `CompanyFinancials`, `FinancialAnalysis`, `FeatureBundle` — Pydantic modèles.
- stock_utils.py
  - `guess_ticker(company_name)` — heuristique ticker.
  - `fetch_price_history(ticker, start, end)` — wrapper prix.

## src/tools

- parquet_io.py
  - `latest_partition(base_dir) -> Optional[Path]` — retourne `Path('.../dt=YYYYMMDD[HH]')`.
  - `read_parquet_latest(base_dir, filename) -> Optional[pd.DataFrame]` — charge fichier dans la dernière partition.
- make.py
  - `run_make(target, args=None, timeout=900, cwd=None) -> Dict` — exécute une cible Make et capture la sortie.
- git_patcher.py
  - `current_branch()` / `create_branch(name)` — gestion branches.
  - `apply_unified_diff(diff_text, commit_message)` — applique patch + commit.
  - `commit_all(message)` — stage + commit tout.

## src/agents (sélection)

- equity_forecast_agent.py
  - `_momentum(series, days)` — feature mom.
  - `_forecasts_for_ticker(ticker, horizons)` — calcule prévisions baseline.
  - `run_once() -> Path` — écrit `data/forecast/dt=.../forecasts.parquet`.
- forecast_aggregator_agent.py (si présent)
  - agrège vers `final.parquet` (scores finaux).
- macro_forecast_agent.py
  - `run_once() -> Dict` — écrit `data/macro/forecast/dt=.../macro_forecast.{json,parquet}`.
- update_monitor_agent.py
  - `run_once() -> Dict` — calcule fraîcheur et couverture (écrit sous `data/quality/dt=.../freshness.json`).
- data_quality.py
  - `scan_*()` — rapports qualité (news/macro/prices/forecasts/features/events/coverage).
  - `write_report(obj)` — écrit un rapport qualité.
- data_harvester.py
  - `harvest_news_recent(...) -> int` — ingère dernières news.
- llm/
  - runtime.py — `LLMClient.generate(messages, json_mode=True, retries, ...)`.
  - schemas.py — `LLMEnsembleSummary`, `Contributor` (Pydantic).
  - toolkit.py — tools read‑only: `load_forecasts`, `load_macro`, `freshness_status`.
  - arbiter_agent.py — `run_llm_summary(save_base="data/llm_summary")` → écrit `summary.json` + `trace_raw.json` (horaire).

## src/analytics (sélection)

- phase2_technical.py / phase3_macro.py / phase5_fusion.py — logiques d’analyse et de fusion.
  - `fuse_*`, `run_fusion(...)` — fonctions de combinaison des signaux.
- phase4_sentiment.py — pipeline news/sentiment.
  - `score_news_items`, `aggregate_sentiment`, `build_sentiment_view`.
- backtest_news_impact.py — évalue impact news (à consulter pour réutilisation métriques/tests).

## src/dash_app/pages (UI Dash)

- Pages prod: `dashboard.py`, `forecasts.py`, `deep_dive.py`, `news.py`, `backtests.py`, `evaluation.py`, `regimes.py`, `risk.py`, `recession.py`, `observability.py`, `agents_status.py`, `quality.py`.
  - Exposent généralement `layout()` et des callbacks associés.
  - Lire via loaders/partitions; ids stables pour tests (ex: `#forecasts-table`, `#risk-body`).
- Pages DEV: `integration_*.py` — toujours gatées par `DEVTOOLS_ENABLED=1`.

## orch / scripts / ops

- Makefile — cibles UI, agents, santé, LLM; ex: `llm-summary-run`, `dash-smoke`, `ui-health`.
- scripts/dash_start_bg.sh — lance Dash BG; `PYTHONPATH` est configuré.
- ops/ui/*.mjs — Playwright (UI health, MCP scripts).

## Recherche rapide (exemples)

- Trouver une fonction: `rg -n "def run_llm_summary\(" src`
- Voir où une partition est lue: `rg -n "final.parquet" src`
- Lister pages: `ls src/dash_app/pages`

---

Si une fonction manque: ouvrir une issue et proposer un wrapper dans `src/tools/` plutôt que réécrire dans chaque page. Toujours ajouter des tests unitaires pour les helpers ajoutés.

