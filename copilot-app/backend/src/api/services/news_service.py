"""
News service with persistent caching to ensure never-empty responses.
Addresses FC-P0-004 requirements for the news endpoint.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

# New imports for persistent caching
from backend.storage.json_storage import load_json, save_json
from backend.services.cache_service import load_or_compute

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
            key=key,
            compute_fn=compute_news_feed,
            sources=["news_pipeline", "rss_feeds", "api_sources"]
        )
        
        # Ensure the result has the expected format for the API
        if result and "data" not in result:
            # If load_or_compute returned raw computed data, wrap it properly
            return {
                "ok": result.get("error") is None,
                "data": result
            }
        else:
            # If load_or_compute returned cached data with metadata, use it as is
            return {
                "ok": result is not None and "error" not in (result.get("data", {}) or {}),
                "data": result.get("data", result) if result else {
                    "items": [], 
                    "count": 0, 
                    "generated_at": datetime.utcnow().isoformat()
                }
            }


# Global news service instance
news_service = NewsService()