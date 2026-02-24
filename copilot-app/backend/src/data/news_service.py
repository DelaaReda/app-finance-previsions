#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
News Service for FastAPI
Expose Bronze/Silver/Gold news data with efficient queries.

Endpoints:
- /news/feed - Get filtered news feed (Silver layer)
- /news/features/daily - Get daily ticker features (Gold layer)
- /news/tickers - Get tickers with news for date
- /news/stats - Get news statistics

Author: AI Assistant
Created: 2025-10-30
"""

import datetime as dt
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

import duckdb
import pandas as pd

# Assume these paths relative to project root
SILVER_DIR = Path("data/news/silver")
GOLD_DIR = Path("data/news/gold")

# =======================
# Response Models
# =======================

@dataclass
class NewsArticle:
    """Silver layer news article."""
    id: str
    title: str
    url: str
    source_domain: str
    source_tier: str
    published_at: str  # ISO format
    lang: str
    tickers: List[str]
    topics: List[str]
    sentiment: Dict[str, float]
    quality: Dict[str, float]
    relevance: float
    summary: Optional[str] = None
    text_preview: Optional[str] = None  # First 500 chars


@dataclass
class DailyFeatures:
    """Gold layer daily features."""
    date: str  # YYYY-MM-DD
    ticker: str
    news_count: int
    news_novelty: float
    sent_mean: float
    sent_pos_share: float
    sent_neg_share: float
    top_topics: List[str]
    source_tier1_share: float


@dataclass
class NewsStats:
    """Statistics about news data."""
    date_range: Dict[str, str]  # min, max dates
    total_articles: int
    unique_tickers: int
    unique_sources: int
    avg_articles_per_day: float
    top_tickers: List[Dict[str, Any]]  # Top 10 by article count


# =======================
# Service Class
# =======================

class NewsService:
    """Service for querying news data."""
    
    def __init__(self):
        self.conn = duckdb.connect(":memory:")
    
    def get_feed(self,
                 tickers: Optional[List[str]] = None,
                 topics: Optional[List[str]] = None,
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None,
                 source_tier: Optional[str] = None,
                 min_relevance: float = 0.0,
                 limit: int = 100,
                 offset: int = 0) -> List[NewsArticle]:
        """
        Get filtered news feed from Silver layer.
        
        Args:
            tickers: Filter by ticker symbols
            topics: Filter by topics
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            source_tier: Filter by source tier (Tier1/Tier2)
            min_relevance: Minimum relevance score
            limit: Max results
            offset: Pagination offset
        
        Returns:
            List of NewsArticle objects
        """
        # Build date pattern
        if start_date and end_date:
            # Query specific date range
            start = pd.to_datetime(start_date).date()
            end = pd.to_datetime(end_date).date()
            date_patterns = []
            current = start
            while current <= end:
                date_patterns.append(f"dt={current.strftime('%Y-%m-%d')}")
                current += dt.timedelta(days=1)
            pattern = str(SILVER_DIR / f"{{{','.join(date_patterns)}}}" / "*.parquet")
        else:
            # Query all dates
            pattern = str(SILVER_DIR / "dt=*/*.parquet")
        
        # Build query
        query = f"""
        SELECT 
            id,
            title,
            url,
            source_domain,
            source_tier,
            published_at,
            lang,
            tickers,
            topics,
            sentiment,
            quality,
            relevance,
            summary,
            substr(text, 1, 500) as text_preview
        FROM read_parquet('{pattern}')
        WHERE parent_id IS NULL  -- Only non-duplicates
        """
        params: List[Any] = []

        # Add filters (parameterized)
        if tickers:
            ticker_conditions = " OR ".join(["list_contains(tickers, ?)" for _ in tickers])
            query += f" AND ({ticker_conditions})"
            params.extend([t.upper() for t in tickers])

        if topics:
            topic_conditions = " OR ".join(["list_contains(topics, ?)" for _ in topics])
            query += f" AND ({topic_conditions})"
            params.extend(topics)

        if source_tier:
            query += " AND source_tier = ?"
            params.append(source_tier)

        if start_date:
            query += " AND published_at >= ?"
            params.append(start_date)

        if end_date:
            query += " AND published_at <= ?"
            params.append(f"{end_date} 23:59:59")

        if min_relevance > 0:
            query += " AND relevance >= ?"
            params.append(float(min_relevance))

        # Order by published date (most recent first)
        query += " ORDER BY published_at DESC"

        # Pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])

        try:
            df = self.conn.execute(query, params).df()
            
            # Convert to NewsArticle objects
            articles = []
            for _, row in df.iterrows():
                article = NewsArticle(
                    id=row["id"],
                    title=row["title"],
                    url=row["url"],
                    source_domain=row["source_domain"],
                    source_tier=row["source_tier"],
                    published_at=row["published_at"].isoformat() if pd.notna(row["published_at"]) else None,
                    lang=row["lang"],
                    tickers=row["tickers"] if row["tickers"] else [],
                    topics=row["topics"] if row["topics"] else [],
                    sentiment=row["sentiment"] if isinstance(row["sentiment"], dict) else {"polarity": 0.0, "subjectivity": 0.0},
                    quality=row["quality"] if isinstance(row["quality"], dict) else {"credibility": 0.5, "completeness": 0.5, "noise": 0.5},
                    relevance=float(row["relevance"]) if pd.notna(row["relevance"]) else 0.0,
                    summary=row["summary"] if pd.notna(row["summary"]) else None,
                    text_preview=row["text_preview"] if pd.notna(row["text_preview"]) else None
                )
                articles.append(article)
            
            return articles
        
        except Exception as e:
            print(f"ERROR querying feed: {e}")
            return []
    
    def get_daily_features(self,
                          ticker: Optional[str] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          min_news_count: int = 0) -> List[DailyFeatures]:
        """
        Get daily features from Gold layer.
        
        Args:
            ticker: Filter by ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            min_news_count: Minimum news count threshold
        
        Returns:
            List of DailyFeatures objects
        """
        pattern = str(GOLD_DIR / "features_daily/dt=*/final.parquet")
        
        query = f"""
        SELECT * 
        FROM read_parquet('{pattern}')
        WHERE 1=1
        """
        params: List[Any] = []

        if ticker:
            query += " AND ticker = ?"
            params.append(ticker.upper())

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        if min_news_count > 0:
            query += " AND news_count >= ?"
            params.append(int(min_news_count))

        query += " ORDER BY date DESC, ticker"

        try:
            df = self.conn.execute(query, params).df()
            
            features = []
            for _, row in df.iterrows():
                feature = DailyFeatures(
                    date=row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
                    ticker=row["ticker"],
                    news_count=int(row["news_count"]),
                    news_novelty=float(row["news_novelty"]) if pd.notna(row["news_novelty"]) else 0.0,
                    sent_mean=float(row["sent_mean"]) if pd.notna(row["sent_mean"]) else 0.0,
                    sent_pos_share=float(row["sent_pos_share"]) if pd.notna(row["sent_pos_share"]) else 0.0,
                    sent_neg_share=float(row["sent_neg_share"]) if pd.notna(row["sent_neg_share"]) else 0.0,
                    top_topics=row["top_topics"] if row["top_topics"] else [],
                    source_tier1_share=float(row["source_tier1_share"]) if pd.notna(row["source_tier1_share"]) else 0.0
                )
                features.append(feature)
            
            return features
        
        except Exception as e:
            print(f"ERROR querying features: {e}")
            return []
    
    def get_tickers_for_date(self, date: str) -> List[str]:
        """
        Get list of tickers with news for a given date.
        
        Args:
            date: Date (YYYY-MM-DD)
        
        Returns:
            List of ticker symbols
        """
        pattern = str(GOLD_DIR / f"features_daily/dt={date}/final.parquet")
        
        try:
            df = self.conn.execute(f"""
                SELECT DISTINCT ticker 
                FROM read_parquet('{pattern}')
                ORDER BY ticker
            """).df()
            
            return df["ticker"].tolist()
        
        except Exception as e:
            print(f"ERROR getting tickers: {e}")
            return []
    
    def get_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> NewsStats:
        """
        Get statistics about news data.
        
        Args:
            start_date: Start date (YYYY-MM-DD), optional
            end_date: End date (YYYY-MM-DD), optional
        
        Returns:
            NewsStats object
        """
        pattern = str(SILVER_DIR / "dt=*/*.parquet")
        
        # Build base query
        where_clause = "WHERE parent_id IS NULL"
        where_params: List[Any] = []

        if start_date:
            where_clause += " AND published_at >= ?"
            where_params.append(start_date)
        if end_date:
            where_clause += " AND published_at <= ?"
            where_params.append(f"{end_date} 23:59:59")

        try:
            # Get overall stats
            stats_query = f"""
            SELECT 
                MIN(published_at) as min_date,
                MAX(published_at) as max_date,
                COUNT(*) as total_articles,
                COUNT(DISTINCT source_domain) as unique_sources
            FROM read_parquet('{pattern}')
            {where_clause}
            """
            
            stats_df = self.conn.execute(stats_query, where_params).df()
            
            if stats_df.empty:
                return NewsStats(
                    date_range={"min": None, "max": None},
                    total_articles=0,
                    unique_tickers=0,
                    unique_sources=0,
                    avg_articles_per_day=0.0,
                    top_tickers=[]
                )
            
            row = stats_df.iloc[0]
            
            # Calculate date range
            min_date = row["min_date"]
            max_date = row["max_date"]
            
            if pd.notna(min_date) and pd.notna(max_date):
                days = (pd.to_datetime(max_date) - pd.to_datetime(min_date)).days + 1
                avg_per_day = row["total_articles"] / max(days, 1)
            else:
                avg_per_day = 0.0
            
            # Get unique tickers count
            tickers_query = f"""
            SELECT COUNT(DISTINCT ticker) as unique_tickers
            FROM (
                SELECT unnest(tickers) as ticker
                FROM read_parquet('{pattern}')
                {where_clause}
            )
            """
            
            tickers_df = self.conn.execute(tickers_query, where_params).df()
            unique_tickers = int(tickers_df.iloc[0]["unique_tickers"]) if not tickers_df.empty else 0
            
            # Get top tickers
            top_tickers_query = f"""
            SELECT 
                ticker,
                COUNT(*) as article_count
            FROM (
                SELECT unnest(tickers) as ticker
                FROM read_parquet('{pattern}')
                {where_clause}
            )
            GROUP BY ticker
            ORDER BY article_count DESC
            LIMIT 10
            """
            
            top_tickers_df = self.conn.execute(top_tickers_query, where_params).df()
            top_tickers = [
                {"ticker": row["ticker"], "count": int(row["article_count"])}
                for _, row in top_tickers_df.iterrows()
            ]
            
            return NewsStats(
                date_range={
                    "min": min_date.strftime("%Y-%m-%d") if pd.notna(min_date) else None,
                    "max": max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else None
                },
                total_articles=int(row["total_articles"]),
                unique_tickers=unique_tickers,
                unique_sources=int(row["unique_sources"]),
                avg_articles_per_day=round(avg_per_day, 2),
                top_tickers=top_tickers
            )
        
        except Exception as e:
            print(f"ERROR getting stats: {e}")
            return NewsStats(
                date_range={"min": None, "max": None},
                total_articles=0,
                unique_tickers=0,
                unique_sources=0,
                avg_articles_per_day=0.0,
                top_tickers=[]
            )


# =======================
# Singleton Instance
# =======================

_news_service = None

def get_news_service() -> NewsService:
    """Get singleton NewsService instance."""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service


# =======================
# Test/CLI
# =======================

if __name__ == "__main__":
    import json
    
    service = get_news_service()
    
    # Test feed query
    print("=== Testing News Feed ===")
    articles = service.get_feed(
        tickers=["AAPL", "MSFT"],
        start_date="2025-10-25",
        limit=5
    )
    print(f"Found {len(articles)} articles")
    for article in articles:
        print(f"  - {article.title} ({article.published_at})")
    
    # Test features query
    print("\n=== Testing Daily Features ===")
    features = service.get_daily_features(
        ticker="AAPL",
        start_date="2025-10-25",
        end_date="2025-10-30"
    )
    print(f"Found {len(features)} feature records")
    for feat in features:
        print(f"  - {feat.date}: {feat.news_count} articles, sent={feat.sent_mean:.2f}")
    
    # Test stats
    print("\n=== Testing Stats ===")
    stats = service.get_stats()
    print(json.dumps(asdict(stats), indent=2))
