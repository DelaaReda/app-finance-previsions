# data_quality.py

Data Quality Scanner — checks datasets and writes a report.

Scans:
- News parquet (columns, NaNs, duplicates)
- Macro series parquet (presence, recency)
- Prices parquet (positivity, outliers)
- Forecasts parquet (schema, NaNs, ranges)
- Features parquet (presence, numeric columns)
- Events JSON (presence, recency)

Writes: data/quality/dt=YYYYMMDD/report.json
CLI:   python -m src.agents.data_quality --scan

## Function: `scan_news`

Signature: `def scan_news(...)->Dict[str, Any]`

Inputs:
- `days_back`: int = 30
Returns: `Dict[str, Any]`

## Function: `scan_macro`

Signature: `def scan_macro(...)->Dict[str, Any]`

Inputs:
- `recency_days`: int = 7
Returns: `Dict[str, Any]`

## Function: `scan_prices`

Signature: `def scan_prices(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `scan_forecasts`

Signature: `def scan_forecasts(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `scan_features`

Signature: `def scan_features(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `scan_events`

Signature: `def scan_events(...)->Dict[str, Any]`

Inputs:
- `recency_days`: int = 14
Returns: `Dict[str, Any]`

## Function: `scan_all`

Signature: `def scan_all(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `scan_coverage`

Signature: `def scan_coverage(...)->Dict[str, Any]`

Check that prices and selected macro series cover at least min_years.

Inputs:
- `min_years`: int = 5
Returns: `Dict[str, Any]`

## Function: `write_report`

Signature: `def write_report(...)->Path`

Inputs:
- `obj`: Dict[str, Any]
Returns: `Path`

## Function: `main`

Signature: `def main(...)->int`

Inputs:
- `argv`: List[str] | None = None
Returns: `int`
