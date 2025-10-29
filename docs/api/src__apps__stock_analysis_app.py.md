# stock_analysis_app.py

## Function: `get_stock_data`

Signature: `def get_stock_data(...)->Any`

Récupère les données historiques d'un actif (action, indice, future).

Inputs:
- `ticker`: Any
- `period`: Any = '5y'
- `interval`: Any = '1d'
Returns: `Any`

## Function: `get_peer_data`

Signature: `def get_peer_data(...)->Any`

Récupère les données de clôture pour un groupe d'actifs.

Inputs:
- `tickers`: Any
- `period`: Any = '1y'
Returns: `Any`

## Function: `calculate_returns`

Signature: `def calculate_returns(...)->Any`

Calcule les rendements (%) sur différentes périodes (en jours ouvrés).

Inputs:
- `df`: Any
- `periods`: Any
Returns: `Any`

## Function: `calculate_volatility`

Signature: `def calculate_volatility(...)->Any`

Volatilité annualisée (%) calculée sur une fenêtre glissante.

Inputs:
- `df`: Any
- `window`: Any = 20
Returns: `Any`

## Function: `calculate_beta`

Signature: `def calculate_beta(...)->Any`

Coefficient bêta glissant (covariance/variance) d'un actif vs indice.

Inputs:
- `stock_returns`: Any
- `benchmark_returns`: Any
- `window`: Any = 60
Returns: `Any`

## Function: `add_technical_indicators`

Signature: `def add_technical_indicators(...)->Any`

Ajoute des indicateurs techniques au DataFrame (MMS, RSI, MACD, Bollinger, OBV).

Inputs:
- `df`: Any
Returns: `Any`

## Function: `get_company_info`

Signature: `def get_company_info(...)->Any`

Récupère les informations fondamentales de l'émetteur via yfinance.

Inputs:
- `ticker`: Any
Returns: `Any`

## Function: `load_fred_series`

Signature: `def load_fred_series(...)->Any`

Récupère une série temporelle depuis FRED (CSV public) de manière robuste.

- Tente d'utiliser fredgraph.csv avec en-tête "DATE".
- Fallback si l'en-tête diffère (ex. "observation_date" ou première colonne anonyme).
- Convertit proprement les valeurs ('.' -> NaN, to_numeric).

Inputs:
- `series_id`: Any
- `start_date`: Any = None
Returns: `Any`

## Function: `get_fred_data`

Signature: `def get_fred_data(...)->Any`

Récupère plusieurs séries FRED et les agrège dans un DataFrame.

Inputs:
- `series_ids`: Any
- `start_date`: Any = None
Returns: `Any`

## Function: `zscore`

Signature: `def zscore(...)->Any`

Calcule le z-score glissant d'une série.

Inputs:
- `series`: Any
- `window`: Any = 24
Returns: `Any`

## Function: `get_financials`

Signature: `def get_financials(...)->Any`

Récupère états financiers (résultat, bilan, flux de trésorerie).

Inputs:
- `ticker`: Any
Returns: `Any`

## Function: `get_similar_stocks`

Signature: `def get_similar_stocks(...)->Any`

Trouve des actifs similaires par corrélation des rendements.

Inputs:
- `ticker`: Any
- `n`: Any = 5
Returns: `Any`

## Function: `load_stock_data`

Signature: `def load_stock_data(...)->Any`

Inputs:
- `t`: Any
- `p`: Any
Returns: `Any`

## Function: `load_company_info`

Signature: `def load_company_info(...)->Any`

Inputs:
- `t`: Any
Returns: `Any`

## Function: `load_financials_cached`

Signature: `def load_financials_cached(...)->Any`

Inputs:
- `t`: Any
Returns: `Any`

## Function: `load_benchmark_data_cached`

Signature: `def load_benchmark_data_cached(...)->Any`

Inputs:
- `bmk`: Any
- `p`: Any
Returns: `Any`

## Function: `load_similar_stocks_cached`

Signature: `def load_similar_stocks_cached(...)->Any`

Inputs:
- `t`: Any
Returns: `Any`

## Function: `load_macro_indicators`

Signature: `def load_macro_indicators(...)->Any`

Inputs:
- `p`: Any
Returns: `Any`

## Function: `render_stock`

Signature: `def render_stock(...)->None`

Point d'entrée léger pour le hub/tests.
Dans un contexte Streamlit, l'UI ci-dessus sera déjà évaluée à l'import.
En contexte PyTest (st_compat), cet appel est un no-op sûr.

Inputs:
- `default_ticker`: str = 'AAPL'
Returns: `None`

## Function: `render_stock`

Signature: `def render_stock(...)->Any`

Fonction exportable pour afficher l'onglet Action dans le hub.

Inputs:
- `default_ticker`: str = 'AAPL'
Returns: `Any`
