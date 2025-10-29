# macro_sector_app.py

## Function: `log_info`

Signature: `def log_info(...)->Any`

Inputs:
- `msg`: Any
Returns: `Any`

## Function: `log_warn`

Signature: `def log_warn(...)->Any`

Inputs:
- `msg`: Any
Returns: `Any`

## Function: `log_error`

Signature: `def log_error(...)->Any`

Inputs:
- `msg`: Any
Returns: `Any`

## Function: `tlog`

Signature: `def tlog(...)->Any`

Décorateur de timing + logging sur les fonctions de fetch/cache.

Inputs:
- `name`: Any = None
Returns: `Any`

## Function: `profile_df`

Signature: `def profile_df(...)->Any`

Inputs:
- `df`: Optional[Union[pd.DataFrame, pd.Series]]
- `name`: str
Returns: `Any`

## Function: `zscore`

Signature: `def zscore(...)->Any`

Inputs:
- `series`: Any
- `win`: Any = 24
Returns: `Any`

## Function: `normalize_fred_key`

Signature: `def normalize_fred_key(...)->Optional[str]`

Valide une clé FRED (32 caractères alphanumériques en minuscules).

Inputs:
- `k`: Optional[str]
Returns: `Optional[str]`

## Function: `load_fred_series`

Signature: `def load_fred_series(...)->pd.DataFrame`

Charge une série FRED robuste :
  1) API JSON officielle (si clé valide)
  2) Fallback CSV fredgraph.csv (sans clé)

Inputs:
- `series_id`: str
- `fred_key`: Optional[str] = None
- `start`: Optional[str] = None
Returns: `pd.DataFrame`

## Function: `get_asset_price`

Signature: `def get_asset_price(...)->Any`

Inputs:
- `symbol`: Any
- `start`: Any = '2010-01-01'
Returns: `Any`

## Function: `get_multi_yf`

Signature: `def get_multi_yf(...)->Any`

Inputs:
- `symbols`: Any
- `start`: Any = '2010-01-01'
Returns: `Any`

## Function: `robust_minmax`

Signature: `def robust_minmax(...)->Any`

Inputs:
- `row`: Any
Returns: `Any`

## Function: `smooth_scores`

Signature: `def smooth_scores(...)->Any`

Inputs:
- `df`: Any
- `ema`: Any = 3
Returns: `Any`

## Function: `hysteresis_picks`

Signature: `def hysteresis_picks(...)->Any`

Inputs:
- `score_df`: Any
- `k`: Any = 3
- `margin`: Any = 0.15
Returns: `Any`

## Function: `set_status`

Signature: `def set_status(...)->Any`

Inputs:
- `name`: str
- `ok`: bool
- `detail`: str = ''
Returns: `Any`

## Function: `call_safely`

Signature: `def call_safely(...)->Any`

Exécute une fonction; enregistre OK/échec dans DATA_STATUS (affiché en UI).

Inputs:
- `_fn`: Any
- `*args`: Any
- `label` (kwonly): str = None
- `**kwargs`: Any
Returns: `Any`

## Function: `render_sources_state`

Signature: `def render_sources_state(...)->Any`

Inputs:
- (none)
Returns: `Any`

## Function: `badge`

Signature: `def badge(...)->Any`

Affiche un badge indiquant l'état d'une source de données

Inputs:
- `available`: bool
- `name`: str
- `fallback`: str = ''
Returns: `Any`

## Function: `fetch_gscpi`

Signature: `def fetch_gscpi(...)->Any`

Charge GSCPI depuis plusieurs miroirs.
Gère les lignes d'en-tête/metadata et CSV non standard.

Inputs:
- (none)
Returns: `Any`

## Function: `fetch_vix_history`

Signature: `def fetch_vix_history(...)->Any`

Indice de volatilité CBOE (VIX) quotidien → pd.Series(name='VIX').

Inputs:
- (none)
Returns: `Any`

## Function: `fetch_gpr`

Signature: `def fetch_gpr(...)->Any`

Indice de risque géopolitique (Iacoviello).
Plusieurs miroirs + arrêt propre si tous échouent.

Inputs:
- (none)
Returns: `Any`

## Function: `fetch_boc_fx`

Signature: `def fetch_boc_fx(...)->Any`

Taux de change Banque du Canada (USD/CAD).

Inputs:
- `series`: Any = 'FXUSDCAD'
Returns: `Any`

## Function: `fetch_eia`

Signature: `def fetch_eia(...)->Any`

Séries EIA (énergie).

Inputs:
- `series_id`: Any
- `api_key`: Any
Returns: `Any`

## Function: `fetch_bls`

Signature: `def fetch_bls(...)->Any`

Bureau of Labor Statistics (ex: séries d’emploi, salaires…).

Inputs:
- `series_ids`: Any
- `api_key`: Any = None
- `start_year`: Any = 2010
Returns: `Any`

## Function: `fetch_gdelt_events`

Signature: `def fetch_gdelt_events(...)->Any`

Proxy de chocs ‘tarifs/guerre’ basé sur le volume d’événements GDELT.

Inputs:
- `days`: Any = 30
Returns: `Any`

## Function: `today_ny`

Signature: `def today_ny(...)->Any`

Inputs:
- (none)
Returns: `Any`

## Function: `fetch_te_calendar`

Signature: `def fetch_te_calendar(...)->Any`

Calendrier des publications économiques (TradingEconomics)

Inputs:
- `d1`: str
- `d2`: str
- `country`: Any = 'United States'
- `client`: Any = 'guest:guest'
Returns: `Any`

## Function: `compute_theme_scores`

Signature: `def compute_theme_scores(...)->Any`

Calcule des scores mensuels par grands thèmes macro, normalisés [-1..1].

Inputs:
- `fred_df`: Any
- `params`: Any
Returns: `Any`

## Function: `sector_scores`

Signature: `def sector_scores(...)->Any`

Score des secteurs = combinaison linéaire (thèmes × sensibilités), puis mise à l’échelle robuste [-5..5].

Inputs:
- `theme_df`: Any
- `sensitivities`: Any
Returns: `Any`

## Function: `backtest_rotation`

Signature: `def backtest_rotation(...)->Any`

Stratégie mensuelle : prendre les K meilleurs secteurs (avec lissage et hystérésis).

Inputs:
- `prices`: Any
- `scores_scaled`: Any
- `top_k`: Any = 3
- `ema`: Any = 3
- `margin`: Any = 0.15
Returns: `Any`

## Function: `render_macro`

Signature: `def render_macro(...)->Any`

Inputs:
- (none)
Returns: `Any`
