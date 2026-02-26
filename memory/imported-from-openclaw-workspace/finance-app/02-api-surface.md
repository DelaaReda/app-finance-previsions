# Finance App API Surface

Updated: 2026-02-24
Base URL: `http://localhost:8050`

## Health and config
- `GET /api/health`
- `GET /api/freshness`
- `GET /api/frontend/config`

## Stocks and market
- `GET /api/stocks/prices`
- `GET /api/stocks/top`
- `GET /api/stocks/search`
- `GET /api/stocks/universe`
- `GET /api/stocks/meta`
- `GET /api/stocks/screener`
- `GET /api/stocks/{ticker}`
- `GET /api/stocks/{ticker}/sheet`

## Macro and news
- `GET /api/macro/series`
- `GET /api/macro/snapshot`
- `GET /api/macro/indicators`
- `GET /api/news/feed`
- `GET /api/news/sentiment`
- `GET /api/news/events`
- `GET /api/news/features/daily`

## Judge and LLM
- `GET /api/judge`
- `GET /api/judge/quality`
- `GET /api/judge/options`
- `POST /api/llm/judge/run`
- `GET /api/llm/providers/working`
- `POST /api/llm/providers/refresh`

## Intelligence and reporting
- `GET /api/recommendations/daily`
- `GET /api/performance/matrix`
- `GET /api/opportunities`
- `GET /api/backtests`
- `GET /api/intelligence/snapshot`
- `GET /api/dashboard/kpis`

## Quick curl checks
```bash
curl -s http://localhost:8050/api/health
curl -s 'http://localhost:8050/api/judge?limit=1' | jq
curl -s 'http://localhost:8050/api/judge/quality?horizon_days=5&min_samples=20' | jq
```
