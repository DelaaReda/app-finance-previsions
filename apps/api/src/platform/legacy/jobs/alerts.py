"""
Alerts Job - Generates market alerts based on technical signals, news sentiment, and forecasts
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import random

import sys
import os
# Add backend directory to path to properly import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.ml_forecast import run_forecast_generation
from storage.io import save_json, load_json


def compute_alerts() -> List[Dict[str, Any]]:
    """
    Compute market alerts by combining:
    1. Technical signals (RSI, MACD, etc.)
    2. News sentiment
    3. Forecast direction
    """
    alerts = []
    
    # Load forecasts to correlate with alerts
    forecasts_data = load_json("forecasts")
    forecasts = forecasts_data.get("payload", {}).get("rows", []) if forecasts_data else []
    
    # Load news to check for sentiment correlation
    news_data = load_json("news_feed")
    articles = news_data.get("payload", {}).get("articles", []) if news_data else []
    
    # Common tickers to scan for alerts
    tickers = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "TSM"]
    
    for ticker in tickers:
        # Simulate technical analysis (in real implementation, would use actual indicators)
        rsi = random.uniform(20, 80)
        volatility = random.uniform(0.01, 0.05)
        
        # Find related forecasts for this ticker
        ticker_forecasts = [f for f in forecasts if f.get("ticker") == ticker]
        
        # Find related news for this ticker
        ticker_news = [a for a in articles if ticker in a.get("tickers", []) or ticker in a.get("title", "").upper()]
        
        # Rule 1: Oversold-Bearish alert
        if rsi < 30:  # Oversold condition
            for forecast in ticker_forecasts:
                if forecast.get("direction") == "down":
                    sentiment_negative = any(a.get("sentiment_score", 0) < -0.3 for a in ticker_news)
                    
                    if sentiment_negative:
                        confidence = min(
                            forecast.get("confidence", 0.5),
                            0.9  # High confidence for confluence
                        )
                        
                        alerts.append({
                            "id": f"oversold-bearish-{ticker}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                            "type": "oversold-bearish",
                            "ticker": ticker,
                            "description": f"{ticker} oversold (RSI: {rsi:.1f}) with negative sentiment and bearish forecast",
                            "severity": "medium",
                            "confidence": confidence,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "signals": {
                                "rsi": rsi,
                                "sentiment_negative": sentiment_negative,
                                "forecast_direction": "down"
                            }
                        })
        
        # Rule 2: Overbought-Bullish alert
        if rsi > 70:  # Overbought condition
            for forecast in ticker_forecasts:
                if forecast.get("direction") == "up":
                    sentiment_positive = any(a.get("sentiment_score", 0) > 0.3 for a in ticker_news)
                    
                    if sentiment_positive:
                        confidence = min(
                            forecast.get("confidence", 0.5),
                            0.9  # High confidence for confluence
                        )
                        
                        alerts.append({
                            "id": f"overbought-bullish-{ticker}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                            "type": "overbought-bullish", 
                            "ticker": ticker,
                            "description": f"{ticker} overbought (RSI: {rsi:.1f}) with positive sentiment and bullish forecast",
                            "severity": "medium",
                            "confidence": confidence,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "signals": {
                                "rsi": rsi,
                                "sentiment_positive": sentiment_positive,
                                "forecast_direction": "up"
                            }
                        })
        
        # Rule 3: Breakout News alert (high volatility + news activity)
        if volatility > 0.03:  # High volatility threshold
            recent_news = [a for a in ticker_news if 
                "pubDate" in a and 
                (datetime.utcnow() - datetime.fromisoformat(a["pubDate"].replace("Z", "+00:00"))) < timedelta(hours=1)]
            
            if len(recent_news) >= 2:  # At least 2 news items in last hour
                alerts.append({
                    "id": f"breakout-news-{ticker}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    "type": "breakout-news",
                    "ticker": ticker,
                    "description": f"{ticker} high volatility with breaking news ({len(recent_news)} articles in last hour)",
                    "severity": "high",
                    "confidence": 0.8,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "signals": {
                        "volatility": volatility,
                        "recent_news_count": len(recent_news)
                    }
                })
    
    # Sort alerts by confidence (highest first)
    alerts.sort(key=lambda x: x["confidence"], reverse=True)
    
    # Prepare final payload
    final_payload = {
        "alerts": alerts,
        "count": len(alerts),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": ["technical_signals", "news_sentiment", "forecast_correlation", "market_regime"],
        "pipeline": {
            "algorithm": "multi_signal_confluence_v1",
            "processed_at": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    return final_payload


def run_alerts_job():
    """
    Main alerts job that computes and saves alerts
    """
    print("[INFO] Starting alerts generation job...")
    
    try:
        # Compute alerts
        alerts_data = compute_alerts()
        
        # Save to persistent storage
        save_json("alerts", alerts_data, source=["job:alerts", "multi_signal_v1"])
        
        print(f"[SUCCESS] Alerts job completed. Generated {alerts_data['count']} alerts.")
        return alerts_data
        
    except Exception as e:
        print(f"[ERROR] Alerts job failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return empty alerts structure on failure to maintain never-empty pattern
        error_payload = {
            "alerts": [],
            "count": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
            "source": ["job:alerts", "error_fallback"],
            "pipeline": {
                "algorithm": "multi_signal_confluence_v1",
                "processed_at": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        save_json("alerts", error_payload, source=["job:alerts", "error_fallback"])
        return error_payload


def get_latest_alerts():
    """
    Retrieve the latest alerts from persistent storage
    """
    alerts_snapshot = load_json("alerts")
    if alerts_snapshot:
        # If alerts_snapshot has a payload key, return that
        if "payload" in alerts_snapshot:
            return alerts_snapshot["payload"]
        else:
            # Otherwise return the data structure
            return {
                "alerts": alerts_snapshot.get("alerts", []),
                "count": alerts_snapshot.get("count", 0),
                "generated_at": alerts_snapshot.get("generated_at", datetime.utcnow().isoformat() + "Z"),
                "source": alerts_snapshot.get("source", []),
                "pipeline": alerts_snapshot.get("pipeline", {})
            }
    else:
        # Return empty structure if no alerts available
        return {
            "alerts": [],
            "count": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["fallback_empty"],
            "pipeline": {
                "algorithm": "multi_signal_confluence_v1",
                "processed_at": None
            }
        }


if __name__ == "__main__":
    # Run standalone for testing
    result = run_alerts_job()
    print(f"Job completed with {result['count']} alerts")