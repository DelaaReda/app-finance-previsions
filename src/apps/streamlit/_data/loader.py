from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from .config import get_config
from .cache import cache_data
from src.tools.parquet_io import latest_partition, read_parquet_latest


def _as_list(x: Optional[Iterable[str] | str]) -> list[str] | None:
    if x is None:
        return None
    if isinstance(x, str):
        return [x]
    return list(x)


@cache_data()
def get_forecasts(tickers: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Load latest forecast final parquet and optionally filter by tickers.

    Returns empty DataFrame if no data.
    """
    cfg = get_config()
    base = cfg.data_base / "forecast"
    df = read_parquet_latest(base, "final.parquet")
    if df is None:
        return pd.DataFrame()
    if tickers:
        tickers = _as_list(tickers)
        if "ticker" in df.columns:
            df = df[df["ticker"].isin(tickers)]
    return df


@cache_data()
def get_partitions_status() -> pd.DataFrame:
    """Return a table of latest known partitions for key domains."""
    cfg = get_config()
    domains = [
        (cfg.data_base / "forecast", "forecast"),
        (cfg.data_base / "macro" / "forecast", "macro_forecast"),
        (cfg.data_base / "quality", "quality"),
        (cfg.data_base / "news", "news"),
    ]
    rows: list[dict] = []
    for path, name in domains:
        part = latest_partition(path)
        rows.append({
            "domain": name,
            "latest": part.name if part else None,
            "path": str(part) if part else None,
        })
    return pd.DataFrame(rows)

