Streamlit Unified App — Skeleton (Sprint-codex-1)

Overview
- New Streamlit multi-page skeleton under `src/apps/streamlit/`.
- Goals: fast local reads (parquet/json), global filters via `session_state`, simple caching, clean empty states.
- This does not replace the canonical UI on 5555; use `make streamlit-run` to try it separately.

Quick Start
- Run: `make streamlit-run` (default port 5566)
- Open: http://127.0.0.1:5566

Layout
- `src/apps/streamlit/app.py` — entrypoint (sets page config, header, sidebar filters)
- `src/apps/streamlit/_state.py` — initializes `st.session_state` (watchlist, dates)
- `src/apps/streamlit/_data/config.py` — app config (paths, TTL) loaded from env if set
- `src/apps/streamlit/_data/cache.py` — thin wrappers over `st.cache_*`
- `src/apps/streamlit/_data/loader.py` — read latest partitions, forecasts, freshness
- `src/apps/streamlit/_components/*` — simple reusable UI blocks
- `src/apps/streamlit/pages/*` — feature pages (Dashboard, Signals, Deep Dive, Forecasts, Observability)

Configuration
- Environment variables (optional):
  - `AF_DATA_BASE` — base data dir (default: `data`)
  - `AF_CACHE_TTL_SECONDS` — default TTL for cached reads (default: 60)
  - `AF_DEFAULT_WATCHLIST` — comma-separated tickers (default: `SPY,AAPL,NVDA,BTC-USD,GC=F`)

Make Targets
- `make streamlit-run` — runs new Streamlit skeleton at port 5566
- `make streamlit-test` — placeholder (can wire into pytest smoke later)
- `make streamlit-shots` — placeholder for screenshots generation

Notes
- Uses `src/tools/parquet_io.py` helpers to locate latest `dt=*` partitions.
- Falls back to empty states if no partition exists; UI never raises.
- Next steps: swap pandas for polars/duckdb as needed; add charts and tests.

