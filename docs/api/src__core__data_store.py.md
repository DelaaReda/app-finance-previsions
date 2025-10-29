# data_store.py

## Function: `ensure_parent`

Signature: `def ensure_parent(...)->None`

Inputs:
- `path`: Path
Returns: `None`

## Function: `write_parquet`

Signature: `def write_parquet(...)->Path`

Inputs:
- `df`: pd.DataFrame
- `path`: str | Path
- `**kwargs`: Any
Returns: `Path`

## Function: `have_files`

Signature: `def have_files(...)->bool`

Inputs:
- `glob_pattern`: str
Returns: `bool`

## Function: `query_duckdb`

Signature: `def query_duckdb(...)->pd.DataFrame`

Inputs:
- `sql`: str
Returns: `pd.DataFrame`
