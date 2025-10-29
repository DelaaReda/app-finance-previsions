# forecaster.py

Lightweight forecasting helpers (baseline + sentiment blend) for 1w/1m/1y.
Designed to work without heavy dependencies and to integrate with
analytics.market_intel outputs.

## Class: `ForecastResult`

### Method: `ForecastResult.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `forecast_ticker`

Signature: `def forecast_ticker(...)->ForecastResult`

Baseline forecast using SMA structure and light sentiment blend.

Inputs:
- `ticker`: str
- `horizon`: str = '1m'
- `features`: Optional[Dict[str, Any]] = None
Returns: `ForecastResult`
