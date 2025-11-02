# src/core/datasets.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

try:
    from tools.parquet_io import latest_partition
except ImportError:
    def latest_partition(base_path: Path) -> Optional[Path]:
        """Fallback: find latest dt= partition"""
        parts = sorted(base_path.glob('dt=*'))
        return parts[-1] if parts else None

PartitionKind = Literal["prices", "macro", "news", "features", "forecast", "quality", "risk"]

@dataclass(frozen=True)
class DatasetLayout:
    base_dir: Path

    @staticmethod
    def default() -> "DatasetLayout":
        return DatasetLayout(base_dir=Path("data"))

    def part_dir(self, kind: PartitionKind, **keys) -> Path:
        """
        Examples:
          data/prices/symbol=AAPL/interval=1d/dt=20251030/
          data/macro/series=CPIAUCSL/dt=20251030/
          data/news/region=US/dt=20251030/
          data/features/table=prices_features_daily/dt=20251030/
        """
        parts = [self.base_dir, kind]
        for k, v in keys.items():
            parts.append(f"{k}={v}")
        return Path(*parts)

    def today_partition(self, kind: PartitionKind, **keys) -> Path:
        d = datetime.utcnow().strftime("%Y%m%d")
        return self.part_dir(kind, **keys) / f"dt={d}"

    def latest(self, kind: PartitionKind, **keys) -> Optional[Path]:
        p = self.part_dir(kind, **keys)
        return latest_partition(p)

def write_parquet_partition(
    df: pd.DataFrame, 
    out_dir: Path, 
    filename: str = "final.parquet", 
    compression: str = "zstd"
) -> Path:
    """Write DataFrame to partitioned Parquet with compression."""
    out_dir.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    fp = out_dir / filename
    pq.write_table(table, fp, compression=compression)
    return fp

def read_parquet_partition(dir_or_file: Path) -> Optional[pd.DataFrame]:
    """Read Parquet partition (directory or file)."""
    if dir_or_file.is_dir():
        fp = dir_or_file / "final.parquet"
    else:
        fp = dir_or_file
    if not fp.exists():
        return None
    return pd.read_parquet(fp)

def append_parquet(
    df: pd.DataFrame, 
    out_dir: Path, 
    filename: str = "append.parquet"
) -> Path:
    """Append DataFrame as timestamped Parquet (for streaming)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime('%H%M%S')
    fp = out_dir / f"{ts}_{filename}"
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, fp, compression="zstd")
    return fp
