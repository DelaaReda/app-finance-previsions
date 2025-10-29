# phase1_fundamental.py

Phase 1 — Fondamental “pro” (Fair Value dynamique) pour actions US/CA.
Mode DEBUG détaillé activable: --log DEBUG ou PHASE1_DEBUG=1

Dépendances:
    pip install yfinance pandas numpy python-dateutil

## Function: `debug_io`

Signature: `def debug_io(...)->Any`

Decorator: trace les entrées (types/shapes), la durée, et la sortie.
N’affiche le détail que si le logger est en DEBUG.

Inputs:
- `name`: Optional[str] = None
Returns: `Any`

## Class: `HealthRatios`

### Method: `HealthRatios.to_dict`

Signature: `def to_dict(...)->Dict[str, Optional[float]]`

Inputs:
- (none)
Returns: `Dict[str, Optional[float]]`

## Class: `PeerMultiples`

### Method: `PeerMultiples.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `ComparableZScores`

### Method: `ComparableZScores.to_dict`

Signature: `def to_dict(...)->Dict[str, Optional[float]]`

Inputs:
- (none)
Returns: `Dict[str, Optional[float]]`

## Class: `DCFResult`

### Method: `DCFResult.to_dict`

Signature: `def to_dict(...)->Dict[str, Optional[float]]`

Inputs:
- (none)
Returns: `Dict[str, Optional[float]]`

## Class: `FairValueAggregate`

### Method: `FairValueAggregate.to_dict`

Signature: `def to_dict(...)->Dict[str, Optional[float]]`

Inputs:
- (none)
Returns: `Dict[str, Optional[float]]`

## Class: `FundamentalView`

### Method: `FundamentalView.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `convert_to_currency`

Signature: `def convert_to_currency(...)->Optional[float]`

Inputs:
- `value`: Optional[float]
- `from_ccy`: Optional[str]
- `to_ccy`: Optional[str]
Returns: `Optional[float]`

## Function: `load_prices`

Signature: `def load_prices(...)->pd.DataFrame`

OHLCV historiques.

Inputs:
- `ticker`: str
- `period`: str = '3y'
- `interval`: str = '1d'
Returns: `pd.DataFrame`

## Function: `load_fundamentals`

Signature: `def load_fundamentals(...)->Dict[str, pd.DataFrame]`

Inputs:
- `ticker`: str
Returns: `Dict[str, pd.DataFrame]`

## Function: `load_info`

Signature: `def load_info(...)->Dict[str, Any]`

Inputs:
- `ticker`: str
Returns: `Dict[str, Any]`

## Function: `load_rf_rate`

Signature: `def load_rf_rate(...)->Optional[float]`

Inputs:
- (none)
Returns: `Optional[float]`

## Function: `estimate_beta`

Signature: `def estimate_beta(...)->Optional[float]`

Inputs:
- `ticker`: str
- `benchmark`: str = DEFAULT_BENCHMARK
- `period`: str = '3y'
Returns: `Optional[float]`

## Function: `pick_first_index`

Signature: `def pick_first_index(...)->Optional[str]`

Inputs:
- `df`: pd.DataFrame
- `*candidates`: Any
Returns: `Optional[str]`

## Function: `compute_health_ratios`

Signature: `def compute_health_ratios(...)->HealthRatios`

Inputs:
- `ticker`: str
- `fundamentals`: Dict[str, pd.DataFrame]
- `info`: Dict[str, Any]
Returns: `HealthRatios`

## Function: `infer_peers_from_info`

Signature: `def infer_peers_from_info(...)->List[str]`

Inputs:
- `ticker`: str
- `info`: Dict[str, Any]
- `limit`: int = MAX_PEERS
Returns: `List[str]`

## Function: `build_peer_set`

Signature: `def build_peer_set(...)->List[str]`

Inputs:
- `ticker`: str
- `info`: Dict[str, Any]
- `fallback_peers`: Optional[List[str]] = None
Returns: `List[str]`

## Function: `fetch_peer_multiples`

Signature: `def fetch_peer_multiples(...)->pd.DataFrame`

Inputs:
- `peers`: List[str]
Returns: `pd.DataFrame`

## Function: `summarize_peer_multiples`

Signature: `def summarize_peer_multiples(...)->PeerMultiples`

Inputs:
- `df`: pd.DataFrame
Returns: `PeerMultiples`

## Function: `compute_company_multiples`

Signature: `def compute_company_multiples(...)->Dict[str, Optional[float]]`

Inputs:
- `info`: Dict[str, Any]
- `fundamentals`: Dict[str, pd.DataFrame]
Returns: `Dict[str, Optional[float]]`

## Function: `compute_zscores_company_vs_peers`

Signature: `def compute_zscores_company_vs_peers(...)->ComparableZScores`

Inputs:
- `company`: Dict[str, Optional[float]]
- `peers_df`: pd.DataFrame
Returns: `ComparableZScores`

## Function: `fair_value_from_comparables`

Signature: `def fair_value_from_comparables(...)->Optional[float]`

Inputs:
- `info`: Dict[str, Any]
- `peers`: PeerMultiples
Returns: `Optional[float]`

## Function: `dcf_simplified`

Signature: `def dcf_simplified(...)->DCFResult`

Inputs:
- `fundamentals`: Dict[str, pd.DataFrame]
- `info`: Dict[str, Any]
- `years`: int = 5
- `growth_g`: Optional[float] = 0.02
- `wacc`: Optional[float] = None
- `tax_rate`: float = DEFAULT_TAX_RATE
- `g_low`: float = DEFAULT_PERPET_G_MIN
- `g_high`: float = DEFAULT_PERPET_G_MAX
- `wacc_low`: float = DEFAULT_WACC_MIN
- `wacc_high`: float = DEFAULT_WACC_MAX
Returns: `DCFResult`

## Function: `aggregate_fair_value`

Signature: `def aggregate_fair_value(...)->FairValueAggregate`

Inputs:
- `current_price`: Optional[float]
- `fv_cmp`: Optional[float]
- `dcf_res`: DCFResult
Returns: `FairValueAggregate`

## Function: `build_fundamental_view`

Signature: `def build_fundamental_view(...)->FundamentalView`

Inputs:
- `ticker`: str
- `fallback_peers`: Optional[List[str]] = None
- `dcf_years`: int = 5
- `dcf_g`: float = 0.02
- `dcf_wacc`: Optional[float] = None
Returns: `FundamentalView`
