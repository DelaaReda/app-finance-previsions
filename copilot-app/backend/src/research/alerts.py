"""
Advanced Alerts Engine combining technical indicators, news sentiment, and forecast signals.
Task: FC-P1-014 - Alerts (signals + news) that incorporates forecasting direction and confidence.
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
from __future__ import annotations
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path


def _last(series: pd.Series):
    """Get last non-null value in series."""
    return None if series is None or series.empty else float(series.dropna().iloc[-1])


def alerts_for_ticker(df_prices: pd.DataFrame, df_ind: pd.DataFrame, recent_news_score: float, ticker: str) -> List[Dict[str, Any]]:
    """
    Enhanced alerts for ticker combining technical indicators, news sentiment, and forecast signals.
    
    Args:
        df_prices: Price data DataFrame
        df_ind: Technical indicators DataFrame
        recent_news_score: News sentiment score (0-1 scale)
        ticker: Ticker symbol
        
    Returns:
        List of alerts with severity levels
    """
    out: List[Dict[str, Any]] = []
    
    # Get key indicator values
    close = _last(df_prices.get("Close", pd.Series(dtype=float)))
    rsi = _last(df_ind.get("rsi", pd.Series(dtype=float)))
    sma20 = _last(df_ind.get("sma20", pd.Series(dtype=float)))
    sma50 = _last(df_ind.get("sma50", pd.Series(dtype=float)))
    sma200 = _last(df_ind.get("sma200", pd.Series(dtype=float)))
    macd = _last(df_ind.get("macd", pd.Series(dtype=float)))
    volume = _last(df_prices.get("Volume", pd.Series(dtype=float)))
    bb_upper = _last(df_ind.get("bollinger_upper", pd.Series(dtype=float)))
    bb_lower = _last(df_ind.get("bollinger_lower", pd.Series(dtype=float)))
    
    # TECHNICAL ALERTS (existing)  
    # RSI zones
    if rsi is not None:
        if rsi > 70:
            out.append({
                "type": "rsi_overbought", 
                "ticker": ticker, 
                "severity": "warning", 
                "detail": f"RSI={rsi:.1f} > 70", 
                "value": rsi,
                "category": "technical"
            })
        elif rsi < 30:
            out.append({
                "type": "rsi_oversold", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"RSI={rsi:.1f} < 30", 
                "value": rsi,
                "category": "technical"
            })
        elif rsi > 60:
            out.append({
                "type": "rsi_bullish", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"RSI={rsi:.1f} in bullish territory", 
                "value": rsi,
                "category": "technical"
            })
        elif rsi < 40:
            out.append({
                "type": "rsi_bearish", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"RSI={rsi:.1f} in bearish territory", 
                "value": rsi,
                "category": "technical"
            })

    # SMA crossovers (golden cross/death cross)
    if close is not None and sma20 is not None and sma50 is not None:
        if sma20 > sma50 and close > sma20:
            out.append({
                "type": "golden_cross_signal", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"Golden cross: SMA20 {sma20:.2f} above SMA50 {sma50:.2f}, price {close:.2f} above SMA20", 
                "value": close,
                "category": "technical"
            })
        elif sma20 < sma50 and close < sma20:
            out.append({
                "type": "death_cross_signal", 
                "ticker": ticker, 
                "severity": "warning", 
                "detail": f"Death cross: SMA20 {sma20:.2f} below SMA50 {sma50:.2f}, price {close:.2f} below SMA20", 
                "value": close,
                "category": "technical"
            })

    # Long-term trend (SMA200)
    if close is not None and sma200 is not None:
        if close > sma200:
            out.append({
                "type": "long_term_bullish", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"Price {close:.2f} above SMA200 {sma200:.2f}", 
                "value": close,
                "category": "technical"
            })
        else:
            out.append({
                "type": "long_term_bearish", 
                "ticker": ticker, 
                "severity": "warning", 
                "detail": f"Price {close:.2f} below SMA200 {sma200:.2f}", 
                "value": close,
                "category": "technical"
            })

    # MACD momentum
    if macd is not None:
        if macd > 0.05:
            out.append({
                "type": "momentum_strong_pos", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"Strong positive MACD {macd:.2f}", 
                "value": macd,
                "category": "technical"
            })
        elif macd > 0:
            out.append({
                "type": "momentum_pos", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"Positive MACD {macd:.2f}", 
                "value": macd,
                "category": "technical"
            })
        elif macd < -0.05:
            out.append({
                "type": "momentum_strong_neg", 
                "ticker": ticker, 
                "severity": "warning", 
                "detail": f"Strong negative MACD {macd:.2f}", 
                "value": macd,
                "category": "technical"
            })
        else:
            out.append({
                "type": "momentum_neg", 
                "ticker": ticker, 
                "severity": "warning", 
                "detail": f"Negative MACD {macd:.2f}", 
                "value": macd,
                "category": "technical"
            })

    # Price levels (Bollinger Bands)
    if close is not None and bb_upper is not None and bb_lower is not None:
        if close >= bb_upper:
            out.append({
                "type": "bb_resistance", 
                "ticker": ticker, 
                "severity": "warning", 
                "detail": f"Price {close:.2f} at upper Bollinger band {bb_upper:.2f}", 
                "value": close,
                "category": "technical"
            })
        elif close <= bb_lower:
            out.append({
                "type": "bb_support", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"Price {close:.2f} at lower Bollinger band {bb_lower:.2f}", 
                "value": close,
                "category": "technical"
            })

    # NEWS SENTIMENT ALERTS (existing)
    if recent_news_score is not None:
        if recent_news_score > 0.8:
            out.append({
                "type": "news_spike_positive", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"High positive news sentiment {recent_news_score:.2f}", 
                "value": recent_news_score,
                "category": "news"
            })
        elif recent_news_score < 0.2:
            out.append({
                "type": "news_spike_negative", 
                "ticker": ticker, 
                "severity": "warning", 
                "detail": f"High negative news sentiment {recent_news_score:.2f}", 
                "value": recent_news_score,
                "category": "news"
            })
        elif recent_news_score > 0.6:
            out.append({
                "type": "news_positive", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"Positive news sentiment {recent_news_score:.2f}", 
                "value": recent_news_score,
                "category": "news"
            })
        elif recent_news_score < 0.4:
            out.append({
                "type": "news_negative", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"Negative news sentiment {recent_news_score:.2f}", 
                "value": recent_news_score,
                "category": "news"
            })

    # PRICE-BASED ALERTS (existing)
    if close is not None:
        # Significant move alerts
        if len(df_prices) >= 2:
            prev_close = float(df_prices['Close'].iloc[-2]) if 'Close' in df_prices.columns else None
            if prev_close is not None and prev_close != 0:
                change_pct = ((close - prev_close) / prev_close) * 100
                if abs(change_pct) > 5:  # Significant move threshold
                    if change_pct > 5:
                        out.append({
                            "type": "large_positive_move", 
                            "ticker": ticker, 
                            "severity": "info", 
                            "detail": f"Large positive move: {change_pct:+.2f}%", 
                            "value": change_pct,
                            "category": "price"
                        })
                    else:
                        out.append({
                            "type": "large_negative_move", 
                            "ticker": ticker, 
                            "severity": "warning", 
                            "detail": f"Large negative move: {change_pct:+.2f}%", 
                            "value": change_pct,
                            "category": "price"
                        })
    
    # FORECAST-BASED ALERTS (NEW - FC-P1-014)
    forecast_signal_alerts = _generate_forecast_based_alerts(ticker, close)
    out.extend(forecast_signal_alerts)
    
    # COMBINED ALERTS (NEW - FC-P1-014)
    combined_alerts = _generate_combined_signal_alerts(ticker, rsi, recent_news_score, close, sma20, sma50)
    out.extend(combined_alerts)
    
    return out


def _generate_forecast_based_alerts(ticker: str, current_price: float) -> List[Dict[str, Any]]:
    """
    Generate alerts based on forecast signals from the hybrid forecasting model.
    """
    from backend.storage.base import load_json
    
    alerts = []
    
    try:
        # Load forecast data for this ticker
        forecasts_data = load_json("forecasts.json")
        
        if forecasts_data and "data" in forecasts_data:
            forecast_rows = forecasts_data["data"].get("rows", [])
            
            # Find forecast for this specific ticker
            ticker_forecast = None
            for row in forecast_rows:
                if row.get("ticker", "").upper() == ticker.upper():
                    ticker_forecast = row
                    break
            
            if ticker_forecast:
                direction = ticker_forecast.get("direction", "neutral")
                confidence = ticker_forecast.get("confidence", 0.0)
                expected_return = ticker_forecast.get("expected_return", 0.0)
                
                # Generate alerts based on forecast
                if confidence > 0.75:
                    if direction == "up" and expected_return > 0.02:
                        alerts.append({
                            "type": "forecast_strong_bullish", 
                            "ticker": ticker, 
                            "severity": "info", 
                            "detail": f"Strong bullish forecast: {direction} direction, {confidence:.2f} confidence, {expected_return*100:+.2f}% expected return", 
                            "value": expected_return,
                            "category": "forecast",
                            "confidence": confidence,
                            "forecast_direction": direction
                        })
                    elif direction == "down" and expected_return < -0.02:
                        alerts.append({
                            "type": "forecast_strong_bearish", 
                            "ticker": ticker, 
                            "severity": "warning", 
                            "detail": f"Strong bearish forecast: {direction} direction, {confidence:.2f} confidence, {expected_return*100:+.2f}% expected return", 
                            "value": expected_return,
                            "category": "forecast",
                            "confidence": confidence,
                            "forecast_direction": direction
                        })
                    elif direction == "up" and expected_return > 0:
                        alerts.append({
                            "type": "forecast_bullish", 
                            "ticker": ticker, 
                            "severity": "info", 
                            "detail": f"Bullish forecast: {direction} direction, {confidence:.2f} confidence, {expected_return*100:+.2f}% expected return", 
                            "value": expected_return,
                            "category": "forecast",
                            "confidence": confidence,
                            "forecast_direction": direction
                        })
                    elif direction == "down":
                        alerts.append({
                            "type": "forecast_bearish", 
                            "ticker": ticker, 
                            "severity": "info", 
                            "detail": f"Bearish forecast: {direction} direction, {confidence:.2f} confidence, {expected_return*100:+.2f}% expected return", 
                            "value": expected_return,
                            "category": "forecast",
                            "confidence": confidence,
                            "forecast_direction": direction
                        })
                
                # Low confidence alert
                if confidence < 0.5:
                    alerts.append({
                        "type": "forecast_low_confidence", 
                        "ticker": ticker, 
                        "severity": "info", 
                        "detail": f"Low forecast confidence: {confidence:.2f}", 
                        "value": confidence,
                        "category": "forecast",
                        "confidence": confidence
                    })
    except Exception as e:
        # If forecast data is unavailable, continue silently
        pass
    
    return alerts


def _generate_combined_signal_alerts(ticker: str, rsi: float, news_score: float, 
                                   current_price: float, sma20: float, sma50: float) -> List[Dict[str, Any]]:
    """
    Generate alerts that combine multiple signals (technical + news + forecast).
    """
    from backend.storage.base import load_json
    
    alerts = []
    
    try:
        # Load forecast data for combination logic
        forecasts_data = load_json("forecasts.json")
        forecast_direction = None
        forecast_confidence = 0.0
        
        if forecasts_data and "data" in forecasts_data:
            forecast_rows = forecasts_data["data"].get("rows", [])
            for row in forecast_rows:
                if row.get("ticker", "").upper() == ticker.upper():
                    forecast_direction = row.get("direction")
                    forecast_confidence = row.get("confidence", 0.0)
                    break
        
        # OVERSOLD-BEARISH combo: RSI<30 AND news sentiment < 0.3 AND forecast dir=down
        if rsi is not None and rsi < 30 and news_score is not None and news_score < 0.3 and forecast_direction == "down":
            alerts.append({
                "type": "oversold_bearish_combo", 
                "ticker": ticker, 
                "severity": "critical", 
                "detail": f"Technical oversold (RSI={rsi:.1f}) + Negative news ({news_score:.2f}) + Bearish forecast = High risk scenario", 
                "value": rsi,
                "category": "combo",
                "rsi": rsi,
                "news_score": news_score,
                "forecast_direction": forecast_direction,
                "forecast_confidence": forecast_confidence
            })
        
        # OVERBOUGHT-BULLISH combo: RSI>70 AND news sentiment > 0.7 AND forecast dir=up
        if rsi is not None and rsi > 70 and news_score is not None and news_score > 0.7 and forecast_direction == "up":
            alerts.append({
                "type": "overbought_bullish_combo", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"Technical overbought (RSI={rsi:.1f}) + Positive news ({news_score:.2f}) + Bullish forecast = Potential bubble or strong momentum", 
                "value": rsi,
                "category": "combo",
                "rsi": rsi,
                "news_score": news_score,
                "forecast_direction": forecast_direction,
                "forecast_confidence": forecast_confidence
            })
        
        # GOLDEN CROSS + BULLISH FORECAST combo
        if (sma20 is not None and sma50 is not None and current_price is not None 
            and sma20 > sma50 and current_price > sma20 and forecast_direction == "up"):
            alerts.append({
                "type": "golden_cross_forecast_bullish", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"Golden cross confirmed (SMA20>SMA50) + Bullish forecast = Strong technical + predictive signal", 
                "value": current_price,
                "category": "combo",
                "sma20": sma20,
                "sma50": sma50,
                "price": current_price,
                "forecast_direction": forecast_direction,
                "forecast_confidence": forecast_confidence
            })
        
        # CONFLICT SIGNAL: Bullish forecast but oversold technicals (potential reversal opportunity)
        if (forecast_direction == "up" and rsi is not None and rsi < 30):
            alerts.append({
                "type": "forecast_technical_conflict_buy", 
                "ticker": ticker, 
                "severity": "info", 
                "detail": f"Bullish forecast but technical oversold (RSI={rsi:.1f}): potential reversal opportunity", 
                "value": rsi,
                "category": "combo",
                "rsi": rsi,
                "forecast_direction": forecast_direction,
                "forecast_confidence": forecast_confidence
            })
        
        # CONFLICT SIGNAL: Bearish forecast but overbought technicals (potential fade opportunity)
        if (forecast_direction == "down" and rsi is not None and rsi > 70):
            alerts.append({
                "type": "forecast_technical_conflict_sell", 
                "ticker": ticker, 
                "severity": "warning", 
                "detail": f"Bearish forecast but technical overbought (RSI={rsi:.1f}): potential fade opportunity", 
                "value": rsi,
                "category": "combo",
                "rsi": rsi,
                "forecast_direction": forecast_direction,
                "forecast_confidence": forecast_confidence
            })
        
    except Exception as e:
        # If combined signal logic fails, continue silently
        pass
    
    return alerts


def summarize_alerts(alerts: List[Dict[str, Any]]) -> Dict[str, int]:
    """Summarize alerts by type."""
    counts: Dict[str, int] = {}
    for a in alerts:
        counts[a["type"]] = counts.get(a["type"], 0) + 1
    return counts


def get_alerts_by_category(alerts: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
    """Filter alerts by category."""
    return [alert for alert in alerts if alert.get("category") == category]


def get_high_priority_alerts(alerts: List[Dict[str, Any]], min_severity: str = "warning") -> List[Dict[str, Any]]:
    """Get high priority alerts based on severity."""
    severity_order = {"info": 2, "warning": 1, "critical": 0}
    min_level = severity_order.get(min_severity, 1)
    
    return [
        alert for alert in alerts 
        if severity_order.get(alert.get("severity", "info"), 2) <= min_level
    ]


if __name__ == "__main__":
    # Example usage/test
    print("Testing enhanced alerts engine...")
    print("Alerts engine with forecast integration loaded successfully!")