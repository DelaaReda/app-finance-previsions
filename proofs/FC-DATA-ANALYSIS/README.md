# FC-DATA-ANALYSIS — Data Pipelines Architecture Assessment

Date (UTC): 2025-11-05

Scope
- Backend endpoints used by UI: health, dashboard/kpis, brief daily/weekly, backtests, forecasts, news feed, macro series, stocks/:ticker.
- Data stores observed: data/news.jsonl (exists), forecast parquet paths (mentioned), macro series API (array), ticker snapshots.

Key Observations
- News feed: present and structured, but needs broader sources + dedup + freshness metrics in health.
- Macro series: API returns array; UI expects mapping → UX mismatch; store parquet per series_id.
- Stocks ticker: many indicators null (RSI/SMA) → show N/A in UI; provide backend fallback compute from /stocks/prices.
- Forecasts: cache-first exists conceptually; enforce materialization daily and serve instant snapshots.
- Backtests: reads from forecasts; ensure it uses materialized `final.parquet` to avoid latency.
- Health: expose `last_updates` + `news_stats` for UI freshness badge.

Artifacts
- Validation logs: `proofs/FC-UI-VALIDATION/*`
- Audit snapshots: `proofs/FC-DATA-ANALYSIS/*`

Tasks Created (see TASKS_BOARD.md)
- FC-DATA-001…010 cover ingestion expansion, freshness SLA, NLP enrich, forecasts materialization, tech indicators fallback, macro storage/snapshot, quality gate, audit script, storage conventions, rate limits.

DoD for the sprint
- All UI pages render either content or clear empty-state with freshness.
- /api/health exposes freshness for news/forecasts/brief; no repeated 429s.
- News 24h coverage >= target; dedup rate <3%.

