# phase2_technical.py

Phase 2 — Analyse Technique & Backtests (actions US/CA, daily par défaut)

Dépendances:
    pip install yfinance pandas numpy ta

Fonctions clés:
- load_prices() : OHLCV via yfinance
- compute_indicators() : ajoute un large set d'indicateurs
- technical_signals() : signaux élémentaires + score composite
- detect_regime() : Bull/Bear/Range + régime de volatilité
- risk_stats() : vol annualisée, VaR(95), max drawdown
- backtest() : moteur vectorisé avec R:R, stops, trailing, slippage, fees
- walk_forward_backtest() : évalue la robustesse par fenêtres temporelles

Les sorties utilisent des dataclasses (sérialisables en dict).

Auteurs: toi + IA (2025)
Licence: MIT (à adapter)

## Class: `IndicatorSet`

### Method: `IndicatorSet.to_frame`

Signature: `def to_frame(...)->pd.DataFrame`

Inputs:
- (none)
Returns: `pd.DataFrame`

### Method: `IndicatorSet.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `TechnicalSignals`

### Method: `TechnicalSignals.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `RegimeInfo`

### Method: `RegimeInfo.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `RiskStats`

### Method: `RiskStats.to_dict`

Signature: `def to_dict(...)->Dict[str, Optional[float]]`

Inputs:
- (none)
Returns: `Dict[str, Optional[float]]`

## Class: `TradeResult`

### Method: `TradeResult.to_dict`

Signature: `def to_dict(...)->Dict[str, float]`

Inputs:
- (none)
Returns: `Dict[str, float]`

## Class: `BacktestReport`

### Method: `BacktestReport.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `WalkForwardReport`

### Method: `WalkForwardReport.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `load_prices`

Signature: `def load_prices(...)->pd.DataFrame`

Télécharge OHLCV et nettoie l'index (timezone-naive).

Inputs:
- `ticker`: str
- `period`: str = DEFAULT_PERIOD
- `interval`: str = DEFAULT_INTERVAL
Returns: `pd.DataFrame`

## Function: `compute_indicators`

Signature: `def compute_indicators(...)->IndicatorSet`

Ajoute un large set d'indicateurs dans un DataFrame unique.
Colonnes ajoutées (extrait):
  SMA_20/50/200, EMA_12/26, RSI_14, MACD/Signal/Hist,
  Stoch_%K/%D, ADX_14, ATR_14, BB_Upper/Middle/Lower,
  Keltner_* , Donchian_20_Up/Down, OBV, ROC_63, Volatility_20,
  Trend_200_slope (lignearly regressed), etc.

Inputs:
- `px`: pd.DataFrame
Returns: `IndicatorSet`

## Function: `technical_signals`

Signature: `def technical_signals(...)->TechnicalSignals`

Crée un score composite (-1..+1) basé sur:
  - Mom short/mid (RSI, MACD, EMA12>EMA26, SMA20>SMA50)
  - Trend long (Close>SMA200, slope200>0)
  - Breakout/Range (Donchian, Bollinger position)
  - Volatility filter (ADX/ATR)

Inputs:
- `ind`: IndicatorSet
Returns: `TechnicalSignals`

## Function: `detect_regime`

Signature: `def detect_regime(...)->RegimeInfo`

Inputs:
- `ind`: IndicatorSet
Returns: `RegimeInfo`

## Function: `risk_stats`

Signature: `def risk_stats(...)->RiskStats`

Inputs:
- `px`: pd.DataFrame
Returns: `RiskStats`

## Function: `backtest`

Signature: `def backtest(...)->BacktestReport`

Backtest vectorisé daily:
  - 'rules' -> signal brut (-1/0/1)
  - stops/trailing -> position
  - vol targeting / kelly -> levier
  - coûts appliqués à chaque rotation

Inputs:
- `ind`: IndicatorSet
- `rules`: Dict[str, Any]
- `initial_equity`: float = 100000.0
- `fee_bps`: float = 1.0
- `slippage_bps`: float = 1.0
- `sl_pct`: Optional[float] = None
- `tp_pct`: Optional[float] = None
- `atr_mult_trail`: Optional[float] = None
- `vol_target_ann`: Optional[float] = None
- `kelly_frac`: Optional[float] = None
Returns: `BacktestReport`

## Function: `walk_forward_backtest`

Signature: `def walk_forward_backtest(...)->WalkForwardReport`

Split temporel en n_folds (consécutifs), backtest sur chaque fold.

Inputs:
- `ind`: IndicatorSet
- `rules`: Dict[str, Any]
- `n_folds`: int = 3
- `min_points_per_fold`: int = 252
- `**bt_kwargs`: Any
Returns: `WalkForwardReport`

## Function: `compute_technical_features`

Signature: `def compute_technical_features(...)->Dict[str, Any]`

Compute technical features for a given ticker using the build_technical_view function.
This is a wrapper function to match the expected signature from app.py.

Args:
    ticker (str): Stock ticker symbol
    window (int): Lookback window in days (default: 180)

Returns:
    Dict: Technical features suitable for conversion to dict

Inputs:
- `ticker`: str
- `window`: int = 180
Returns: `Dict[str, Any]`

## Function: `build_technical_view`

Signature: `def build_technical_view(...)->Dict[str, Any]`

Pipeline rapide (sans backtest):
  - charge prix
  - compute_indicators
  - technical_signals + detect_regime + risk_stats
Retourne un dict compact prêt à afficher/logguer.

Inputs:
- `ticker`: str
- `period`: str = DEFAULT_PERIOD
- `interval`: str = DEFAULT_INTERVAL
Returns: `Dict[str, Any]`
