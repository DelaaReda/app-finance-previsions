# io_utils.py

Core I/O utilities for financial data processing.
Handles JSONL, parquet, caching, and time-related operations.

## Function: `setup_logging`

Signature: `def setup_logging(...)->logging.Logger`

Configure rotating file logger

Inputs:
- `name`: str = 'finance_analysis'
Returns: `logging.Logger`

## Function: `ensure_dir`

Signature: `def ensure_dir(...)->Path`

Ensure directory exists and return Path object

Inputs:
- `path`: Union[str, Path]
Returns: `Path`

## Function: `read_jsonl`

Signature: `def read_jsonl(...)->List[Dict]`

Read JSONL file and return list of dictionaries

Inputs:
- `path`: Union[str, Path]
Returns: `List[Dict]`

## Function: `write_jsonl`

Signature: `def write_jsonl(...)->None`

Write list of dictionaries to JSONL file

Inputs:
- `data`: List[Dict]
- `path`: Union[str, Path]
Returns: `None`

## Function: `read_parquet`

Signature: `def read_parquet(...)->pd.DataFrame`

Read Parquet file with basic error handling

Inputs:
- `path`: Union[str, Path]
Returns: `pd.DataFrame`

## Function: `write_parquet`

Signature: `def write_parquet(...)->None`

Write DataFrame to Parquet with basic error handling

Inputs:
- `df`: pd.DataFrame
- `path`: Union[str, Path]
Returns: `None`

## Class: `Cache`

Simple file-based cache with TTL support

### Method: `Cache.get`

Signature: `def get(...)->Optional[Any]`

Get value from cache, None if missing or expired

Inputs:
- `key`: str
- `ttl_hours`: Optional[int] = None
Returns: `Optional[Any]`

### Method: `Cache.set`

Signature: `def set(...)->None`

Set cache value with current timestamp

Inputs:
- `key`: str
- `value`: Any
Returns: `None`

## Function: `get_artifacts_dir`

Signature: `def get_artifacts_dir(...)->Path`

Get dated artifacts directory for outputs

Inputs:
- `name`: str
Returns: `Path`

## Function: `ensure_utc`

Signature: `def ensure_utc(...)->datetime`

Ensure datetime is UTC-aware

Inputs:
- `dt`: datetime
Returns: `datetime`

## Function: `parse_iso_date`

Signature: `def parse_iso_date(...)->datetime`

Parse ISO date string to UTC datetime

Inputs:
- `date_str`: str
Returns: `datetime`
