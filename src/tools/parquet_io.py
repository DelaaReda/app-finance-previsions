from __future__ import annotations

from pathlib import Path
from typing import Optional
import pandas as pd


def latest_partition(base_dir: str | Path) -> Optional[Path]:
    base = Path(base_dir)
    parts = sorted(base.glob("dt=*"))
    return parts[-1] if parts else None


def read_parquet_latest(base_dir: str | Path, filename: str) -> Optional[pd.DataFrame]:
    part = latest_partition(base_dir)
    if not part:
        return None
    fp = part / filename
    if not fp.exists():
        return None
    return pd.read_parquet(fp)

