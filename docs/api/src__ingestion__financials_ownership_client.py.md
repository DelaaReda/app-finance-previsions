# financials_ownership_client.py

Financials & Ownership client (Yahoo + SEC EDGAR: submissions / 10-K/10-Q/8-K / Form 4 / 13F)
- Télécharge, met en cache, normalise et agrège données 'fundamentals', 'insiders' et 'institutionnels'.
- Conçu pour cohabiter avec finnews / macro_derivatives_client; schémas stables et JSONL-friendly.

Fonctions principales:
- yahoo_snapshot(ticker) -> dict (price, mcap, pe, beta, sector, industry, calendar, dividends)
- yahoo_options_chain(ticker, expiry=None) -> dict(calls=[...], puts=[...], expiries=[...])
- sec_submissions(cik_or_ticker) -> dict (company profile + derniers filings)
- sec_filings_index(cik_or_ticker, forms=['10-K','10-Q','8-K'], limit=100) -> list[...]
- sec_form4_insiders(cik_or_ticker, limit=200) -> dict(transactions=[...], aggregates={...})
- sec_13f_holdings(cik_or_ticker, limit_filings=1) -> dict(filings=[...], holdings=[...])
- build_ownership_snapshot(ticker) -> dict unifié (yahoo, filings, insiders, 13F, options meta)

Notes:
- Aucune clé obligatoire. Respecte les bonnes pratiques SEC (User-Agent).
- Cache local dans cache/ownership/ + retries/backoff.

Auteur: toi

## Function: `yahoo_snapshot`

Signature: `def yahoo_snapshot(...)->Dict[str, Any]`

Essaye yfinance d'abord; sinon fallback à parsing HTML light de la 'quoteSummary' page.
Retour: dict avec price, market_cap, pe, beta, sector, industry, dividend_yield, earnings_dates, short_interest (best-effort)

Inputs:
- `ticker`: str
- `use_cache`: Any = True
Returns: `Dict[str, Any]`

## Function: `yahoo_options_chain`

Signature: `def yahoo_options_chain(...)->Dict[str, Any]`

Retourne {calls:[...], puts:[...], expiries:[...]} avec champs: strike, lastPrice, bid, ask, volume, openInterest, impliedVolatility
- Avec yfinance: simple.
- Fallback HTML (best effort) si yfinance absent (retourne expiries uniquement).
expiry: 'YYYY-MM-DD' optionnelle; si None -> prochaine échéance.

Inputs:
- `ticker`: str
- `expiry`: Optional[str] = None
- `use_cache`: Any = True
Returns: `Dict[str, Any]`

## Function: `sec_submissions`

Signature: `def sec_submissions(...)->Dict[str, Any]`

data.sec.gov/submissions/CIK##########.json
Si un ticker est donné: le même endpoint accepte `CIK##########` uniquement → on détecte via map 'tickers' retournée par SEC si dispo.

Inputs:
- `cik_or_ticker`: str
- `use_cache`: Any = True
Returns: `Dict[str, Any]`

## Function: `sec_filings_index`

Signature: `def sec_filings_index(...)->List[Dict[str, Any]]`

A partir de submissions.json: reconstruit tableau des filings récents et filtre par 'forms'.

Inputs:
- `cik_or_ticker`: str
- `forms`: List[str] = ['10-K', '10-Q', '8-K']
- `limit`: int = 100
- `use_cache`: Any = True
Returns: `List[Dict[str, Any]]`

## Function: `sec_form4_insiders`

Signature: `def sec_form4_insiders(...)->Dict[str, Any]`

Retourne {transactions:[...], aggregates:{window_30d:{buys, sells, net_shares, net_value}, window_90d:...}}
NB: Sans suivre chaque 'primaryDoc.xml', on reste best-effort; pour la plupart des cas, l'Atom suffit pour signaux grossiers.

Inputs:
- `cik_or_ticker`: str
- `limit`: int = 200
- `use_cache`: Any = True
Returns: `Dict[str, Any]`

## Function: `sec_13f_holdings`

Signature: `def sec_13f_holdings(...)->Dict[str, Any]`

Liste les dernières 13F-HR et agrège le(s) infoTable en un tableau 'holdings'.

Inputs:
- `cik_or_ticker`: str
- `limit_filings`: int = 1
- `use_cache`: Any = True
Returns: `Dict[str, Any]`

## Function: `build_ownership_snapshot`

Signature: `def build_ownership_snapshot(...)->Dict[str, Any]`

assemble: yahoo (price/funda), options expiries, sec filings head, insiders (Form4 agg), 13F last

Inputs:
- `ticker`: str
- `use_cache`: Any = True
Returns: `Dict[str, Any]`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
