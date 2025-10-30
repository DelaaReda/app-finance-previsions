# src/api/services/news_service.py
"""
News service facade - wraps ingestion/finnews.py
Provides news feed with scoring and filtering.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

from api.schemas import (
    NewsFeedData, NewsArticle, NewsScore, NewsFeedFilters,
    SentimentData, TraceMetadata
)

# Try to import finnews
try:
    from ingestion.finnews import (
        run_pipeline,
        build_news_features,
        NewsItem
    )
    HAS_FINNEWS = True
except ImportError:
    HAS_FINNEWS = False
    NewsItem = None


def _hash_data(data: Any) -> str:
    """Generate SHA256 hash of data."""
    content = str(data).encode('utf-8')
    return hashlib.sha256(content).hexdigest()[:32]


def _create_trace(source: str, asof: date, data: Any) -> TraceMetadata:
    """Create trace metadata."""
    return TraceMetadata(
        created_at=datetime.utcnow(),
        source=source,
        asof_date=asof,
        hash=_hash_data(data)
    )


def _parse_since(since: str) -> str:
    """Convert since parameter to finnews window format."""
    mapping = {
        "1h": "1h",
        "6h": "6h",
        "1d": "24h",
        "3d": "48h",  # Approximate
        "7d": "last_week",
        "14d": "last_week",  # Fallback
        "30d": "last_month",
        "90d": "last_month",  # Fallback
    }
    return mapping.get(since, "last_week")


def _convert_news_item(item: NewsItem, score_min: float = 0.0) -> Optional[NewsArticle]:
    """
    Convert finnews NewsItem to API NewsArticle schema.
    
    Args:
        item: finnews.NewsItem object
        score_min: Minimum score filter
    
    Returns:
        NewsArticle or None if filtered out
    """
    try:
        # Calculate scores
        importance = getattr(item, 'importance', None) or 0.5
        freshness = getattr(item, 'freshness', None) or 0.5
        relevance = getattr(item, 'relevance', None) or 0.5
        
        # Total score (composite)
        total_score = importance * 0.4 + freshness * 0.4 + relevance * 0.2
        
        # Filter by minimum score
        if total_score < score_min:
            return None
        
        # Create NewsScore
        score = NewsScore(
            total=total_score,
            freshness=freshness,
            source_quality=importance,  # Use importance as proxy
            relevance=relevance
        )
        
        # Parse published date
        published = item.published
        if isinstance(published, str):
            published = datetime.fromisoformat(published.replace('Z', '+00:00'))
        
        # Get tickers
        tickers = getattr(item, 'tickers', []) or []
        if not isinstance(tickers, list):
            tickers = [str(tickers)]
        
        # Create trace
        trace = _create_trace(
            source=item.source or "RSS",
            asof=published.date() if isinstance(published, datetime) else date.today(),
            data=item.id
        )
        
        # Build NewsArticle
        article = NewsArticle(
            id=item.id,
            title=item.title,
            summary=item.summary,
            url=item.link,
            source=item.source or "Unknown",
            published_at=published if isinstance(published, datetime) else datetime.fromisoformat(published.replace('Z', '+00:00')),
            tickers=tickers,
            score=score,
            trace=trace
        )
        
        return article
        
    except Exception as e:
        print(f"⚠️  Failed to convert news item: {e}")
        return None


def get_news_feed(
    tickers: Optional[str] = None,
    since: str = "7d",
    score_min: float = 0.0,
    region: str = "all",
    limit: int = 50
) -> NewsFeedData:
    """
    Get news feed with scoring and filtering.
    
    Args:
        tickers: Comma-separated ticker symbols (e.g., "AAPL,MSFT")
        since: Time period (1h, 6h, 1d, 3d, 7d, 14d, 30d, 90d)
        score_min: Minimum composite score (0.0 to 1.0)
        region: Geographic region (US, CA, EU, INTL, all)
        limit: Maximum number of articles
    
    Returns:
        NewsFeedData with filtered articles
    """
    if not HAS_FINNEWS:
        # Return empty feed with warning
        trace = _create_trace("mock", date.today(), "finnews_unavailable")
        return NewsFeedData(
            articles=[],
            count=0,
            total=0,
            filters=NewsFeedFilters(
                tickers=None,
                since=since,
                score_min=score_min,
                region=region
            ),
            trace=trace
        )
    
    # Parse parameters
    ticker_list = [t.strip() for t in tickers.split(",")] if tickers else None
    window = _parse_since(since)
    
    # Map region to finnews regions
    region_map = {
        "US": ["US"],
        "CA": ["CA"],
        "EU": ["FR", "DE"],
        "INTL": ["INTL", "GEO"],
        "all": ["US", "CA", "FR", "DE", "INTL", "GEO"]
    }
    regions = region_map.get(region, ["US", "INTL"])
    
    # Build query for tickers if specified
    query = " OR ".join(ticker_list) if ticker_list else ""
    
    # Run finnews pipeline
    try:
        items = run_pipeline(
            regions=regions,
            window=window,
            query=query,
            tgt_ticker=ticker_list[0] if ticker_list and len(ticker_list) == 1 else None,
            per_source_cap=20,  # Limit per source to avoid overload
            limit=limit * 2  # Fetch more to account for filtering
        )
    except Exception as e:
        print(f"⚠️  Finnews pipeline failed: {e}")
        items = []
    
    # Convert to API schema
    articles = []
    for item in items:
        article = _convert_news_item(item, score_min=score_min)
        if article:
            articles.append(article)
        if len(articles) >= limit:
            break
    
    # Create filters object
    filters = NewsFeedFilters(
        tickers=ticker_list,
        since=since,
        score_min=score_min,
        region=region
    )
    
    # Create trace
    trace = _create_trace(
        source="finnews",
        asof=date.today(),
        data={"count": len(articles), "total": len(items)}
    )
    
    return NewsFeedData(
        articles=articles,
        count=len(articles),
        total=len(items),
        filters=filters,
        trace=trace
    )


def get_sentiment(limit: int = 100) -> SentimentData:
    """
    Get aggregated sentiment by ticker.
    
    Args:
        limit: Max articles to analyze
    
    Returns:
        SentimentData with sentiment scores
    """
    if not HAS_FINNEWS:
        trace = _create_trace("mock", date.today(), "finnews_unavailable")
        return SentimentData(
            sentiment={},
            count=0,
            trace=trace
        )
    
    try:
        # Fetch recent news
        items = run_pipeline(
            regions=["US", "INTL"],
            window="last_week",
            query="",
            limit=limit
        )
        
        # Build features (aggregates by ticker)
        features = build_news_features(items)
        
        # Extract mean sentiment per ticker
        sentiment = {}
        for ticker, feats in features.items():
            mean_sent = feats.get("mean_sentiment", 0.0)
            sentiment[ticker] = mean_sent
        
        trace = _create_trace("finnews", date.today(), sentiment)
        
        return SentimentData(
            sentiment=sentiment,
            count=len(sentiment),
            trace=trace
        )
        
    except Exception as e:
        print(f"⚠️  Sentiment aggregation failed: {e}")
        trace = _create_trace("finnews/error", date.today(), str(e))
        return SentimentData(
            sentiment={},
            count=0,
            trace=trace
        )
