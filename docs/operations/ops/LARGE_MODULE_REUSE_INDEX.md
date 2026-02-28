# Large Module Reuse Index (Backend)

Generated at: `2026-02-28 00:36:32Z`
Threshold: `>= 400` lines

Purpose: make large modules obvious and reusable before creating new code.

Regenerate with:
```bash
python3 scripts/generate_large_module_reuse_index.py
```

Scan roots:
- `copilot-app/backend/src`
- `copilot-app/backend/services`
- `copilot-app/backend/jobs`
- `copilot-app/backend/models`
- `copilot-app/backend/storage`

## Summary

- Total modules listed: `51`
- `agent`: `2`
- `analytics`: `9`
- `api_entrypoint`: `1`
- `api_route`: `3`
- `api_service_facade`: `3`
- `core`: `2`
- `ingestion`: `6`
- `job`: `1`
- `module`: `2`
- `research`: `7`
- `service`: `15`

## Priority Reuse Modules

- `copilot-app/backend/src/analytics/econ_llm_agent.py` (1038 lines) -> `from analytics.econ_llm_agent import ...` - LLM economic analyst core.
- `copilot-app/backend/src/analytics/market_intel.py` (446 lines) -> `from analytics.market_intel import ...` - Market context pack builder.
- `copilot-app/backend/src/analytics/phase1_fundamental.py` (808 lines) -> `from analytics.phase1_fundamental import ...` - Fundamental forecast block.
- `copilot-app/backend/src/analytics/phase2_technical.py` (841 lines) -> `from analytics.phase2_technical import ...` - Technical forecast block.
- `copilot-app/backend/src/analytics/phase3_macro.py` (1048 lines) -> `from analytics.phase3_macro import ...` - Macro regime/nowcast block.
- `copilot-app/backend/src/analytics/phase4_sentiment.py` (587 lines) -> `from analytics.phase4_sentiment import ...` - Sentiment/news signal block.
- `copilot-app/backend/src/analytics/phase5_fusion.py` (649 lines) -> `from analytics.phase5_fusion import ...` - Multi-signal fusion block.
- `copilot-app/backend/src/services/forecasts_service.py` (604 lines) -> `from services.forecasts_service import ...` - Forecast orchestration service.
- `copilot-app/backend/src/services/g4f_client.py` (838 lines) -> `from services.g4f_client import ...` - Canonical LLM wrapper (mode + fallback).
- `copilot-app/backend/src/services/judge_pipeline.py` (831 lines) -> `from services.judge_pipeline import ...` - Judge-grade verdict pipeline.

## Modules

| Lines | Module | Category | Import Hint | Public Symbols (sample) | Reuse Note |
|---:|---|---|---|---|---|
| 4981 | `copilot-app/backend/src/api/main.py` | `api_entrypoint` | `from api.main import ...` | `create_app, ApiResponse, CopilotAskRequest, LLMJudgeRequest, register_routes, run_server` | FastAPI bootstrap/reference only. Keep orchestration thin, avoid new business logic here. |
| 3517 | `copilot-app/backend/src/api/routes/judge.py` | `api_route` | `from api.routes.judge import ...` | `get_judge_verdicts, get_judge_quality, get_judge_quality_history, get_judge_options` | Protected Judge template route. Reuse patterns/services around it; do not clone route logic inline. |
| 1048 | `copilot-app/backend/src/analytics/phase3_macro.py` | `analytics` | `from analytics.phase3_macro import ...` | `MacroBundle, NowcastView, ExposureReport, MacroRegimeView, ScenarioImpact, fetch_fred_series, fetch_market_proxies, resample_align` | Reusable implementation candidate. |
| 1038 | `copilot-app/backend/src/analytics/econ_llm_agent.py` | `analytics` | `from analytics.econ_llm_agent import ...` | `EconomicInput, clean_llm_text, EconomicAnalyst, main, ask_model, arbitre` | Central economic LLM analyst module reused by multiple routes/agents. |
| 886 | `copilot-app/backend/src/ingestion/finnews.py` | `ingestion` | `from ingestion.finnews import ...` | `now_utc, parse_date, strip_html, sha256, domain_of, guess_lang, bool_query_match, NewsItem` | Reusable implementation candidate. |
| 841 | `copilot-app/backend/src/analytics/phase2_technical.py` | `analytics` | `from analytics.phase2_technical import ...` | `IndicatorSet, TechnicalSignals, RegimeInfo, RiskStats, TradeResult, BacktestReport, WalkForwardReport, load_prices` | Reusable implementation candidate. |
| 838 | `copilot-app/backend/src/services/g4f_client.py` | `service` | `from services.g4f_client import ...` | `resolve_llm_mode, get_ranked_tested_models, get_mode_model_candidates, call_g4f, call_llm` | Canonical LLM call entrypoint (model mode + fallback handling). |
| 831 | `copilot-app/backend/src/services/judge_pipeline.py` | `service` | `from services.judge_pipeline import ...` | `JudgeProfile, load_profile, NewsItem, PhaseScores, MlPrior, JudgePayload, LLMResponse, calculate_age_hours` | Shared verdict computation pipeline; reuse from services, not routes. |
| 811 | `copilot-app/backend/src/agents/g4f_model_watcher.py` | `agent` | `from agents.g4f_model_watcher import ...` | `ModelProbe, build_working_from_models_txt, build_working_from_test_results, refresh_async, refresh, load_working_models, merge_from_working_txt, merge_from_remote` | Reusable implementation candidate. |
| 808 | `copilot-app/backend/src/analytics/phase1_fundamental.py` | `analytics` | `from analytics.phase1_fundamental import ...` | `debug_io, HealthRatios, PeerMultiples, ComparableZScores, DCFResult, FairValueAggregate, FundamentalView, convert_to_currency` | Reusable implementation candidate. |
| 758 | `copilot-app/backend/src/ingestion/financials_ownership_client.py` | `ingestion` | `from ingestion.financials_ownership_client import ...` | `yahoo_snapshot, yahoo_options_chain, sec_submissions, sec_filings_index, sec_form4_insiders, sec_13f_holdings, build_ownership_snapshot, main` | Reusable implementation candidate. |
| 712 | `copilot-app/backend/jobs/news_ingest.py` | `job` | `from jobs.news_ingest import ...` | `parse_published_datetime, build_dynamic_sources, extract_tickers, fetch_rss_feed, parse_rss_xml, score_article, detect_sentiment, run_news_ingest` | Scheduler layer. Reuse services/core helpers instead of job-to-job copy. |
| 700 | `copilot-app/backend/services/recommendations_service.py` | `service` | `from services.recommendations_service import ...` | `RecommendationsService, get_recommendations_service` | Reusable implementation candidate. |
| 649 | `copilot-app/backend/src/analytics/phase5_fusion.py` | `analytics` | `from analytics.phase5_fusion import ...` | `PillarScores, RiskMetrics, FusionOutput, fuse_fundamental, fuse_technical, fuse_macro, fuse_sentiment, combine_scores` | Reusable implementation candidate. |
| 639 | `copilot-app/backend/src/research/web_navigator.py` | `research` | `from research.web_navigator import ...` | `RedirectError, NonJSONError, ForbiddenError, TooManyRequestsError, fetch_searxng_instances, search_searxng, finance_search, main` | Reusable implementation candidate. |
| 622 | `copilot-app/backend/src/research/macro_firecrawl.py` | `research` | `from research.macro_firecrawl import ...` | `fc_extract, fc_search, MacroData, get_economic_indicators, get_market_data, get_news_impact, get_geopolitical_risks, get_commodity_prices` | Reusable implementation candidate. |
| 612 | `copilot-app/backend/src/ingestion/finviz_client.py` | `ingestion` | `from ingestion.finviz_client import ...` | `company_snapshot, insider_trades, latest_filings, options_chain, news, futures, FinvizCompany, fetch_company_all` | Reusable implementation candidate. |
| 611 | `copilot-app/backend/src/ingestion/macro_derivatives_client.py` | `ingestion` | `from ingestion.macro_derivatives_client import ...` | `fred_series, tradingeconomics_calendar, cboe_indexes, cftc_cot, build_macro_snapshot, main` | Reusable implementation candidate. |
| 607 | `copilot-app/backend/services/context_service.py` | `service` | `from services.context_service import ...` | `ContextService, get_context_service` | Reusable implementation candidate. |
| 604 | `copilot-app/backend/src/services/forecasts_service.py` | `service` | `from services.forecasts_service import ...` | `get_forecasts_payload, get_forecast_detail_payload` | Forecast endpoint orchestration service aligned with Judge template parity. |
| 587 | `copilot-app/backend/src/analytics/phase4_sentiment.py` | `analytics` | `from analytics.phase4_sentiment import ...` | `NewsItem, SentimentDetail, EventSignal, ScoredNews, AggregateSentiment, fetch_yf_news, fetch_rss, score_sentiment` | Reusable implementation candidate. |
| 586 | `copilot-app/backend/src/api/routes/news_impact.py` | `api_route` | `from api.routes.news_impact import ...` | `get_news_impact_analysis, calculate_single_news_impact, generate_impact_summary, calculate_article_relevance, categorize_news_impact, calculate_impact_confidence, estimate_price_impact, calculate_volatility_factor` | Reference endpoint. Keep reusable logic in services/core modules. |
| 582 | `copilot-app/backend/src/agents/data_harvester.py` | `agent` | `from agents.data_harvester import ...` | `harvest_news_recent, backfill_news, update_macro, update_prices_and_fundamentals, generate_upcoming_events, investigate_macro, discover_topics_via_llm, run_once` | Reusable implementation candidate. |
| 573 | `copilot-app/backend/src/api/services/dashboard_ui_service.py` | `api_service_facade` | `from api.services.dashboard_ui_service import ...` | `build_market_drivers_snapshot, build_news_impact_table, build_performance_snapshot, build_portfolio_summary, load_portfolio_allocation, build_portfolio_health` | Facade layer for routes; good place for thin composition. |
| 572 | `copilot-app/backend/src/core/data_access.py` | `core` | `from core.data_access import ...` | `get_close_series, load_macro_forecast_rows, get_last_update_timestamp, get_latest_forecast_date, get_latest_macro_date, load_latest_forecasts_data, get_equity_final_data, get_commodity_data` | Reusable implementation candidate. |
| 570 | `copilot-app/backend/src/api/routes/search.py` | `api_route` | `from api.routes.search import ...` | `fuzzy_match, search_tickers, search_global, calculate_similarity, get_sectors, universal_search_endpoint` | Reference endpoint. Keep reusable logic in services/core modules. |
| 560 | `copilot-app/backend/src/services/judge_builder.py` | `service` | `from services.judge_builder import ...` | `build_judge_verdict` | Reusable implementation candidate. |
| 549 | `copilot-app/backend/services/intelligence_service.py` | `service` | `from services.intelligence_service import ...` | `RegimeMetrics, get_market_intelligence_snapshot, get_market_context_snapshot` | Reusable implementation candidate. |
| 526 | `copilot-app/backend/src/analytics/indicators_basic.py` | `analytics` | `from analytics.indicators_basic import ...` | `calculate_sma, calculate_ema, calculate_rsi, calculate_bollinger_bands, calculate_macd, calculate_technical_indicators, enrich_ticker_data_with_indicators, get_enriched_ticker_data` | Reusable implementation candidate. |
| 522 | `copilot-app/backend/src/ingestion/finviz.py` | `ingestion` | `from ingestion.finviz import ...` | `FinvizClient, fetch_finviz_global_news, fetch_finviz_company_news, fetch_finviz_insider_recent, fetch_finviz_company_insiders, fetch_finviz_company_ratings, fetch_finviz_company_snapshot, fetch_finviz_company_institutions` | Reusable implementation candidate. |
| 492 | `copilot-app/backend/src/research/scoring.py` | `research` | `from research.scoring import ...` | `score_macro_conditions, score_technical, score_news_sentiment, calculate_composite_score, get_top_signals_and_risks, compute_composite_brief` | Reusable implementation candidate. |
| 488 | `copilot-app/backend/src/research/alerts.py` | `research` | `from research.alerts import ...` | `alerts_for_ticker, summarize_alerts, get_alerts_by_category, get_high_priority_alerts` | Reusable implementation candidate. |
| 482 | `copilot-app/backend/src/analytics/backtest_news_impact.py` | `analytics` | `from analytics.backtest_news_impact import ...` | `parse_window, ensure_tz_utc, load_news, PriceCache, fetch_daily_prices, EventConfig, nearest_trading_day, compute_market_model_AR` | Reusable implementation candidate. |
| 482 | `copilot-app/backend/src/api/services/scoring_service.py` | `api_service_facade` | `from api.services.scoring_service import ...` | `get_macro_contribution, get_technical_contribution, get_news_contribution, compute_composite_score, compute_universe_scores, get_top_signals, build_brief, get_signals_top` | Facade layer for routes; good place for thin composition. |
| 478 | `copilot-app/backend/services/universal_search.py` | `service` | `from services.universal_search import ...` | `UniversalSearchService, universal_search, get_search_suggestions` | Reusable implementation candidate. |
| 472 | `copilot-app/backend/src/data/news_service.py` | `module` | `from data.news_service import ...` | `NewsArticle, DailyFeatures, NewsStats, NewsService, get_news_service` | Reusable implementation candidate. |
| 464 | `copilot-app/backend/services/portfolio_performance_service.py` | `service` | `from services.portfolio_performance_service import ...` | `PortfolioMetrics, BenchmarkComparison, PerformanceTimeSeries, fetch_price_data, calculate_returns, calculate_portfolio_returns, calculate_sharpe_ratio, calculate_drawdown` | Reusable implementation candidate. |
| 464 | `copilot-app/backend/services/prediction_analyzer.py` | `service` | `from services.prediction_analyzer import ...` | `PredictionAnalyzerService, get_prediction_accuracy, get_prediction_trends, compare_prediction_models` | Reusable implementation candidate. |
| 463 | `copilot-app/backend/src/api/services/macro_service.py` | `api_service_facade` | `from api.services.macro_service import ...` | `get_macro_overview, get_macro_snapshot, get_macro_indicators` | Facade layer for routes; good place for thin composition. |
| 458 | `copilot-app/backend/src/core/data_loader.py` | `core` | `from core.data_loader import ...` | `DataLoader, load_json, save_json, load_generic_data, load_with_fallback` | Reusable implementation candidate. |
| 448 | `copilot-app/backend/services/alert_rules.py` | `service` | `from services.alert_rules import ...` | `AlertRulesService, get_all_alerts, create_alert, update_alert, delete_alert, get_alert_types, get_default_alert_rules` | Reusable implementation candidate. |
| 446 | `copilot-app/backend/src/analytics/market_intel.py` | `analytics` | `from analytics.market_intel import ...` | `now_utc, iso, collect_news, collect_ownership, collect_finviz, collect_macro_derivs, build_unified_features, build_snapshot` | Reusable implementation candidate. |
| 433 | `copilot-app/backend/src/ingestion/financial_news_ingest.py` | `ingestion` | `from ingestion.financial_news_ingest import ...` | `fetch_financial_news, estimate_sentiment_score, estimate_importance_score, calculate_freshness_score, deduplicate_articles, compute_news_feed, run_news_ingest_job` | Reusable implementation candidate. |
| 432 | `copilot-app/backend/src/research/nlp_enrich.py` | `research` | `from research.nlp_enrich import ...` | `summarize, sentiment_score, extract_entities, guess_language, EnrichedArticle, enrich_article, ask_model` | Reusable implementation candidate. |
| 431 | `copilot-app/backend/src/services/judge_quality.py` | `service` | `from services.judge_quality import ...` | `EvaluatedForecast, build_judge_quality_report_from_data, build_judge_quality_report` | Reusable implementation candidate. |
| 429 | `copilot-app/backend/services/correlation_intelligence_service.py` | `service` | `from services.correlation_intelligence_service import ...` | `CorrelationIntelligenceService, get_correlation_intelligence_service` | Reusable implementation candidate. |
| 429 | `copilot-app/backend/src/research/peers_finder.py` | `research` | `from research.peers_finder import ...` | `get_peers_auto, find_peers, main` | Reusable implementation candidate. |
| 423 | `copilot-app/backend/src/research/versioned_notes.py` | `research` | `from research.versioned_notes import ...` | `NoteType, NoteVersion, Note, VersionedNotesStore` | Reusable implementation candidate. |
| 405 | `copilot-app/backend/services/indicator_service.py` | `service` | `from services.indicator_service import ...` | `calculate_sma, calculate_ema, calculate_rsi, calculate_macd, calculate_bollinger_bands, calculate_volatility, fill_missing_technical_indicators, run_technical_indicators_job` | Reusable implementation candidate. |
| 405 | `copilot-app/backend/src/api/schemas.py` | `module` | `from api.schemas import ...` | `TraceMetadata, ApiResponse, HealthStatus, FreshnessStatus, HealthData, HealthResponse, DataSourceFreshness, FreshnessData` | Reusable implementation candidate. |
| 400 | `copilot-app/backend/services/tech_indicators_fallback.py` | `service` | `from services.tech_indicators_fallback import ...` | `calculate_sma, calculate_rsi, calculate_ema, calculate_macd, enrich_missing_indicators, calculate_missing_indicators_from_prices` | Reusable implementation candidate. |
