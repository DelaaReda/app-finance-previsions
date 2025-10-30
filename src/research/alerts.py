# src/research/alerts.py
from __future__ import annotations
from typing import List, Dict, Any
import pandas as pd

def _last(series: pd.Series):
    return None if series is None or series.empty else float(series.dropna().iloc[-1])

def alerts_for_ticker(df_prices: pd.DataFrame, df_ind: pd.DataFrame, recent_news_score: float, ticker: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    close = _last(df_prices.get("Close", pd.Series(dtype=float)))
    rsi = _last(df_ind.get("rsi", pd.Series(dtype=float)))
    sma20 = _last(df_ind.get("sma20", pd.Series(dtype=float)))
    macd = _last(df_ind.get("macd", pd.Series(dtype=float)))

    # RSI zones
    if rsi is not None and rsi > 70:
        out.append({"type": "rsi_overbought", "ticker": ticker, "severity": "warning", "detail": f"RSI={rsi:.1f} > 70"})
    if rsi is not None and rsi < 30:
        out.append({"type": "rsi_oversold", "ticker": ticker, "severity": "info", "detail": f"RSI={rsi:.1f} < 30"})

    # SMA20 cross
    if close is not None and sma20 is not None:
        if close > sma20:
            out.append({"type": "trend_up", "ticker": ticker, "severity": "info", "detail": f"Close {close:.2f} above SMA20 {sma20:.2f}"})
        else:
            out.append({"type": "trend_down", "ticker": ticker, "severity": "warning", "detail": f"Close {close:.2f} below SMA20 {sma20:.2f}"})

    # MACD momentum
    if macd is not None:
        if macd > 0:
            out.append({"type": "momentum_pos", "ticker": ticker, "severity": "info", "detail": f"MACD positive {macd:.2f}"})
        else:
            out.append({"type": "momentum_neg", "ticker": ticker, "severity": "warning", "detail": f"MACD negative {macd:.2f}"})

    # News spike (naïf)
    if recent_news_score is not None and recent_news_score > 0.8:
        out.append({"type": "news_spike", "ticker": ticker, "severity": "info", "detail": f"High news score {recent_news_score:.2f}"})

    return out

def summarize_alerts(alerts: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for a in alerts:
        counts[a["type"]] = counts.get(a["type"], 0) + 1
    return counts