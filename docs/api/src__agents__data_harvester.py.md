# data_harvester.py

Data Harvester Agent — 24/7 ingestion and investigations.

Capabilities
- Periodic tasks (news, macro, prices/fundamentals) with best‑effort retries
- Backfill historical news (up to 1y) when API keys allow (Tavily)
- Investigation reports: macro anomalies → web research → IA summary (econ_llm_agent)

Usage examples
- One cycle:      python -m src.agents.data_harvester --once
- Daemon (loop):  python -m src.agents.data_harvester --daemon --interval 1800
- Backfill news:  python -m src.agents.data_harvester --backfill-news-days 365 --query "gold OR mining"

Notes
- Writes Parquet under data/* using core.data_store
- Stores last run state in data/state/harvester_state.json

## Function: `harvest_news_recent`

Signature: `def harvest_news_recent(...)->int`

Inputs:
- `regions`: List[str]
- `watchlist`: List[str]
- `query`: str = ''
- `window`: str = '24h'
- `limit`: int = 300
Returns: `int`

## Function: `backfill_news`

Signature: `def backfill_news(...)->int`

Backfill older news using Tavily if available; fallback to finnews all-window queries.

Writes parquet batches under data/news/dt=YYYY-MM-DD.

Inputs:
- `years`: float = 1.0
- `topic_queries`: Optional[List[str]] = None
Returns: `int`

## Function: `update_macro`

Signature: `def update_macro(...)->int`

Inputs:
- `series_ids`: Optional[List[str]] = None
Returns: `int`

## Function: `update_prices_and_fundamentals`

Signature: `def update_prices_and_fundamentals(...)->int`

Inputs:
- `tickers`: List[str]
Returns: `int`

## Function: `generate_upcoming_events`

Signature: `def generate_upcoming_events(...)->List[Dict[str, Any]]`

Inputs:
- `days_ahead`: int = 14
Returns: `List[Dict[str, Any]]`

## Function: `investigate_macro`

Signature: `def investigate_macro(...)->Dict[str, Any]`

Produce a concise investigation report combining macro deltas and a news brief.

Inputs:
- `theme`: str = 'gold miners & macro context'
Returns: `Dict[str, Any]`

## Function: `discover_topics_via_llm`

Signature: `def discover_topics_via_llm(...)->List[str]`

Use econ_llm_agent (g4f-backed) to propose search queries given macro + watchlist.

Returns a list of short query strings (<= 10).

Inputs:
- `watchlist`: List[str]
Returns: `List[str]`

## Function: `run_once`

Signature: `def run_once(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `daemon_loop`

Signature: `def daemon_loop(...)->None`

Inputs:
- `interval_seconds`: int = 1800
Returns: `None`
