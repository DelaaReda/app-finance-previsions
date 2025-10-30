# src/core/datasets.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal, Dict

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from tools.parquet_io import latest_partition

PartitionKind = Literal["prices", "macro", "news", "features"]

@dataclass(frozen=True)
class DatasetLayout:
    base_dir: Path

    @staticmethod
    def default() -> "DatasetLayout":
        return DatasetLayout(base_dir=Path("data"))

    def part_dir(self, kind: PartitionKind, **keys) -> Path:
        """
        price example:
          data/prices/symbol=AAPL/interval=1d/dt=20251029/
        macro example:
          data/macro/series=CPIAUCSL/dt=20251029/
        news example:
          data/news/region=US/dt=20251029/
        features example:
          data/features/table=prices_features_daily/dt=20251029/
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

def write_parquet_partition(df: pd.DataFrame, out_dir: Path, filename: str = "final.parquet", compression: str = "zstd") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=True)
    fp = out_dir / filename
    pq.write_table(table, fp, compression=compression)
    return fp

def read_parquet_partition(dir_or_file: Path) -> Optional[pd.DataFrame]:
    if dir_or_file.is_dir():
        fp = dir_or_file / "final.parquet"
    else:
        fp = dir_or_file
    if not fp.exists():
        return None
    return pd.read_parquet(fp)

def append_parquet(df: pd.DataFrame, out_dir: Path, filename: str = "append.parquet") -> Path:
    """Append simple: écrit un fichier par append; DuckDB consolidera."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fp = out_dir / f"{datetime.utcnow().strftime('%H%M%S')}_{filename}"
    table = pa.Table.from_pandas(df, preserve_index=True)
    pq.write_table(table, fp, compression="zstd")
    return fp