# deep_dive_logic.py

## Function: `filter_prices`

Signature: `def filter_prices(...)->pd.DataFrame`

Return a tidy DataFrame for the selected tickers and date window.

- Ignores missing tickers or frames without the requested column.
- Adds a `ticker` column for plotting.
- Returns empty DataFrame if nothing is available.

Inputs:
- `prices_by_ticker`: Dict[str, pd.DataFrame]
- `tickers`: Iterable[str] | None
- `start`: str | pd.Timestamp | None
- `end`: str | pd.Timestamp | None
- `col`: str
Returns: `pd.DataFrame`
