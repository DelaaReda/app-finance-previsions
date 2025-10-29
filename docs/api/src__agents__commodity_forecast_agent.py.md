# commodity_forecast_agent.py

Commodity Forecast Agent

Generates forecasts for commodities (gold, oil, agricultural) using technical indicators,
macro factors (supply/demand, USD strength), and historical patterns.

Outputs: data/forecast/dt=YYYYMMDD/commodities.parquet

## Function: `run_once`

Signature: `def run_once(...)->Path`

Generate commodity forecasts and save to parquet

Inputs:
- (none)
Returns: `Path`

## Function: `main`

Signature: `def main(...)->Any`

CLI entry point

Inputs:
- (none)
Returns: `Any`
