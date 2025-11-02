# Dash overview — pages & agents

This document lists Dash pages and the agents they rely on (I/O contracts).

## New pages added (Sprint-5)
- /news — News & Aggregation
  - Reads: `data/news/dt=YYYYMMDD/*.parquet` or `data/news.jsonl` fallback
  - Renders: summary (AI placeholder), table (`news-table`), filters sector/search
  - Generate data: run harvester/harvest scripts (see README) or `make` targets if configured

- /deep_dive — Deep dive per ticker
  - Reads: `data/prices/ticker=TICKER/prices.parquet`, `data/forecast/dt=*/final.parquet`, news fallback
  - Renders: price chart (5y), forecasts table, news cards

- /forecasts — Forecasts Multi-Ticker
  - Reads: `data/forecast/dt=*/final.parquet` (preferred) or `forecasts.parquet`
  - Renders: DataTable with filters (horizon, ticker), summary card

- /backtests — Backtests & Évaluation (scaffold + agent)
  - Agent: `src.agents.backtest_agent` (writes `data/backtest/dt=YYYYMMDD/details.parquet` and `summary.json`)
  - Renders: metrics and performance curves (placeholder until backtest details exist)

- /evaluation — Evaluation metrics (MAE, RMSE, Hit ratio)
  - Agent: `src.agents.evaluation_agent` (writes `data/evaluation/dt=YYYYMMDD/metrics.json`)
  - Renders: list of metrics per agent/provider or overall

## Agents (I/O)
- `src/agents/backtest_agent.py`
  - Inputs: latest forecasts (`data/forecast/dt=*/forecasts.parquet` or `final.parquet`), cached prices `data/prices/ticker=.../prices.parquet`
  - Outputs: `data/backtest/dt=YYYYMMDD/details.parquet`, `summary.json`
  - CLI: `PYTHONPATH=src python -m src.agents.backtest_agent --horizon 1m --top-n 5`

- `src/agents/evaluation_agent.py`
  - Inputs: latest forecasts, cached prices
  - Outputs: `data/evaluation/dt=YYYYMMDD/metrics.json`, `details.parquet`
  - CLI: `PYTHONPATH=src python -m src.agents.evaluation_agent --horizon 1m`

## How to generate required data for News page
- Preferred flow (Make targets):
  - `make harvest-news` (or the repository equivalent) to create `data/news/dt=YYYYMMDD/news_*.parquet`
  - Alternatively, place a JSONL at `data/news.jsonl` with fields: `title`, `summary`, `source`, `published`, `sentiment`, `tickers`
- Quick dev: create a small `data/news.jsonl` sample with 2-3 lines, then reload Dash.

## Tests & validation
- Use `make dash-smoke` to validate HTTP 200 on routes.
- Run `make dash-mcp-test` to run MCP/playwright checks (screenshot + UX tests).
- Unit tests added: `tests/test_pages.py` (verifies basic layout IDs exist for News and Deep Dive pages)

## Notes
- Pages must handle missing partitions gracefully and display FR empty states.
- Agents must write dated partitions under `data/.../dt=YYYYMMDD/` as per repo conventions.
