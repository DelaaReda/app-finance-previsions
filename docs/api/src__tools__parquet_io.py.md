# parquet_io.py

## Function: `latest_partition`

Signature: `def latest_partition(...)->Optional[Path]`

Inputs:
- `base_dir`: str | Path
Returns: `Optional[Path]`

## Function: `read_parquet_latest`

Signature: `def read_parquet_latest(...)->Optional[pd.DataFrame]`

Inputs:
- `base_dir`: str | Path
- `filename`: str
Returns: `Optional[pd.DataFrame]`
