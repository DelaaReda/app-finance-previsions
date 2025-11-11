"""
News Impact Analysis API Route
Task: FC-API-030 - News Impact Analysis
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from services.news_analyzer import news_analytics_service
from storage.io import load_json
from services.cache_layer import load_or_compute

router = APIRouter(prefix="/api", tags=["news"])

@router.get("/news/analysis")
async def news_impact_analysis(
    ticker: List[str] = Query(..., description="Tickers à analyser (ex: NVDA,TSLA,AAPL)"),
    days_back: int = Query(30, ge=1, le=365, description="Nombre de jours d'historique à analyser"),
    min_sentiment: float = Query(-1.0, ge=-1.0, le=1.0, description="Sentiment minimum pour inclusion (-1.0 à 1.0)"),
    max_sentiment: float = Query(1.0, ge=-1.0, le=1.0, description="Sentiment maximum pour inclusion (-1.0 à 1.0)"),
    min_relevance: float = Query(0.1, ge=0.0, le=1.0, description="Score de pertinence minimum (0.0 à 1.0)"),
    source: Optional[str] = Query(None, description="Source spécifique à analyser (bloomberg, reuters, etc.)")
):
    """
    Get news impact analysis for specified tickers with comprehensive metrics.
    Implements never-empty contract by serving cached/latest analysis if live computation fails.
    """
    try:
        def compute_news_analysis():
            """Compute fresh news impact analysis from article data"""
            try:
                # Load news articles
                news_data = load_json("news_feed") or {}
                articles = news_data.get("articles", [])
                
                # Load price history for relevant tickers
                price_history = {}
                for tick in ticker:
                    try:
                        price_data = load_json(f"stock_prices_{tick.lower()}") or {}
                        if "data" in price_data:
                            price_history[tick.upper()] = price_data["data"]
                        else:
                            price_history[tick.upper()] = price_data.get("rows", [])  # Alternative structure
                    except:
                        # If specific price data not found, use empty list to maintain contract
                        price_history[tick.upper()] = []
                
                # Get news impact analysis from service
                result = news_analytics_service.get_news_impact_analysis(
                    articles=articles,
                    price_history=price_history,
                    tickers=[t.upper() for t in ticker],
                    days_back=days_back,
                    min_sentiment=min_sentiment,
                    max_sentiment=max_sentiment,
                    min_relevance=min_relevance,
                    source_filter=source
                )
                
                return result["data"]  # Return just the data portion
                
            except Exception as e:
                print(f"Error in news analysis computation: {str(e)}")
                
                # Return structured fallback to maintain never-empty contract
                fallback_result = {
                    "articles_analyzed": 0,
                    "impacts": {},
                    "summary_by_ticker": {
                        t: {
                            "total_articles": 0,
                            "avg_impact": 0.0,
                            "total_impact": 0.0,
                            "positive_articles": 0,
                            "negative_articles": 0,
                            "neutral_articles": 0,
                            "avg_sentiment": 0.0,
                            "most_impactful_article": None,
                            "generated_at": datetime.utcnow().isoformat() + "Z"
                        } for t in ticker
                    },
                    "total_mentions": 0,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "parameters": {
                        "tickers": ticker,
                        "days_back": days_back,
                        "min_sentiment": min_sentiment,
                        "max_sentiment": max_sentiment,
                        "min_relevance": min_relevance,
                        "source_filter": source
                    },
                    "source": ["news_analysis_route", "error_fallback", "fc-api-030"],
                    "error": str(e),
                    "message": "News impact analysis computation failed but fallback data generated to maintain never-empty contract"
                }
                
                return fallback_result
        
        # Use cache layer to serve latest available data, compute fresh if none available
        analysis_key = f"news_analysis_{'_'.join(sorted([t.upper() for t in ticker]))}_{days_back}d_{min_sentiment}_{max_sentiment}"
        analysis_data = load_or_compute(
            key=analysis_key,
            compute_fn=compute_news_analysis,
            source=["news_analysis_route", "impact_calculation", "fc-api-030"]
        )
        
        # Ensure proper response format
        if not isinstance(analysis_data, dict):
            analysis_data = {
                "articles_analyzed": 0,
                "impacts": {},
                "summary_by_ticker": {},
                "total_mentions": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "message": "Invalid data format returned from news analyzer, using fallback to maintain never-empty contract",
                "source": ["news_analysis_route", "format_fallback", "fc-api-030"]
            }
        
        return {
            "ok": True,  # Always true to maintain never-empty contract
            "data": analysis_data,
            "freshness": analysis_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
        
    except Exception as e:
        print(f"Error in /news/analysis endpoint: {str(e)}")
        
        # Return structured fallback to maintain never-empty contract
        return {
            "ok": True,  # Always maintain never-empty contract
            "data": {
                "articles_analyzed": 0,
                "impacts": {},
                "summary_by_ticker": {
                    t: {
                        "total_articles": 0,
                        "avg_impact": 0.0,
                        "total_impact": 0.0,
                        "positive_articles": 0,
                        "negative_articles": 0,
                        "neutral_articles": 0,
                        "avg_sentiment": 0.0,
                        "most_impactful_article": None,
                        "generated_at": datetime.utcnow().isoformat() + "Z"
                    } for t in ticker
                },
                "total_mentions": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "parameters": {
                    "tickers": ticker,
                    "days_back": days_back,
                    "min_sentiment": min_sentiment,
                    "max_sentiment": max_sentiment,
                    "min_relevance": min_relevance,
                    "source_filter": source
                },
                "error": str(e),
                "message": "News impact analysis endpoint failed but fallback data returned to maintain never-empty contract",
                "source": ["news_analysis_route", "endpoint_error_fallback", "fc-api-030"]
            },
            "freshness": "error"
        }

# Additional endpoint for correlation analysis between news sentiment and price movements
@router.get("/news/correlation")
async def news_price_correlation(
    ticker: str = Query(..., description="Ticker à analyser (ex: NVDA)"),
    days_back: int = Query(30, ge=1, le=365, description="Nombre de jours d'historique"),
    news_source: Optional[str] = Query(None, description="Source spécifique pour analyse")
):
    """
    Get correlation between news sentiment and price movements for specific ticker.
    Useful for understanding how markets react to news sentiment.
    """
    try:
        def compute_correlation():
            """Compute fresh correlation between news sentiment and price movements"""
            try:
                # Load recent news articles
                news_data = load_json("news_feed") or {}
                articles = news_data.get("articles", [])
                
                # Load price history
                price_data = load_json(f"stock_prices_{ticker.lower()}") or {}
                if "data" in price_data:
                    price_history = {ticker.upper(): price_data["data"]}
                else:
                    price_history = {ticker.upper(): price_data.get("rows", [])}
                
                # Get correlation from news impact model
                from models.news_impact import news_impact_model
                correlation_result = news_impact_model.calculate_correlation_news_price(
                    articles=articles,
                    price_history=price_history,
                    ticker=ticker
                )
                
                return correlation_result
                
            except Exception as e:
                print(f"Error in correlation computation: {str(e)}")
                
                # Return fallback correlation data
                return {
                    "correlation": 0.0,
                    "sentiment_price_correlation": 0.0,
                    "count": 0,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "parameters": {
                        "ticker": ticker,
                        "days_back": days_back,
                        "news_source": news_source
                    },
                    "error": str(e),
                    "message": "News-price correlation computation failed but fallback data returned to maintain never-empty contract"
                }
        
        correlation_key = f"news_price_corr_{ticker.upper()}_{days_back}d_{news_source or 'any'}"
        correlation_data = load_or_compute(
            key=correlation_key,
            compute_fn=compute_correlation,
            source=["news_correlation_route", "sentiment_price_analysis", "fc-api-030"]
        )
        
        return {
            "ok": True,  # Maintain never-empty contract
            "data": correlation_data,
            "freshness": correlation_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
        
    except Exception as e:
        print(f"Error in /news/correlation endpoint: {str(e)}")
        
        return {
            "ok": True,  # Maintain never-empty contract
            "data": {
                "correlation": 0.0,
                "sentiment_price_correlation": 0.0,
                "count": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "parameters": {
                    "ticker": ticker,
                    "days_back": days_back,
                    "news_source": news_source
                },
                "error": str(e),
                "message": "News-price correlation endpoint failed but fallback data returned to maintain never-empty contract"
            },
            "freshness": "error"
        }