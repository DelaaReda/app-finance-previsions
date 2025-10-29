# backtest_agent.py

Backtest agent

Computes a Top-N basket realized-return time series from latest forecasts and cached prices
and writes outputs under `data/backtest/dt=YYYYMMDD/`:
- details.parquet (per-date/per-ticker realized returns)
- summary.json (aggregate metrics)

Usage: PYTHONPATH=src python -m src.agents.backtest_agent --horizon 1m --top-n 5

## Function: `run_backtest`

Signature: `def run_backtest(...)->dict`

Inputs:
- `horizon`: str = '1m'
- `top_n`: int = 5
- `days_back`: int = 180
Returns: `dict`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
