from __future__ import annotations

import pandas as pd
from typing import Dict, Iterable


def filter_prices(
    prices_by_ticker: Dict[str, pd.DataFrame],
    tickers: Iterable[str] | None,
    start: str | pd.Timestamp | None,
    end: str | pd.Timestamp | None,
    col: str,
) -> pd.DataFrame:
    """Return a tidy DataFrame for the selected tickers and date window.

    - Ignores missing tickers or frames without the requested column.
    - Adds a `ticker` column for plotting.
    - Returns empty DataFrame if nothing is available.
    """
    frames = []
    for t in list(tickers or []):
        df = prices_by_ticker.get(t, pd.DataFrame())
        if df.empty or col not in df.columns:
            continue
        try:
            if 'date' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
                df = df.copy()
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            # Normalize index to datetime for easy filtering
            idx_name = 'date' if 'date' in df.columns else None
            if idx_name:
                df = df.set_index(idx_name)
            if isinstance(df.index, pd.DatetimeIndex):
                if start:
                    df = df[df.index >= pd.to_datetime(start)]
                if end:
                    df = df[df.index <= pd.to_datetime(end)]
            df = df.assign(ticker=t)
            frames.append(df.reset_index())
        except Exception:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

