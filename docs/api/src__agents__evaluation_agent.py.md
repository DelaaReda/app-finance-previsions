# evaluation_agent.py

Evaluation agent

Computes MAE, RMSE and hit ratio for forecasts by agent/provider (if available) or overall.
Writes outputs under `data/evaluation/dt=YYYYMMDD/` as `metrics.json` and `details.parquet`.

Usage: PYTHONPATH=src python -m src.agents.evaluation_agent --horizon 1m --top-n 5

## Function: `compute_metrics`

Signature: `def compute_metrics(...)->dict`

Inputs:
- `horizon`: str = '1m'
- `days_back`: int = 180
Returns: `dict`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
