# backtest_news_impact.py

Backtest: couple news to price moves (event study)

What it does
------------
- Loads your enriched JSONL news (from finnews.py + nlp_enrich.py)
- Extracts (timestamp, ticker(s), sentiment, event_class, relevance)
- Fetches historical OHLCV via yfinance (with a tiny on-disk cache)
- Computes abnormal returns around each article date using a market model baseline
- Aggregates CARs by sentiment bucket / event class / source / region
- Outputs:
  * per_event.csv         : one row per (article,ticker) with AR/CAR
  * aggregates.csv        : grouped stats (mean/median t-stats)
  * diagnostics.json      : counts, data coverage, warnings
  * (optional) PNG plots  : average CAR curves by bucket

CLI Examples
------------
python backtest_news_impact.py   --news data/news_enriched.jsonl   --index SPY   --window -1,1 --post 5   --bucket sentiment --min_relevance 0.3

python backtest_news_impact.py   --news data/news_enriched.jsonl   --index ^GSPTSE --window -1,1 --post 3 --region CA --sector_map data/ticker_sector.csv

Notes
-----
- Requires: pandas, numpy, yfinance, scipy, matplotlib (optional for plots)
- Internet access is needed at runtime for price fetches unless cached.
- Timestamps are assumed UTC in the input JSONL (finnews.py already outputs ISO UTC).
- Trading-day alignment: we compute D0 as the first market session at/after the article time
  (using daily bars). For higher precision you can later switch to intraday data.

## Function: `parse_window`

Signature: `def parse_window(...)->Tuple[int, int]`

Parse window like "-1,1" -> (-1, 1)

Inputs:
- `s`: str
Returns: `Tuple[int, int]`

## Function: `ensure_tz_utc`

Signature: `def ensure_tz_utc(...)->datetime`

Inputs:
- `ts`: datetime
Returns: `datetime`

## Function: `load_news`

Signature: `def load_news(...)->List[Article]`

Inputs:
- `jsonl_path`: str
- `region_filter`: Optional[str] = None
- `min_relevance`: Optional[float] = None
- `min_abs_sent`: Optional[float] = None
- `max_age_days`: Optional[int] = None
Returns: `List[Article]`

## Class: `PriceCache`

### Method: `PriceCache.path`

Signature: `def path(...)->str`

Inputs:
- `ticker`: str
Returns: `str`

### Method: `PriceCache.get`

Signature: `def get(...)->Optional[pd.DataFrame]`

Inputs:
- `ticker`: str
Returns: `Optional[pd.DataFrame]`

### Method: `PriceCache.set`

Signature: `def set(...)->None`

Inputs:
- `ticker`: str
- `df`: pd.DataFrame
Returns: `None`

## Function: `fetch_daily_prices`

Signature: `def fetch_daily_prices(...)->pd.DataFrame`

Inputs:
- `ticker`: str
- `start`: datetime
- `end`: datetime
- `cache`: PriceCache
Returns: `pd.DataFrame`

## Class: `EventConfig`

## Function: `nearest_trading_day`

Signature: `def nearest_trading_day(...)->pd.Timestamp`

Inputs:
- `df`: pd.DataFrame
- `ts`: datetime
- `align_to_open`: bool = True
Returns: `pd.Timestamp`

## Function: `compute_market_model_AR`

Signature: `def compute_market_model_AR(...)->Tuple[pd.DataFrame, Dict[str, float]]`

Inputs:
- `stock`: pd.Series
- `market`: pd.Series
- `event_loc`: int
- `pre`: int
- `post`: int
- `est_len`: int
Returns: `Tuple[pd.DataFrame, Dict[str, float]]`

## Function: `make_daily_returns`

Signature: `def make_daily_returns(...)->pd.Series`

Inputs:
- `df`: pd.DataFrame
Returns: `pd.Series`

## Function: `run_backtest`

Signature: `def run_backtest(...)->None`

Inputs:
- `news_path`: str
- `index_ticker`: str
- `out_dir`: str
- `window_pre`: int
- `window_post`: int
- `est_days`: int
- `min_relevance`: Optional[float]
- `min_abs_sent`: Optional[float]
- `region`: Optional[str]
- `plot`: bool
- `cache_dir`: str
Returns: `None`
