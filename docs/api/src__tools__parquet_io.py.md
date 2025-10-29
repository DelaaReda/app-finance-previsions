# parquet_io.py

## Function: `latest_partition`

Signature: `def latest_partition(...)->Optional[Path]`

Return the latest partition directory under a base path.

Inputs:
- base_dir: path to a folder that contains subfolders named like `dt=YYYYMMDD` or `dt=YYYYMMDDHH`.

Returns:
- Path to the lexicographically last `dt=*` folder, or None if none exists.

Inputs:
- `base_dir`: str | Path
Returns: `Optional[Path]`

## Function: `read_parquet_latest`

Signature: `def read_parquet_latest(...)->Optional[pd.DataFrame]`

Read a Parquet file from the latest partition.

Inputs:
- base_dir: base directory that contains `dt=*` subfolders.
- filename: file name to read within the latest partition (e.g., `final.parquet`).

Returns:
- pandas.DataFrame if the partition and file exist, otherwise None.

Inputs:
- `base_dir`: str | Path
- `filename`: str
Returns: `Optional[pd.DataFrame]`
