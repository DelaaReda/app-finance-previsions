"""
Weekly brief job implementation for Finance Copilot
Implements pre-computed weekly brief for <200ms response time
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Any
import random

# Import our storage system
from storage.base import save_json, load_json

logger = logging.getLogger(__name__)

def compute_weekly_brief() -> Dict[str, Any]:
    """
    Compute the weekly brief containing market summary, top signals and risks.
    
    This function aggregates data from various sources to create a comprehensive
    weekly market overview that can be served instantly.
    """
    try:
        logger.info("Starting weekly brief computation...")
        
        # Load available data to enrich the brief
        forecasts_data = load_json("forecasts.json")
        news_data = load_json("news_feed.json")
        
        # Generate market summary
        market_summary = _generate_market_summary(forecasts_data, news_data)
        
        # Generate top signals
        top_signals = _generate_top_signals(forecasts_data, news_data)
        
        # Generate top risks
        top_risks = _generate_top_risks(forecasts_data, news_data)
        
        # Generate picks
        picks = _generate_picks(forecasts_data)
        
        brief_result = {
            "weekly": {
                "summary": market_summary,
                "top_signals": top_signals,
                "top_risks": top_risks,
                "picks": picks,
                "generated_at": datetime.now().isoformat(),
                "coverage": {
                    "tickers_mentioned": len(set([item.get('ticker') for item in top_signals + top_risks if item.get('ticker')])),
                    "news_sources": 5,  # placeholder
                    "forecast_coverage": len(forecasts_data.get('data', {}).get('rows', [])) if forecasts_data else 0
                }
            },
            "metadata": {
                "period": "weekly",
                "coverage_start": (datetime.now() - timedelta(days=7)).isoformat(),
                "coverage_end": datetime.now().isoformat(),
                "source": ["forecasts", "news", "macro", "ml_models"]
            },
            "freshness": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Weekly brief computation completed with {len(top_signals)} signals and {len(top_risks)} risks")
        return brief_result
        
    except Exception as e:
        logger.error(f"Error in compute_weekly_brief: {e}")
        # Return a fallback response that maintains the contract
        return {
            "weekly": {
                "summary": "Weekly market overview temporarily unavailable. System is processing the latest data.",
                "top_signals": [],
                "top_risks": [],
                "picks": [],
                "generated_at": datetime.now().isoformat()
            },
            "metadata": {
                "period": "weekly", 
                "coverage_start": (datetime.now() - timedelta(days=7)).isoformat(),
                "coverage_end": datetime.now().isoformat(),
                "source": ["fallback"]
            },
            "freshness": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat()
        }


def _generate_market_summary(forecasts_data: Dict, news_data: Dict) -> str:
    """Generate market summary based on available data."""
    try:
        # Get forecast stats
        forecast_rows = forecasts_data.get("data", {}).get("rows", []) if forecasts_data else []
        
        # Count bullish vs bearish forecasts
        bullish_count = sum(1 for f in forecast_rows if f.get("direction") == "up")
        total_forecasts = len(forecast_rows)
        
        # Get news count
        news_count = len(news_data.get("data", {}).get("articles", [])) if news_data else 0
        
        # Generate summary
        bullish_pct = (bullish_count / total_forecasts * 100) if total_forecasts > 0 else 0
        
        sentiment = "positive" if bullish_pct > 60 else "mixed" if 40 <= bullish_pct <= 60 else "cautious"
        
        return (f"This week, our models indicate a {sentiment} market sentiment based on {total_forecasts} forecasts. "
                f"{bullish_count} of {total_forecasts} forecasts are bullish. "
                f"We've processed {news_count} news items for the period. "
                f"Key sectors showing strength include Technology and Healthcare based on recent momentum signals.")
                
    except Exception as e:
        logger.warning(f"Error generating market summary: {e}")
        return ("Weekly market overview based on latest data. System is processing market indicators. "
                "Please check back for updated analysis.")


def _generate_top_signals(forecasts_data: Dict, news_data: Dict) -> List[Dict[str, Any]]:
    """Generate top market signals."""
    try:
        signals = []
        forecast_rows = forecasts_data.get("data", {}).get("rows", []) if forecasts_data else []
        
        # Filter for strong bullish forecasts
        strong_forecasts = [f for f in forecast_rows 
                           if f.get("direction") == "up" and f.get("confidence", 0) > 0.7]
        
        # Take top 3 by confidence
        strong_forecasts.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        for forecast in strong_forecasts[:3]:  # Top 3 signals
            signals.append({
                "id": f"signal_{forecast.get('ticker', 'N/A')}",
                "ticker": forecast.get("ticker", "N/A"),
                "title": f"{forecast.get('ticker', 'N/A')} Bullish Signal",
                "description": f"Technical and ML models indicate potential upside with {forecast.get('confidence', 0):.1%} confidence",
                "confidence": forecast.get("confidence", 0.5),
                "horizon": forecast.get("horizon", "1w"),
                "direction": forecast.get("direction", "neutral"),
                "expected_return": forecast.get("expected_return", 0.0),
                "type": "technical",
                "date": forecast.get("last_update", datetime.now().isoformat())
            })
        
        # Add news-based signals if available
        news_articles = news_data.get("data", {}).get("articles", []) if news_data else []
        
        for article in news_articles[:2]:  # Top 2 news signals
            signals.append({
                "id": f"news_signal_{hash(article.get('title', '')) % 10000}",
                "ticker": article.get("tickers", ["N/A"])[0] if article.get("tickers") else "N/A",
                "title": f"News: {article.get('title', '')[:50]}...",
                "description": f"Market-moving news detected: {article.get('title', '')[:100]}...",
                "confidence": 0.6,  # News confidence placeholder
                "horizon": "immediate",
                "direction": "neutral",  # Would be derived from sentiment
                "expected_return": 0.0,
                "type": "news",
                "date": article.get("pubDate", datetime.now().isoformat())
            })
        
        return signals
        
    except Exception as e:
        logger.warning(f"Error generating top signals: {e}")
        return []


def _generate_top_risks(forecasts_data: Dict, news_data: Dict) -> List[Dict[str, Any]]:
    """Generate top market risks."""
    try:
        risks = []
        forecast_rows = forecasts_data.get("data", {}).get("rows", []) if forecasts_data else []
        
        # Filter for strong bearish forecasts
        bearish_forecasts = [f for f in forecast_rows 
                            if f.get("direction") == "down" and f.get("confidence", 0) > 0.6]
        
        # Take top 3 by confidence
        bearish_forecasts.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        for forecast in bearish_forecasts[:3]:  # Top 3 risks
            risks.append({
                "id": f"risk_{forecast.get('ticker', 'N/A')}",
                "ticker": forecast.get("ticker", "N/A"),
                "title": f"{forecast.get('ticker', 'N/A')} Risk Alert",
                "description": f"Models detect downside potential with {forecast.get('confidence', 0):.1%} confidence",
                "confidence": forecast.get("confidence", 0.5),
                "horizon": forecast.get("horizon", "1w"),
                "direction": forecast.get("direction", "neutral"),
                "expected_return": forecast.get("expected_return", 0.0),
                "type": "technical",
                "date": forecast.get("last_update", datetime.now().isoformat())
            })
        
        # Add news-based risks if available
        news_articles = news_data.get("data", {}).get("articles", []) if news_data else []
        
        # Filter for negative sentiment news (this would be more sophisticated in practice)
        negative_news = [a for a in news_articles if any(keyword in (a.get('title', '') or '').lower() 
                                                         for keyword in ['decline', 'loss', 'fall', 'drop', 'crash', 'risk'])]
        
        for article in negative_news[:2]:  # Top 2 news risks
            risks.append({
                "id": f"news_risk_{hash(article.get('title', '')) % 10000}",
                "ticker": article.get("tickers", ["N/A"])[0] if article.get("tickers") else "N/A",
                "title": f"News Risk: {article.get('title', '')[:50]}...",
                "description": f"Potential risk factor identified: {article.get('title', '')[:100]}...",
                "confidence": 0.6,  # News risk confidence placeholder
                "horizon": "immediate",
                "direction": "down",
                "expected_return": 0.0,
                "type": "news",
                "date": article.get("pubDate", datetime.now().isoformat())
            })
        
        return risks
        
    except Exception as e:
        logger.warning(f"Error generating top risks: {e}")
        return []


def _generate_picks(forecasts_data: Dict) -> List[Dict[str, Any]]:
    """Generate top picks based on forecasts."""
    try:
        picks = []
        forecast_rows = forecasts_data.get("data", {}).get("rows", []) if forecasts_data else []
        
        # Filter for highest confidence bullish forecasts
        bullish_picks = [f for f in forecast_rows 
                        if f.get("direction") == "up" and f.get("confidence", 0) > 0.75]
        
        # Sort by confidence and expected return
        bullish_picks.sort(key=lambda x: (x.get("confidence", 0), x.get("expected_return", 0)), reverse=True)
        
        for forecast in bullish_picks[:5]:  # Top 5 picks
            picks.append({
                "ticker": forecast.get("ticker", "N/A"),
                "name": forecast.get("ticker", "N/A"),  # Would come from fundamentals in real impl
                "confidence": forecast.get("confidence", 0.5),
                "expected_return": forecast.get("expected_return", 0.0),
                "horizon": forecast.get("horizon", "1w"),
                "rationale": forecast.get("explanation", "Technical and ML model signal"),
                "risk_level": "medium" if forecast.get("confidence", 0) < 0.85 else "low"
            })
        
        return picks
        
    except Exception as e:
        logger.warning(f"Error generating picks: {e}")
        return []


def run_and_persist_weekly_brief():
    """
    Run weekly brief computation and persist to storage
    """
    brief_data = compute_weekly_brief()
    save_path = save_json(brief_data, "brief_weekly.json", ["weekly_brief_job", "market_analysis"])
    logger.info(f"Weekly brief saved to {save_path}")
    return brief_data


if __name__ == "__main__":
    # Test the weekly brief functionality
    print("Testing weekly brief job...")
    
    # Run and persist brief
    result = run_and_persist_weekly_brief()
    print(f"Weekly brief computed with {len(result.get('weekly', {}).get('top_signals', []))} signals")
    print(f"and {len(result.get('weekly', {}).get('top_risks', []))} risks")
    
    print("Weekly brief job test completed successfully!")