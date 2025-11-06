"""
API Routes for News - Dashboard Integration
Provides filtered news data for the dashboard with never-empty guarantee
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timedelta

from core.response import ok, err
from storage.io import load_json

router = APIRouter()

@router.get("/news/feed")
def get_filtered_news(
    tickers: Optional[List[str]] = Query(None, description="Filter news by specific tickers"),
    limit: Optional[int] = Query(50, description="Limit number of results returned"),
    since: Optional[str] = Query("7d", description="Time window: 1h, 6h, 1d, 3d, 7d, 14d"),
    sentiment_min: Optional[float] = Query(-1.0, description="Minimum sentiment score (-1.0 to 1.0)"),
    sentiment_max: Optional[float] = Query(1.0, description="Maximum sentiment score (-1.0 to 1.0)"),
    sources: Optional[List[str]] = Query(None, description="Filter by specific sources (reuters, bloomberg, etc.)")
) -> Dict[str, Any]:
    """
    Dashboard news endpoint with filtering capabilities.
    Returns news data with proper structure for dashboard UI components.
    """
    try:
        # Load news from persistent storage (following never-empty pattern)
        news_data = load_json("news_feed")
        
        if not news_data:
            # Return empty structure with metadata but never fail
            return ok({
                "articles": [],
                "count": 0,
                "filtered_params": {
                    "tickers": tickers,
                    "limit": limit,
                    "since": since,
                    "sentiment_min": sentiment_min,
                    "sentiment_max": sentiment_max,
                    "sources": sources
                },
                "message": "No news data available - system ingesting in background",
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback_empty"]
            })
        
        # Extract news articles
        data_payload = news_data.get("data", news_data.get("payload", news_data))
        all_articles = data_payload.get("articles", data_payload if isinstance(data_payload, list) else [])
        
        # Apply filtering
        filtered_articles = all_articles
        
        # Filter by tickers if specified
        if tickers:
            filtered_articles = [
                article for article in filtered_articles
                if any(ticker in (article.get("tickers", []) if article.get("tickers") else [article.get("ticker")]) for ticker in tickers)
            ]
        
        # Filter by sentiment range
        if sentiment_min > -1.0 or sentiment_max < 1.0:
            filtered_articles = [
                article for article in filtered_articles
                if sentiment_min <= article.get("sentiment_score", 0) <= sentiment_max
            ]
        
        # Filter by sources if specified
        if sources:
            filtered_articles = [
                article for article in filtered_articles
                if article.get("source") in sources or article.get("source_name") in sources
            ]
        
        # Filter by date range
        if since:
            # Parse the time window
            time_multiplier = {"h": 1, "d": 24, "w": 168, "m": 720, "y": 8760}  # hours in each period
            if len(since) > 1 and since[-1] in time_multiplier:
                try:
                    num = int(since[:-1])
                    hours_back = num * time_multiplier[since[-1]]
                    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                    
                    filtered_articles = [
                        article for article in filtered_articles
                        if article.get("pubDate") and datetime.fromisoformat(article["pubDate"].replace("Z", "+00:00")) > cutoff_time
                    ]
                except ValueError:
                    # If parsing fails, skip date filtering
                    pass
        
        # Sort by publication date (most recent first)
        filtered_articles = sorted(
            filtered_articles,
            key=lambda x: datetime.fromisoformat(x.get("pubDate", "").replace("Z", "+00:00")) if x.get("pubDate", "") else datetime.min,
            reverse=True
        )
        
        # Apply limit
        if limit and limit > 0:
            filtered_articles = filtered_articles[:limit]
        
        # Prepare response data
        response_data = {
            "articles": filtered_articles,
            "count": len(filtered_articles),
            "filtered_params": {
                "tickers": tickers,
                "limit": limit,
                "since": since,
                "sentiment_min": sentiment_min,
                "sentiment_max": sentiment_max,
                "sources": sources
            },
            "freshness": news_data.get("freshness") or news_data.get("last_update"),
            "generated_at": datetime.utcnow().isoformat(),
            "source": news_data.get("source", ["news_pipeline"])
        }
        
        return ok(response_data)
        
    except Exception as e:
        # Return structured response even on error to maintain never-empty contract
        return ok({
            "articles": [],
            "count": 0,
            "filtered_params": {
                "tickers": tickers,
                "limit": limit,
                "since": since,
                "sentiment_min": sentiment_min,
                "sentiment_max": sentiment_max,
                "sources": sources
            },
            "error": str(e),
            "message": "News temporarily unavailable - showing fallback data",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback", "error_handling"]
        })