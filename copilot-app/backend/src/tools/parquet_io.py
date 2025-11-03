from __future__ import annotations

from pathlib import Path
from typing import Optional
import pandas as pd


def latest_partition(base_dir: str | Path) -> Optional[Path]:
    """
    Return the latest partition directory under a base path.

    Inputs:
    - base_dir: path to a folder that contains subfolders named like `dt=YYYYMMDD` or `dt=YYYYMMDDHH`.

    Returns:
    - Path to the lexicographically last `dt=*` folder, or None if none exists.
    """
    base = Path(base_dir)
    parts = sorted(base.glob("dt=*"))
    return parts[-1] if parts else None


def read_parquet_latest(base_dir: str | Path, filename: str) -> Optional[pd.DataFrame]:
    """
    Read a Parquet file from the latest partition.

    Inputs:
    - base_dir: base directory that contains `dt=*` subfolders.
    - filename: file name to read within the latest partition (e.g., `final.parquet`).

    Returns:
    - pandas.DataFrame if the partition and file exist, otherwise None.
    """
    part = latest_partition(base_dir)
    if not part:
        return None
    fp = part / filename
    if not fp.exists():
        return None
    return pd.read_parquet(fp)
