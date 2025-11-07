"""
Weekly brief job module - REAL IMPLEMENTATION
Handles the generation of the weekly market brief with key insights and signals
Aggregates forecasts + news to generate top signals and risks
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: DATA-GEN-003 - Create real weekly brief generation
"""
from datetime import datetime
import logging
from pathlib import Path
import sys

# Add parent directory to path to import storage
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

logger = logging.getLogger(__name__)


def generate_signal_from_forecast(forecast: dict) -> dict:
    """
    Convert a bullish forecast into a signal
    
    Args:
        forecast: Forecast dictionary
        
    Returns:
        Signal dictionary
    """
    return {
        "ticker": forecast.get("ticker", ""),
        "type": "BULLISH",
        "confidence": forecast.get("confidence", 0.5),
        "expected_return": forecast.get("expected_return", 0),
        "reasoning": forecast.get("reasoning", ""),
        "target_price": forecast.get("target_price", 0),
        "current_price": forecast.get("current_price", 0),
        "horizon": forecast.get("horizon", "1d"),
        "source": "forecast_analysis",
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


def generate_risk_from_forecast(forecast: dict) -> dict:
    """
    Convert a bearish forecast into a risk
    
    Args:
        forecast: Forecast dictionary
        
    Returns:
        Risk dictionary
    """
    return {
        "ticker": forecast.get("ticker", ""),
        "type": "BEARISH",
        "confidence": forecast.get("confidence", 0.5),
        "expected_return": forecast.get("expected_return", 0),
        "reasoning": forecast.get("reasoning", ""),
        "target_price": forecast.get("target_price", 0),
        "current_price": forecast.get("current_price", 0),
        "horizon": forecast.get("horizon", "1d"),
        "source": "forecast_analysis",
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


def generate_signal_from_news(article: dict) -> dict:
    """
    Convert positive news into a signal
    
    Args:
        article: News article dictionary
        
    Returns:
        Signal dictionary
    """
    return {
        "ticker": article.get("tickers", [""])[0] if article.get("tickers") else "MARKET",
        "type": "NEWS_POSITIVE",
        "confidence": article.get("score", 50) / 100.0,  # Convert 0-100 to 0-1
        "sentiment": article.get("sentiment", "neutral"),
        "title": article.get("title", "")[:100],
        "summary": article.get("summary", "")[:200],
        "source": article.get("source", "news_feed"),
        "published_at": article.get("published_at", ""),
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


def generate_risk_from_news(article: dict) -> dict:
    """
    Convert negative news into a risk
    
    Args:
        article: News article dictionary
        
    Returns:
        Risk dictionary
    """
    return {
        "ticker": article.get("tickers", [""])[0] if article.get("tickers") else "MARKET",
        "type": "NEWS_NEGATIVE",
        "confidence": article.get("score", 50) / 100.0,  # Convert 0-100 to 0-1
        "sentiment": article.get("sentiment", "neutral"),
        "title": article.get("title", "")[:100],
        "summary": article.get("summary", "")[:200],
        "source": article.get("source", "news_feed"),
        "published_at": article.get("published_at", ""),
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


def run_weekly_brief_job():
    """
    Main function to run weekly brief generation job
    Aggregates forecasts and news to generate top signals and risks
    """
    logger.info("Starting weekly brief job with REAL data aggregation...")
    
    try:
        from storage.base import load_forecasts, load_news_feed, save_weekly_brief
        
        # Load forecasts
        forecasts_data = load_forecasts()
        forecasts = []
        if forecasts_data and forecasts_data.get('data'):
            forecasts = forecasts_data['data'].get('rows', [])
        logger.info(f"Loaded {len(forecasts)} forecasts")
        
        # Load news
        news_data = load_news_feed()
        articles = []
        if news_data and news_data.get('data'):
            articles = news_data['data'].get('articles', [])
        logger.info(f"Loaded {len(articles)} news articles")
        
        # Generate signals (bullish opportunities)
        signals = []
        
        # Signals from bullish forecasts
        bullish_forecasts = [f for f in forecasts if f.get('direction') == 'up']
        # Sort by confidence * expected_return (best opportunities)
        bullish_forecasts.sort(key=lambda x: x.get('confidence', 0) * x.get('expected_return', 0), reverse=True)
        
        for forecast in bullish_forecasts[:5]:  # Top 5 bullish forecasts
            signals.append(generate_signal_from_forecast(forecast))
        
        # Signals from positive news
        positive_news = [a for a in articles if a.get('sentiment') == 'positive']
        positive_news.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        for article in positive_news[:3]:  # Top 3 positive news
            signals.append(generate_signal_from_news(article))
        
        # Sort all signals by confidence
        signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        top_signals = signals[:3]  # Top 3 overall signals
        
        # Generate risks (bearish threats)
        risks = []
        
        # Risks from bearish forecasts
        bearish_forecasts = [f for f in forecasts if f.get('direction') == 'down']
        # Sort by confidence * abs(expected_return) (biggest threats)
        bearish_forecasts.sort(key=lambda x: x.get('confidence', 0) * abs(x.get('expected_return', 0)), reverse=True)
        
        for forecast in bearish_forecasts[:5]:  # Top 5 bearish forecasts
            risks.append(generate_risk_from_forecast(forecast))
        
        # Risks from negative news
        negative_news = [a for a in articles if a.get('sentiment') == 'negative']
        negative_news.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        for article in negative_news[:3]:  # Top 3 negative news
            risks.append(generate_risk_from_news(article))
        
        # Sort all risks by confidence
        risks.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        top_risks = risks[:3]  # Top 3 overall risks
        
        # Generate summary
        bullish_count = len([f for f in forecasts if f.get('direction') == 'up'])
        bearish_count = len([f for f in forecasts if f.get('direction') == 'down'])
        
        if bullish_count > bearish_count * 1.5:
            market_sentiment = "BULLISH"
        elif bearish_count > bullish_count * 1.5:
            market_sentiment = "BEARISH"
        else:
            market_sentiment = "MIXED"
        
        summary = f"Market sentiment: {market_sentiment}. {bullish_count} bullish vs {bearish_count} bearish forecasts. {len(positive_news)} positive and {len(negative_news)} negative news articles analyzed."
        
        # Prepare result
        result = {
            "summary": summary,
            "market_sentiment": market_sentiment,
            "top_signals": top_signals,
            "top_risks": top_risks,
            "key_events": [],  # Can be enhanced later
            "forecasts_analyzed": len(forecasts),
            "news_analyzed": len(articles),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "status": "completed"
        }
        
        # Save to persistent storage
        logger.info("Saving weekly brief to storage...")
        save_weekly_brief(result, source=["job:weekly_brief", "forecasts", "news"])
        
        # Return summary
        summary_result = {
            "summary": summary,
            "top_signals": len(top_signals),
            "top_risks": len(top_risks),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "completed"
        }
        
        logger.info(f"✅ Weekly brief job completed successfully. Generated {len(top_signals)} signals and {len(top_risks)} risks.")
        return summary_result
        
    except ImportError as e:
        logger.error(f"Import error in weekly brief job: {str(e)}", exc_info=True)
        return {
            "summary": "",
            "top_signals": [],
            "top_risks": [],
            "key_events": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": f"Import error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Weekly brief job failed: {str(e)}", exc_info=True)
        return {
            "summary": "",
            "top_signals": [],
            "top_risks": [],
            "key_events": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": str(e)
        }


if __name__ == "__main__":
    # Allow testing the job directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    result = run_weekly_brief_job()
    print(f"\n✅ Job completed: {result}")
