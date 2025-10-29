# loader.py

Robust data loading helpers for Dash pages.
- Accept path as str/Path or a callable that returns a Path.
- Return empty structures on missing files, never raise in UI.

## Function: `read_parquet`

Signature: `def read_parquet(...)->pd.DataFrame`

Inputs:
- `path`: str | Path | Callable[[], Path]
Returns: `pd.DataFrame`

## Function: `read_json`

Signature: `def read_json(...)->dict`

Inputs:
- `path`: str | Path | Callable[[], Path]
Returns: `dict`

## Function: `read_jsonl`

Signature: `def read_jsonl(...)->list[dict]`

Inputs:
- `path`: str | Path | Callable[[], Path]
Returns: `list[dict]`
