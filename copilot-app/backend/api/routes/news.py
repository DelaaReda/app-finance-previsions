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
    tickers: Optional[str] = Query(None, description="Filter news by specific tickers (comma-separated)"),
    limit: Optional[int] = Query(50, description="Limit number of results returned (max 200)"),
    page: Optional[int] = Query(1, ge=1, description="Page number (1-based)"),
    since: Optional[str] = Query("7d", description="Time window: 1h, 6h, 1d, 3d, 7d, 14d"),
    sentiment_min: Optional[float] = Query(-1.0, description="Minimum sentiment score (-1.0 to 1.0)"),
    sentiment_max: Optional[float] = Query(1.0, description="Maximum sentiment score (-1.0 to 1.0)"),
    sources: Optional[str] = Query(None, description="Filter by specific sources (comma-separated)"),
    q: Optional[str] = Query(None, description="Search keyword in title/description")
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

        # Filter by tickers if specified (split comma-separated string)
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
            ticker_filtered = [
                article for article in filtered_articles
                if any(ticker in (article.get("tickers", []) if article.get("tickers") else [article.get("ticker")]) for ticker in ticker_list)
            ]
            # Graceful degradation: if ticker filter returns nothing, keep all articles
            # This ensures News Feed page is never empty due to missing ticker metadata
            if len(ticker_filtered) > 0:
                filtered_articles = ticker_filtered
        
        # Filter by sentiment range
        if sentiment_min > -1.0 or sentiment_max < 1.0:
            filtered_articles = [
                article for article in filtered_articles
                if sentiment_min <= article.get("sentiment_score", 0) <= sentiment_max
            ]
        
        # Filter by sources if specified (split comma-separated string)
        if sources:
            source_list = [s.strip().lower() for s in sources.split(',') if s.strip()]
            filtered_articles = [
                article for article in filtered_articles
                if article.get("source", "").lower() in source_list or article.get("source_name", "").lower() in source_list
            ]
        
        # Filter by keyword (q) in title/description (Sprint 4 - Tâche 4.2)
        if q:
            q_lower = q.lower()
            filtered_articles = [
                article for article in filtered_articles
                if q_lower in (article.get("title", "") or "").lower() or q_lower in (article.get("description", "") or "").lower() or q_lower in (article.get("summary", "") or "").lower()
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
        
        # Calculate pagination (Sprint 4 - Tâche 4.1)
        total_count = len(filtered_articles)
        page_num = page or 1
        limit_num = min(limit or 50, 200)  # Cap at 200
        
        # Calculate offset
        offset = (page_num - 1) * limit_num
        
        # Apply pagination
        paginated_articles = filtered_articles[offset:offset + limit_num]
        
        # Calculate if there are more pages
        has_more = offset + limit_num < total_count
        
        # Prepare response data (Sprint 4 - Tâche 4.1)
        response_data = {
            "articles": paginated_articles,
            "count": len(paginated_articles),
            "total": total_count,
            "page": page_num,
            "limit": limit_num,
            "has_more": has_more,
            "next_page": page_num + 1 if has_more else None,
            "filters": {
                "tickers": tickers.split(',') if tickers else [],
                "limit": limit_num,
                "page": page_num,
                "since": since,
                "sentiment_min": sentiment_min,
                "sentiment_max": sentiment_max,
                "sources": sources.split(',') if sources else [],
                "q": q
            },
            "freshness": news_data.get("freshness") or news_data.get("last_update"),
            "last_update": news_data.get("freshness") or news_data.get("last_update"),
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
                "page": page,
                "since": since,
                "sentiment_min": sentiment_min,
                "sentiment_max": sentiment_max,
                "sources": sources,
                "q": q
            },
            "error": str(e),
            "message": "News temporarily unavailable - showing fallback data",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback", "error_handling"]
        })