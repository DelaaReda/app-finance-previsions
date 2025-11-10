"""
API Routes for News - Dashboard Integration
Provides filtered news data for the dashboard with never-empty guarantee
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timedelta, timezone

from core.response import ok, err
from storage.io import load_json
import logging

logger = logging.getLogger(__name__)

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
        
        # Remove duplicates by URL (fix for issue #5)
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if not isinstance(article, dict):
                continue
            url = article.get("url") or article.get("link")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
            elif not url:
                # Keep articles without URL but with unique title+date
                article_id = f"{article.get('title', '')}_{article.get('pubDate', '')}"
                if article_id not in seen_urls:
                    seen_urls.add(article_id)
                    unique_articles.append(article)
        
        # Filter out articles with empty URLs (optional - can be enabled if needed)
        # unique_articles = [a for a in unique_articles if a.get("url") or a.get("link")]
        
        all_articles = unique_articles
        
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
                    cutoff_utc = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                    
                    filtered_articles = [
                        article for article in filtered_articles
                        if article.get("pubDate") and _safe_parse_date(article["pubDate"]) and _safe_parse_date(article["pubDate"]) > cutoff_utc
                    ]
                except ValueError:
                    # If parsing fails, skip date filtering
                    pass
        
        # Sort by publication date (most recent first)
        filtered_articles = sorted(
            filtered_articles,
            key=lambda x: _safe_parse_date(x.get("pubDate", "")) or datetime.min,
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
        
        # Enhance response for frontend consumption with additional metrics
        # Format articles to support frontend components like NewsFeed.tsx
        enhanced_articles = []
        for article in paginated_articles:
            # Enhance each article with frontend-required fields
            enhanced_article = {
                "id": article.get("id") or article.get("url") or f"news_{hash(article.get('title', '') + article.get('pubDate', ''))}",
                "title": article.get("title", ""),
                "description": article.get("description", "") or article.get("summary", ""),
                "url": article.get("url") or article.get("link", ""),
                "pubDate": article.get("pubDate") or article.get("published_at") or article.get("timestamp") or "",
                "source": article.get("source") or article.get("publisher") or "Unknown",
                "tickers": article.get("tickers") or article.get("symbols") or [],
                "sentiment": {
                    "score": article.get("sentiment_score", 0),
                    "label": _get_sentiment_label(article.get("sentiment_score", 0)),
                    "magnitude": abs(article.get("sentiment_score", 0))
                },
                "score": article.get("score") or article.get("confidence", 0.5),
                "themes": article.get("themes") or article.get("tags", []),
                "summary": article.get("summary") or article.get("description", ""),
                # For frontend timeago display:
                "timeago": _calculate_timeago(article.get("pubDate", "")),
                # For frontend categorization:
                "category": article.get("category") or _infer_category(article),
                "thumbnail": article.get("thumbnail") or article.get("image_url") or "",
                "read_time": article.get("read_time") or _estimate_read_time(article.get("content", ""))
            }
            enhanced_articles.append(enhanced_article)
        
        # Update the response with enhanced articles
        response_data["articles"] = enhanced_articles
        
        return ok(response_data)
    
    except Exception as e:
        # Return structured response even on error to maintain never-empty contract
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in news feed endpoint: {str(e)}", exc_info=True)
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


def _get_sentiment_label(sentiment_score: float) -> str:
    """Helper to convert numeric sentiment score to human-readable label."""
    if sentiment_score >= 0.6:
        return "very-positive"
    elif sentiment_score >= 0.2:
        return "positive"
    elif sentiment_score >= -0.2:
        return "neutral"
    elif sentiment_score >= -0.6:
        return "negative"
    else:
        return "very-negative"


def _calculate_timeago(pub_date: str) -> str:
    """Helper to calculate relative time ago string."""
    try:
        from datetime import datetime
        if not pub_date:
            return "Just now"
        
        # Parse the date string
        if "T" in pub_date:
            dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00").replace("z", "+00:00"))
        else:
            dt = datetime.fromisoformat(pub_date)
        
        diff = datetime.utcnow() - dt.replace(tzinfo=None) if dt.tzinfo else datetime.utcnow() - dt
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago" if hours > 1 else "1h ago"
        elif diff.seconds >= 60:
            mins = diff.seconds // 60
            return f"{mins}m ago" if mins > 1 else "1m ago"
        else:
            return "Just now"
    except:
        return "Unknown"


def _infer_category(article: Dict[str, Any]) -> str:
    """Helper to infer article category from content or keywords."""
    title = article.get("title", "").lower()
    content = article.get("content", "").lower()
    
    # Common categories based on keywords
    if any(word in title or word in content for word in ["earnings", "quarter", "revenue", "profit", "report"]):
        return "earnings"
    elif any(word in title or word in content for word in ["merger", "acquisition", "acquire", "buyout"]):
        return "mergers"
    elif any(word in title or word in content for word in ["ipo", "public", "shares", "debut"]):
        return "ipos"
    elif any(word in title or word in content for word in ["fed", "interest", "policy", "rates", "monetary"]):
        return "policy"
    elif any(word in title or word in content for word in ["crypto", "bitcoin", "ethereum", "blockchain"]):
        return "crypto"
    elif any(word in title or word in content for word in ["tech", "technology", "software", "cloud", "ai", "artificial intelligence"]):
        return "technology"
    else:
        return "general"


def _estimate_read_time(content: str) -> int:
    """Helper to estimate read time based on content length."""
    words_per_minute = 225  # Average reading speed
    if not content:
        return 1  # Minimum 1 minute
    
    word_count = len(content.split())
    minutes = max(1, round(word_count / words_per_minute))
    return minutes


def _safe_parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Safely parse date string, return None if parsing fails"""
    if not date_str:
        return None
    try:
        # Try ISO format first
        if "T" in date_str or "Z" in date_str:
            parsed_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # Make sure it's timezone-aware
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            return parsed_date
        # Try other common formats
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                # Make it timezone-aware
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                return parsed_date
            except ValueError:
                continue
        return None
    except (ValueError, AttributeError, TypeError):
        return None


# Export router
news_router = router