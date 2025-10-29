# ml_baseline.py

Simple ML baseline for next-horizon returns using Ridge regression on
recent price-based features. Designed to run fast on a single ticker.

Features (latest day):
- r_5, r_21, r_63: past returns over 5/21/63 trading days
- vol_21: 21-day realized volatility

Target:
- forward horizon return over H days (H in {5,21,252} for 1w/1m/1y)

Returns predicted return (float) and a crude confidence (0..1) based on
sample size and out-of-sample R^2 if available.

## Function: `ml_predict_next_return`

Signature: `def ml_predict_next_return(...)->Tuple[Optional[float], float]`

Inputs:
- `ticker`: str
- `horizon`: str = '1m'
Returns: `Tuple[Optional[float], float]`
