# stock_utils.py

Simple stock utilities for ticker mapping and validation.

## Function: `guess_ticker`

Signature: `def guess_ticker(...)->str`

Simple heuristic to guess ticker from company name.
This is a basic implementation - in production you'd want a proper mapping database.

Inputs:
- `company_name`: str
Returns: `str`

## Function: `fetch_price_history`

Signature: `def fetch_price_history(...)->Optional[pd.DataFrame]`

Fetch historical price data for a given ticker via yfinance.
Returns OHLCV DataFrame or None if not found.

Inputs:
- `ticker`: str
- `start_date`: str
- `end_date`: str
Returns: `Optional[pd.DataFrame]`
