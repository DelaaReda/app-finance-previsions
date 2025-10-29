# finnews.py

Monolithic Financial News Module (personal/pro-grade)
- Unified schema
- Multi-region & sector sources (FR/DE/US/CA/INTL/GEO)
- RSS/Atom ingest + normalize + dedup
- Enrichment: lang detect -> translate (noop fallback) -> summarize -> entities -> event/sector tags -> sentiment
- Search: full text + boolean (AND/OR/NOT) + filters (date/window/region/source/lang/sector/event/ticker)
- Signals: aggregated features per ticker/sector for modeling (phase4/phase5)
- Quick backtest: align daily features with returns (needs price loader hook)
- CLI: regions, window, query, company/aliases/ticker, per_source_cap, limit, jsonl/pretty

Author: you

## Function: `now_utc`

Signature: `def now_utc(...)->dt.datetime`

Inputs:
- (none)
Returns: `dt.datetime`

## Function: `parse_date`

Signature: `def parse_date(...)->Optional[dt.datetime]`

Inputs:
- `d`: Any
Returns: `Optional[dt.datetime]`

## Function: `strip_html`

Signature: `def strip_html(...)->str`

Inputs:
- `txt`: str
Returns: `str`

## Function: `sha256`

Signature: `def sha256(...)->str`

Inputs:
- `s`: str
Returns: `str`

## Function: `domain_of`

Signature: `def domain_of(...)->str`

Inputs:
- `url`: str
Returns: `str`

## Function: `guess_lang`

Signature: `def guess_lang(...)->str`

Inputs:
- `text`: str
- `url`: str = ''
Returns: `str`

## Function: `bool_query_match`

Signature: `def bool_query_match(...)->bool`

Simple boolean parser for queries like:
"BRICS OR oil", "Ukraine AND sanctions", "chip NOT Nvidia"

Inputs:
- `q`: str
- `text`: str
Returns: `bool`

## Class: `NewsItem`

## Function: `list_sources`

Signature: `def list_sources(...)->List[str]`

Inputs:
- `regions`: List[str]
Returns: `List[str]`

## Function: `fetch_feed`

Signature: `def fetch_feed(...)->List[Dict[str, Any]]`

Enhanced RSS feed fetching with robust error handling and headers.

Inputs:
- `url`: str
- `per_source_cap`: Optional[int] = None
- `timeout`: int = 30
Returns: `List[Dict[str, Any]]`

## Function: `in_window`

Signature: `def in_window(...)->bool`

window: '1h','6h','12h','24h','48h','last_day','last_week','last_month', or 'all'

Inputs:
- `published_iso`: str
- `window`: str
Returns: `bool`

## Function: `filter_items`

Signature: `def filter_items(...)->List[NewsItem]`

Inputs:
- `items`: List[NewsItem]
- `query`: str = ''
- `window`: str = 'last_week'
- `regions`: Optional[List[str]] = None
- `sources_substr`: Optional[List[str]] = None
- `languages`: Optional[List[str]] = None
- `sectors`: Optional[List[str]] = None
- `events`: Optional[List[str]] = None
- `tickers`: Optional[List[str]] = None
Returns: `List[NewsItem]`

## Function: `run_pipeline`

Signature: `def run_pipeline(...)->List[NewsItem]`

Inputs:
- `regions`: List[str]
- `window`: str
- `query`: str = ''
- `company`: Optional[str] = None
- `aliases`: Optional[List[str]] = None
- `tgt_ticker`: Optional[str] = None
- `per_source_cap`: Optional[int] = None
- `limit`: int = 100
Returns: `List[NewsItem]`

## Function: `build_news_features`

Signature: `def build_news_features(...)->Dict[str, Dict[str, float]]`

Aggregate simple features per ticker for modeling stage:
  - count, mean_sentiment, pos_ratio, neg_ratio, event flags, sector counts, novelty (unique sources)
Return: {ticker: {feature: value}}

Inputs:
- `items`: List[NewsItem]
- `target_ticker`: Optional[str] = None
- `window`: str = 'last_week'
Returns: `Dict[str, Dict[str, float]]`

## Function: `price_loader_stub`

Signature: `def price_loader_stub(...)->Optional[Any]`

Replace this by your real price loader (e.g., yfinance, polygon, local DB).
Must return DataFrame with columns: ['close'] indexed by date (UTC naive ok).

Inputs:
- `ticker`: str
- `start`: str
- `end`: str
Returns: `Optional[Any]`

## Function: `align_news_with_returns`

Signature: `def align_news_with_returns(...)->Optional[Any]`

Inputs:
- `items`: List[NewsItem]
- `ticker`: str
- `horizon_days`: int = 1
- `loader`: Any = price_loader_stub
Returns: `Optional[Any]`

## Function: `save_jsonl`

Signature: `def save_jsonl(...)->Any`

Inputs:
- `items`: List[NewsItem]
- `path`: str
Returns: `Any`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
