# macro_derivatives_client.py

Macro & Derivatives client (FRED, TradingEconomics, CBOE, CFTC)
- Télécharge, met en cache, normalise et agrège des indicateurs macro et de dérivés.
- Conçu pour cohabiter avec finnews / finviz_client; schemas stables et JSONL-friendly.

Fonctions principales:
- fred_series(series_ids, start=None, end=None) -> dict[str, list[{date,value}]]
- tradingeconomics_calendar(countries=None, start=None, end=None, importance=None) -> list[...]
- cboe_indexes(which=['VIX','VVIX','SKEW']) -> dict[str, {value, change, ts}]
- cftc_cot(symbols=['SPX','NDX',...]) -> dict[symbol, {long, short, net, ts}]
- build_macro_snapshot(...) -> dict avec "macro", "risk", "surprises", "sources_used"

Notes:
- Clés API facultatives (FRED, TradingEconomics) via variables d'env:
  FRED_API_KEY, TE_API_KEY, TE_CLIENT, TE_SECRET
- Tous les appels utilisent un cache local (cache/macro/...) + retries, backoff.

Auteur: toi

## Function: `fred_series`

Signature: `def fred_series(...)->Dict[str, List[Dict[str, Any]]]`

Retourne {series_id: [{date:'YYYY-MM-DD', value:float}, ...]}
Si pas de clé API FRED, on bascule vers CSV public 'fredgraph' (moins fiable mais utile).

Inputs:
- `series_ids`: List[str]
- `start`: Optional[str] = None
- `end`: Optional[str] = None
- `use_cache`: Any = True
Returns: `Dict[str, List[Dict[str, Any]]]`

## Function: `tradingeconomics_calendar`

Signature: `def tradingeconomics_calendar(...)->List[Dict[str, Any]]`

Calendar with fields: {country, category, actual, previous, forecast, date, importance, unit}
Docs: https://developer.tradingeconomics.com

Inputs:
- `countries`: Optional[List[str]] = None
- `start`: Optional[str] = None
- `end`: Optional[str] = None
- `importance`: Optional[int] = None
- `use_cache`: Any = True
- `limit`: int = 1000
Returns: `List[Dict[str, Any]]`

## Function: `cboe_indexes`

Signature: `def cboe_indexes(...)->Dict[str, Dict[str, Any]]`

Récupère VIX, VVIX, SKEW depuis endpoints publics (CSV / JSON)
- VIX CSV example: https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv
- SKEW CSV:       https://cdn.cboe.com/api/global/us_indices/daily_prices/SKEW_History.csv

Inputs:
- `which`: List[str] = ['VIX', 'VVIX', 'SKEW']
- `use_cache`: Any = True
Returns: `Dict[str, Dict[str, Any]]`

## Function: `cftc_cot`

Signature: `def cftc_cot(...)->Dict[str, Dict[str, Any]]`

Retourne {symbol: {long, short, net, ts, market}}
Données agrégées Non-commercials si disponibles.

Inputs:
- `symbols`: List[str] = ['SPX', 'NDX', 'WTI', 'GOLD', 'COPPER', 'EUR', 'JPY']
- `use_cache`: Any = True
Returns: `Dict[str, Dict[str, Any]]`

## Function: `build_macro_snapshot`

Signature: `def build_macro_snapshot(...)->Dict[str, Any]`

Construit un snapshot macro unifié:
- macro: dict de séries clés (last, MoM/YoY)
- rates & spreads: ust2y, ust10y, 2s10s
- risk: vix, vvix, skew, hy_oas
- surprises: événements TE récents (actual-forecast, signe)
- positioning (COT): net non-commercials sur marchés clés

Inputs:
- `fred_ids`: Dict[str, str] = DEFAULT_FRED
- `include_te`: bool = True
- `include_cboe`: bool = True
- `include_cot`: bool = True
- `use_cache`: bool = True
- `lookback_months`: int = 18
Returns: `Dict[str, Any]`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
