# finviz_client.py

Finviz client (scrape + normalize) — conçu pour fonctionner conjointement avec finnews:
- Company snapshot (ratios, ownership, short interest, profile…)
- Insider trades / Latest filings
- Options chain (list view, by expiry)
- News (global and per ticker)
- Futures dashboards (quotes/performance/charts) across categories

Robustesse:
- Cache HTML local (cache/finviz/{sha1}.html)
- User-Agent rotation, backoff, retries, timeout
- Parse tolérant (BS4), défensif (None-safe), schéma JSON stable

Sorties (schemas JSON-friendly):
- Company: {ticker, name, sector, industry, country, market, metrics{...}, ownership{...}, short{...}, links{...}}
- Insider: [{insider, relation, date, transaction, shares, price, value, link}]
- Filings: [{title, date, form, link}]
- Options: {ticker, expiry, calls:[...], puts:[...]}
- News: [{ts, source, title, link, tickers:[], tags:{...}, summary:...}]
- Futures: {category, timeframe, rows: [{symbol, name, price, change, pct, vol, oi, link}]}

Auteur: toi

## Function: `company_snapshot`

Signature: `def company_snapshot(...)->Dict[str, Any]`

Parse finviz quote main page for snapshot ratios/ownership/short/links etc.
Example URL: https://finviz.com/quote.ashx?t=AAPL&p=w

Inputs:
- `ticker`: str
- `use_cache`: Any = True
Returns: `Dict[str, Any]`

## Function: `insider_trades`

Signature: `def insider_trades(...)->List[Dict[str, Any]]`

Parse insider trades table (if present).

Inputs:
- `ticker`: str
- `use_cache`: Any = True
Returns: `List[Dict[str, Any]]`

## Function: `latest_filings`

Signature: `def latest_filings(...)->List[Dict[str, Any]]`

Parse 'Latest Filings' tab list.

Inputs:
- `ticker`: str
- `use_cache`: Any = True
Returns: `List[Dict[str, Any]]`

## Function: `options_chain`

Signature: `def options_chain(...)->Dict[str, Any]`

Fetch options list view (calls/puts) for a given expiry if provided.
- expiry format like '2025-09-19' (as seen in finviz)
- returns {ticker, expiry, calls:[...], puts:[...]}

Inputs:
- `ticker`: str
- `expiry`: Optional[str] = None
- `use_cache`: Any = True
Returns: `Dict[str, Any]`

## Function: `news`

Signature: `def news(...)->List[Dict[str, Any]]`

Finviz news feed (global or per ticker)
- Global: https://finviz.com/news.ashx?v=2
- Per ticker: https://finviz.com/quote.ashx?t=AAPL (news panel)

Inputs:
- `ticker`: Optional[str] = None
- `use_cache`: Any = True
- `limit`: int = 200
Returns: `List[Dict[str, Any]]`

## Function: `futures`

Signature: `def futures(...)->Dict[str, Any]`

Scrape futures dashboard by category:
  https://finviz.com/futures_{tab}.ashx?p={timeframe}
Then pick the tab for category (Metals, Energy, ...). We normalize each tile row.

Returns: {category, timeframe, tab, rows:[{symbol,name,price,change,pct,vol,oi,link}]}

Inputs:
- `category`: Optional[str] = None
- `timeframe`: str = 'w'
- `tab`: str = 'quotes'
- `use_cache`: Any = True
Returns: `Dict[str, Any]`

## Class: `FinvizCompany`

### Method: `FinvizCompany.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `fetch_company_all`

Signature: `def fetch_company_all(...)->FinvizCompany`

Inputs:
- `ticker`: str
- `expiry`: Optional[str] = None
- `include_news`: bool = True
- `use_cache`: Any = True
Returns: `FinvizCompany`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
