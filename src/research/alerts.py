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
    sma50 = _last(df_ind.get("sma50", pd.Series(dtype=float)))
    sma200 = _last(df_ind.get("sma200", pd.Series(dtype=float)))
    macd = _last(df_ind.get("macd", pd.Series(dtype=float)))
    volume = _last(df_prices.get("Volume", pd.Series(dtype=float)))  # if volume data is available
    bb_upper = _last(df_ind.get("bollinger_upper", pd.Series(dtype=float)))
    bb_lower = _last(df_ind.get("bollinger_lower", pd.Series(dtype=float)))

    # RSI zones
    if rsi is not None:
        if rsi > 70:
            out.append({"type": "rsi_overbought", "ticker": ticker, "severity": "warning", "detail": f"RSI={rsi:.1f} > 70", "value": rsi})
        elif rsi < 30:
            out.append({"type": "rsi_oversold", "ticker": ticker, "severity": "info", "detail": f"RSI={rsi:.1f} < 30", "value": rsi})
        elif rsi > 60:
            out.append({"type": "rsi_bullish", "ticker": ticker, "severity": "info", "detail": f"RSI={rsi:.1f} in bullish territory", "value": rsi})
        elif rsi < 40:
            out.append({"type": "rsi_bearish", "ticker": ticker, "severity": "info", "detail": f"RSI={rsi:.1f} in bearish territory", "value": rsi})

    # SMA crossovers (golden cross/death cross)
    if close is not None and sma20 is not None and sma50 is not None:
        if sma20 > sma50 and close > sma20:
            out.append({"type": "golden_cross_signal", "ticker": ticker, "severity": "info", "detail": f"Golden cross: SMA20 {sma20:.2f} above SMA50 {sma50:.2f}, price {close:.2f} above SMA20", "value": close})
        elif sma20 < sma50 and close < sma20:
            out.append({"type": "death_cross_signal", "ticker": ticker, "severity": "warning", "detail": f"Death cross: SMA20 {sma20:.2f} below SMA50 {sma50:.2f}, price {close:.2f} below SMA20", "value": close})

    # Long-term trend (SMA200)
    if close is not None and sma200 is not None:
        if close > sma200:
            out.append({"type": "long_term_bullish", "ticker": ticker, "severity": "info", "detail": f"Price {close:.2f} above SMA200 {sma200:.2f}", "value": close})
        else:
            out.append({"type": "long_term_bearish", "ticker": ticker, "severity": "warning", "detail": f"Price {close:.2f} below SMA200 {sma200:.2f}", "value": close})

    # MACD momentum
    if macd is not None:
        if macd > 0.05:
            out.append({"type": "momentum_strong_pos", "ticker": ticker, "severity": "info", "detail": f"Strong positive MACD {macd:.2f}", "value": macd})
        elif macd > 0:
            out.append({"type": "momentum_pos", "ticker": ticker, "severity": "info", "detail": f"Positive MACD {macd:.2f}", "value": macd})
        elif macd < -0.05:
            out.append({"type": "momentum_strong_neg", "ticker": ticker, "severity": "warning", "detail": f"Strong negative MACD {macd:.2f}", "value": macd})
        else:
            out.append({"type": "momentum_neg", "ticker": ticker, "severity": "warning", "detail": f"Negative MACD {macd:.2f}", "value": macd})

    # Price levels (Bollinger Bands)
    if close is not None and bb_upper is not None and bb_lower is not None:
        if close >= bb_upper:
            out.append({"type": "bb_resistance", "ticker": ticker, "severity": "warning", "detail": f"Price {close:.2f} at upper Bollinger band {bb_upper:.2f}", "value": close})
        elif close <= bb_lower:
            out.append({"type": "bb_support", "ticker": ticker, "severity": "info", "detail": f"Price {close:.2f} at lower Bollinger band {bb_lower:.2f}", "value": close})

    # News sentiment alerts
    if recent_news_score is not None:
        if recent_news_score > 0.8:
            out.append({"type": "news_spike_positive", "ticker": ticker, "severity": "info", "detail": f"High positive news sentiment {recent_news_score:.2f}", "value": recent_news_score})
        elif recent_news_score < 0.2:
            out.append({"type": "news_spike_negative", "ticker": ticker, "severity": "warning", "detail": f"High negative news sentiment {recent_news_score:.2f}", "value": recent_news_score})
        elif recent_news_score > 0.6:
            out.append({"type": "news_positive", "ticker": ticker, "severity": "info", "detail": f"Positive news sentiment {recent_news_score:.2f}", "value": recent_news_score})
        elif recent_news_score < 0.4:
            out.append({"type": "news_negative", "ticker": ticker, "severity": "info", "detail": f"Negative news sentiment {recent_news_score:.2f}", "value": recent_news_score})

    # Price-based alerts
    if close is not None:
        # Significant move alerts
        if len(df_prices) >= 2:
            prev_close = float(df_prices['Close'].iloc[-2]) if 'Close' in df_prices.columns else None
            if prev_close is not None and prev_close != 0:
                change_pct = ((close - prev_close) / prev_close) * 100
                if abs(change_pct) > 5:  # Significant move threshold
                    if change_pct > 5:
                        out.append({"type": "large_positive_move", "ticker": ticker, "severity": "info", "detail": f"Large positive move: {change_pct:+.2f}%", "value": change_pct})
                    else:
                        out.append({"type": "large_negative_move", "ticker": ticker, "severity": "warning", "detail": f"Large negative move: {change_pct:+.2f}%", "value": change_pct})

    return out

def summarize_alerts(alerts: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for a in alerts:
        counts[a["type"]] = counts.get(a["type"], 0) + 1
    return counts