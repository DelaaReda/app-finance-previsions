"""
Massive.com REST client helpers.
Best-effort wrappers with simple rate limiting for low-tier plans.
"""
from __future__ import annotations

import os
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

_LAST_CALL_TS = 0.0
_MIN_INTERVAL_SEC = float(os.getenv("MASSIVE_MIN_INTERVAL_SEC", "12.5"))


def _sleep_rate_limit() -> None:
    global _LAST_CALL_TS
    if _MIN_INTERVAL_SEC <= 0:
        return
    now = time.time()
    wait = _MIN_INTERVAL_SEC - (now - _LAST_CALL_TS)
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL_TS = time.time()


def _get_client():
    try:
        from massive import RESTClient
    except Exception as exc:
        raise RuntimeError("massive client not installed") from exc
    api_key = os.getenv("MASSIVE_API_KEY") or os.getenv("MASSIVE_KEY")
    if api_key:
        return RESTClient(api_key)
    return RESTClient()


def _ts_from_agg(item: Any) -> Optional[int]:
    # Massive agg objects typically expose timestamp (ms) as .timestamp or .t
    for attr in ("timestamp", "t"):
        if hasattr(item, attr):
            v = getattr(item, attr)
            if isinstance(v, (int, float)):
                return int(v)
    return None


def _get_attr(item: Any, *names: str) -> Optional[float]:
    for name in names:
        if hasattr(item, name):
            v = getattr(item, name)
            if v is None:
                return None
            try:
                return float(v)
            except Exception:
                return None
    return None


def list_aggs_daily(
    ticker: str,
    start: str,
    end: str,
    limit: int = 50000,
) -> pd.DataFrame:
    """
    Fetch daily aggregates (OHLCV) for a ticker between start and end dates.
    Returns a DataFrame indexed by Date with Open/High/Low/Close/Volume.
    """
    client = _get_client()
    _sleep_rate_limit()
    aggs: List[Any] = []
    for a in client.list_aggs(
        ticker=ticker,
        multiplier=1,
        timespan="day",
        from_=start,
        to=end,
        limit=limit,
    ):
        aggs.append(a)

    if not aggs:
        return pd.DataFrame()

    rows = []
    for a in aggs:
        ts = _ts_from_agg(a)
        if ts is None:
            continue
        dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).replace(tzinfo=None)
        row = {
            "Date": dt,
            "Open": _get_attr(a, "open", "o"),
            "High": _get_attr(a, "high", "h"),
            "Low": _get_attr(a, "low", "l"),
            "Close": _get_attr(a, "close", "c"),
            "Volume": _get_attr(a, "volume", "v"),
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).dropna(subset=["Date"]).set_index("Date").sort_index()
    return df


def get_snapshot_ticker(market: str, ticker: str) -> Any:
    client = _get_client()
    _sleep_rate_limit()
    return client.get_snapshot_ticker(market, ticker)


def get_snapshot_all(market: str) -> Iterable[Any]:
    client = _get_client()
    _sleep_rate_limit()
    return client.get_snapshot_all(market)


def get_ticker_events(ticker: str) -> Any:
    client = _get_client()
    _sleep_rate_limit()
    return client.get_ticker_events(ticker)
