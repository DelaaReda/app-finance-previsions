"""
News service with persistent caching to ensure never-empty responses.
Addresses FC-P0-004 requirements for the news endpoint.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

# New imports for persistent caching
from storage import load_json, save_json
from services import load_or_compute

# Import the existing news functionality
from ingestion.finnews import run_pipeline as run_news_pipeline
from api.schemas import (
    NewsArticle,
    NewsEvent,
    NewsEventValue,
    NewsEventsData,
    NewsFeedData,
    NewsFeedFilters,
    NewsScore,
    SentimentData,
    TraceMetadata,
)


class NewsService:
    def __init__(self):
        self.default_limit = 50
    
    async def get_news_feed(
        self,
        tickers: Optional[List[str]] = None,
        q: Optional[str] = None,
        limit: int = 50,
        window: str = "last_week"
    ) -> Dict[str, Any]:
        """
        Get news feed with persistent caching and fallback mechanisms.
        Returns real data or empty structure but never fails.
        """
        # Create a unique cache key based on parameters
        ticker_key = "_".join(tickers or ["all"])
        key = f"news_feed_{ticker_key}_{q or 'all'}_{limit}_{window}"
        
        async def compute_news_feed():
            try:
                # Run the existing news pipeline
                regions = ["US", "CA", "INTL"]
                tgt_ticker = tickers[0] if tickers and len(tickers) > 0 else None
                
                items = run_news_pipeline(
                    regions=regions,
                    window=window,
                    query=q or "",
                    tgt_ticker=tgt_ticker,
                    per_source_cap=None,
                    limit=limit
                )
                
                # Serialize the items
                serialized_items = []
                for item in items:
                    serialized_items.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "published": item.get("published", ""),
                        "source": item.get("source", ""),
                        "region": item.get("region"),
                        "summary": item.get("summary", ""),
                        "score": item.get("score", 0),
                        "importance": item.get("importance", 0),
                        "freshness": item.get("freshness", 0),
                        "relevance": item.get("relevance", 0),
                        "sentiment": item.get("sentiment", None),
                        "entities": item.get("entities", []),
                        "tickers": item.get("tickers", []),
                    })
                
                return {
                    "items": serialized_items,
                    "count": len(serialized_items),
                    "generated_at": datetime.utcnow().isoformat(),
                    "source": "news_pipeline"
                }
            except Exception as e:
                # Fallback: return structured empty response instead of failing
                return {
                    "items": [],
                    "count": 0,
                    "error": str(e),
                    "generated_at": datetime.utcnow().isoformat(),
                    "source": "error_fallback"
                }
        
        # Use load_or_compute to get data with persistent caching
        result = await load_or_compute(
            key,
            compute_news_feed,
            ["news_pipeline", "rss_feeds", "api_sources"]
        )
        
        # Prepare the response with freshness info at the top level
        if result and isinstance(result, dict) and "data" in result:
            # This is cached data with metadata, return with freshness info
            api_response = result["data"].copy() if isinstance(result["data"], dict) else {"items": [], "count": 0}
            api_response["freshness"] = result.get("freshness", "unknown")
            api_response["last_update"] = result.get("last_update")
            api_response["source"] = result.get("source", [])
            
            return {
                "ok": "error" not in (result.get("data", {}) or {}),
                "data": api_response
            }
        else:
            # This is computed data without cache metadata, add basic freshness info
            api_response = result if isinstance(result, dict) else {"items": [], "count": 0, "generated_at": datetime.utcnow().isoformat()}
            api_response["freshness"] = "fresh"
            api_response["last_update"] = datetime.utcnow().isoformat()
            api_response["source"] = ["realtime_calculation"]
            
            return {
                "ok": "error" not in (result or {}),
                "data": api_response
            }


# Global news service instance
news_service = NewsService()


# Wrapper functions for direct imports (for compatibility with __init__.py)
async def get_news_feed(tickers=None, q=None, limit=50, window="last_week"):
    """Wrapper function for news_service.get_news_feed"""
    return await news_service.get_news_feed(tickers, q, limit, window)


async def get_news_events(tickers=None, q=None, limit=50, window="last_week"):
    """Wrapper function for news_service.get_news (placeholder implementation)"""
    # Placeholder implementation - return empty response
    return {"events": [], "count": 0}


async def get_sentiment(tickers=None, q=None, limit=50, window="last_week"):
    """Wrapper function for news_service.get_sentiment (placeholder implementation)"""
    # Placeholder implementation - return neutral sentiment
    return {"sentiment": [], "average": 0.0, "count": 0}
