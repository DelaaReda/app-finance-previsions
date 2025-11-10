# Forecast Data Pipeline (Hybrid ML + G4F)

This document explains how the forecast pipeline now works end‑to‑end with **real data** and G4F models.

## Data Flow Overview

1. **Snapshots reused first**
   - Macro indicators → `backend/data/macro_series.json` (refreshed by `python backend/jobs/macro_series_snapshot.py`).
   - News feed → `backend/data/news_feed.json` (refreshed by `python backend/jobs/news_ingest.py`).
   - Stock prices → pulled live via `core.market_data.get_price_history` then cached to `backend/data/forecast_pipeline/prices/<ticker>.csv` for 6h.
2. **Feature assembly** (`NewsMacroStocksForecastPipeline`)
   - Builds technical signals (RSI, SMA, MACD, Bollinger, ATR) from the cached OHLC data.
   - Aggregates real RSS articles per ticker (sentiment + volume spikes).
   - Reconstructs macro regime score by z‑scoring each FRED series.
3. **Hybrid forecast generation** (`ForecastHybridV1`)
   - ML layer estimates direction/expected return from the composite signals.
   - LLM layer (G4F) validates + adjusts confidence using the freshest working models from `g4f_model_watcher`.
   - Final rows include `features_used`, `market_context`, and are written to `backend/data/forecasts.json`.

## CLI Recipe

```bash
cd copilot-app/backend

# 1. Refresh supporting snapshots (optional but recommended)
source .venv/bin/activate
python jobs/news_ingest.py
python jobs/macro_series_snapshot.py

# 2. Run the hybrid forecast job (pulls real prices, reuses caches)
python jobs/forecasts.py

# 3. Inspect the output
jq '.rows[0]' data/forecasts.json
```

The FastAPI endpoint `/api/forecasts` now serves the file written in step 3 with millisecond latency and never hits G4F at request time.

## Troubleshooting

| Issue | Checks |
| --- | --- |
| Forecast rows empty | `python jobs/forecasts.py --tickers SPY,QQQ` to log detailed errors. Ensure yfinance network reachable. |
| LLM validation slow | Run `python -m src.agents.g4f_model_watcher --ensure` to refresh working models cache. |
| News sentiment zero | Confirm `data/news_feed.json` contains `score`/`sentiment` fields (run news job). |
| Macro regime flat | Re-run `macro_series_snapshot` so the normalization window has fresh values. |

## Key Files

- `backend/models/pipeline_news_macro_stocks_forecast.py` – assembles real features (news/macro/prices).
- `backend/models/forecast_hybrid_v1.py` – ML + G4F adjudication producing final rows.
- `backend/jobs/forecasts.py` – CLI entrypoint that persists snapshots for the API.
- `data/forecast_pipeline/prices/` – cached OHLC files; safe to delete if you need a clean refresh.

Keep this loop tight: **refresh snapshots → run forecasts job → hit `/api/forecasts`**. EOF
