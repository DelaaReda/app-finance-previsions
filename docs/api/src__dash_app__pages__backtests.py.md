# backtests.py

Backtests page

Reads latest `data/backtest/dt=*/details.parquet` (written by
`src.agents.backtest_agent`) and renders a cumulative Top-N performance
curve (mean realized return per backtest date cumulated over time).

Behaviour:
 - If no parquet found, shows a French empty-state message.
 - Exposes a Plotly line graph with id `backtests-topn-curve` so tests can
   assert its presence.

## Function: `layout`

Signature: `def layout(...)->Any`

Inputs:
- (none)
Returns: `Any`
