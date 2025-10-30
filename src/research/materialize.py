# src/research/materialize.py
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Iterable, List, Dict
import pandas as pd

from core.datasets import DatasetLayout, write_parquet_partition
from core.market_data import get_price_history, get_fred_series
from ingestion.finnews import run_pipeline
# Indicateurs: priorité phase2_technical; fallback basic
try:
    from analytics.phase2_technical import compute_indicators
except Exception:
    from analytics.indicators_basic import compute_indicators  # <— module fallback que je t'ai donné

DEFAULT_UNIVERSE = ("SPY", "QQQ", "AAPL", "NVDA", "MSFT")
MACRO_SERIES = ("CPIAUCSL", "VIXCLS", "DGS10")  # CPI, VIX, 10Y

def materialize_prices_features(universe: Iterable[str] = DEFAULT_UNIVERSE, interval="1d", period="1y"):
    lay = DatasetLayout.default()
    frames = []
    for sym in universe:
        df = get_price_history(sym, interval=interval)  # period param si ton loader le supporte
        if df is None or df.empty:
            continue
        ind = compute_indicators(df)
        out = pd.DataFrame(index=df.index)
        out["symbol"] = sym
        out["close"] = df["Close"]
        for col in ("rsi", "sma20", "macd"):
            if col in ind:
                out[col] = ind[col]
        out = out.reset_index().rename(columns={"Date": "date", "Datetime": "date"})
        frames.append(out)
    if not frames:
        return None
    all_df = pd.concat(frames, ignore_index=True)
    pdir = lay.today_partition("features", table="prices_features_daily")
    return write_parquet_partition(all_df, pdir)

def materialize_macro_snapshot(series_ids: Iterable[str] = MACRO_SERIES, start="2018-01-01"):
    lay = DatasetLayout.default()
    frames = []
    for sid in series_ids:
        s = get_fred_series(sid, start=start)
        if s is None or s.empty:
            continue
        out = s.reset_index()
        out.columns = ["date", "value"]
        out["series"] = sid
        frames.append(out)
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    pdir = lay.today_partition("features", table="macro_snapshot_daily")
    return write_parquet_partition(df, pdir)

def materialize_news_features(universe: Iterable[str] = DEFAULT_UNIVERSE, limit=200):
    lay = DatasetLayout.default()
    rows = []
    for sym in universe:
        items = run_pipeline(regions=["US","CA","INTL"], window="last_week", tgt_ticker=sym, limit=limit)
        if not items:
            continue
        scores = [float(x.get("score", 0.0)) for x in items]
        row = {
            "symbol": sym,
            "news_score_mean": float(pd.Series(scores).mean()) if scores else 0.0,
            "news_count": int(len(items)),
            "asof": datetime.utcnow().date().isoformat(),
        }
        rows.append(row)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    pdir = lay.today_partition("features", table="news_features_daily")
    return write_parquet_partition(df, pdir)