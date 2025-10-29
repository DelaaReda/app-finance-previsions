# market_data.py

Thin data access layer for prices, fundamentals, and macro series.

Prefers API keys from environment when available:
- FINNHUB_API_KEY for quotes/fundamentals via Finnhub
- FRED_API_KEY for macro via FRED JSON API

Falls back to yfinance for prices/fundamentals and FRED CSV for macro.
All functions are best-effort and return None/empty on failure.

## Function: `get_price_history`

Signature: `def get_price_history(...)->Optional[pd.DataFrame]`

Fetch OHLCV history using yfinance. Returns DataFrame or None.

Inputs:
- `ticker`: str
- `start`: Optional[str] = None
- `end`: Optional[str] = None
- `interval`: str = '1d'
Returns: `Optional[pd.DataFrame]`

## Function: `get_fundamentals`

Signature: `def get_fundamentals(...)->Dict[str, Any]`

Return a minimal fundamentals dict. Prefer Finnhub, fallback to yfinance.

Inputs:
- `symbol`: str
Returns: `Dict[str, Any]`

## Function: `get_fred_series`

Signature: `def get_fred_series(...)->pd.DataFrame`

Return a single-column DataFrame for a FRED series. Best-effort.

Inputs:
- `series_id`: str
- `start`: Optional[str] = None
Returns: `pd.DataFrame`

## Class: `SnapshotInputs`
