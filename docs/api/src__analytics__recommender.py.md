# recommender.py

Simple recommender that ranks tickers using forecast outputs and basic features.
Inputs: list of { ticker, features, forecasts: {1w,1m,1y} }
Outputs: sorted list with score and reasons.

## Function: `rank`

Signature: `def rank(...)->List[Dict[str, Any]]`

Inputs:
- `items`: List[Dict[str, Any]]
Returns: `List[Dict[str, Any]]`
