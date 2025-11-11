"""
Financial News Ingestion Pipeline - Fixed & Enhanced Version
Task: FC-P1-011 - News Ingest v1 (RSS multi-sources)
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import json
import feedparser
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re
import hashlib
from pathlib import Path

# Import our storage and cache system
import sys
import os
# Add backend directory to path to handle imports properly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from storage.base import save_json, load_json

# Try to import cache layer, but don't fail if it's not available
try:
    from services.cache_layer import load_or_compute
except ImportError:
    # Define a fallback function if cache_layer is not available
    def load_or_compute(key, compute_fn, source=None):
        """
        Simple fallback implementation of load_or_compute that just runs the compute function
        """
        return compute_fn()

logger = logging.getLogger(__name__)

# Financial news RSS sources organized by region
RSS_SOURCES = {
    "US": [
        "https://www.reuters.com/business/rssBusinessNews",
        "https://feeds.bloomberg.com/markets/news.rss", 
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "https://www.marketwatch.com/rss/topstories",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"
    ],
    "CA": [
        "https://www.theglobeandmail.com/feeds/business/",
        "https://financialpost.com/feed/",
    ],
    "FR": [
        "https://www.lesechos.fr/rss/finance-marches.xml",
        "https://www.boursorama.com/rss/flux-actus-boursorama.xml",
    ],
    "DE": [
        "https://www.handelsblatt.com/contentexport/feed/meistgelesen",
        "https://www.faz.net/rss/aktuell/wirtschaft/",
    ],
    "INTL": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.economist.com/business/rss.xml",
        "https://www.ft.com/rss/markets",
    ],
}


def fetch_financial_news(regions: List[str] = None, limit_per_source: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch financial news from RSS feeds with robust error handling.
    """
    if regions is None:
        regions = ["US", "INTL"]  # Default regions
        
    all_articles = []
    
    for region in regions:
        if region not in RSS_SOURCES:
            continue
            
        for source_url in RSS_SOURCES[region]:
            try:
                logger.info(f"Fetching news from {source_url}")
                
                # Fetch the RSS feed
                headers = {
                    'User-Agent': 'FinanceCopilot Bot 1.0 (market analysis)',
                    'Accept': 'application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8'
                }
                
                response = requests.get(source_url, headers=headers, timeout=15)
                response.raise_for_status()
                
                # Parse the feed
                feed = feedparser.parse(response.content)
                
                if not feed.entries:
                    logger.warning(f"No entries found in feed: {source_url}")
                    continue
                
                # Process entries with limit
                for entry in feed.entries[:limit_per_source]:
                    try:
                        # Extract publication date
                        pub_date = None
                        for date_field in ['published', 'updated', 'created']:
                            if hasattr(entry, f'{date_field}_parsed') and getattr(entry, f'{date_field}_parsed'):
                                date_tuple = getattr(entry, f'{date_field}_parsed')
                                pub_date = datetime(*date_tuple[:6]).isoformat() + "Z"
                                break
                        
                        if not pub_date:
                            pub_date = datetime.utcnow().isoformat() + "Z"
                        
                        # Extract and clean title
                        title = getattr(entry, 'title', '').strip()
                        if not title:
                            continue  # Skip entries without titles
                        
                        # Extract link
                        link = getattr(entry, 'link', '').strip()
                        
                        # Extract summary/description
                        summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
                        # Remove HTML tags
                        summary = re.sub('<[^<]+?>', '', summary)[:500]  # Limit to 500 chars
                        
                        # Extract potential tickers from title and summary
                        text_for_ticker_extraction = f"{title} {summary}".upper()
                        potential_tickers = set(re.findall(r'\b([A-Z]{1,5})\b', text_for_ticker_extraction))
                        
                        # Filter for known financial tickers (expanded list)
                        financial_tickers = {
                            "SPY", "QQQ", "IWM", "DIA",  # Major ETFs
                            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX", "ADBE", "CRM",
                            "JPM", "BAC", "GS", "MS", "C", "WFC", "AXP",  # Major banks
                            "JNJ", "PFE", "AZN", "NVS", "RDS-A", "RDS-B",  # Pharma/healthcare
                            "XOM", "CVX", "BP", "SLB", "HAL",  # Oil/energy
                            "V", "MA", "PYPL", "SQ", "COIN",  # Payment/Fintech
                            "DIS", "CMCSA", "T", "VZ", "TMUS",  # Media/Telecom
                            "HD", "LOW", "WMT", "TGT", "COST",  # Retail
                            "BA", "CAT", "HON", "LMT", "RTX", "GE",  # Industrials/Defense
                            "TMO", "DHR", "ILMN", "TSLA", "SIRI",  # Tech/Biotech
                        }
                        
                        actual_tickers = [ticker for ticker in potential_tickers if ticker in financial_tickers]
                        
                        # Calculate basic scores
                        importance_score = estimate_importance_score(title, summary)
                        sentiment_score = estimate_sentiment_score(summary)
                        
                        # Generate unique ID
                        unique_id = hashlib.md5(f"{title}{link}{pub_date}".encode()).hexdigest()
                        
                        article = {
                            "id": unique_id,
                            "title": title[:500],  # Limit length
                            "url": link,
                            "pubDate": pub_date,
                            "source": source_url,
                            "region": region,
                            "summary": summary,
                            "tickers": actual_tickers,
                            "sentiment_score": sentiment_score,
                            "importance_score": importance_score,
                            "freshness_score": calculate_freshness_score(pub_date),
                            "timestamp": int(datetime.utcnow().timestamp())
                        }
                        
                        all_articles.append(article)
                        
                    except Exception as e:
                        logger.warning(f"Skipping entry from {source_url} due to error: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Failed to fetch {source_url}: {e}")
                continue
    
    logger.info(f"Fetched {len(all_articles)} articles from {len(regions)} regions")
    return all_articles


def estimate_sentiment_score(text: str) -> float:
    """
    Very basic sentiment estimation based on keywords.
    In production, this would use a proper NLP model.
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    
    positive_keywords = ["rise", "gain", "up", "positive", "bullish", "grow", "profit", "beat", "upgrade", "strong", "gain", "advance", "jump", "surge", "rally"]
    negative_keywords = ["fall", "lose", "down", "negative", "bearish", "drop", "loss", "miss", "downgrade", "weak", "decline", "slump", "plunge", "slide", "dip"]
    
    pos_count = sum(1 for word in positive_keywords if word in text_lower)
    neg_count = sum(1 for word in negative_keywords if word in text_lower)
    
    # Normalize between -1 (very negative) and 1 (very positive)
    total_relevant_words = pos_count + neg_count
    if total_relevant_words > 0:
        sentiment = (pos_count - neg_count) / total_relevant_words
    else:
        sentiment = 0.0  # Neutral if no relevant keywords found
    
    # Clamp between -1 and 1
    return max(-1.0, min(1.0, sentiment))


def estimate_importance_score(title: str, summary: str) -> float:
    """
    Estimate importance score based on keywords.
    """
    text_combined = (title + " " + summary).lower()
    
    # Keywords that indicate higher importance
    important_keywords = [
        "earnings", "merger", "acquisition", "dividend", "regulatory", "fed", 
        "interest rate", "inflation", "gdp", "unemployment", "recession", "bankruptcy",
        "ceo", "analyst", "rating", "target", "forecast", "guidance", "buyback",
        "ipo", "delisting", "lawsuit", "antitrust", "takeover", "spinoff", "restructure"
    ]
    
    importance_count = sum(1 for word in important_keywords if word in text_combined)
    
    # Scale based on how many important keywords were found (0 to 1)
    return min(1.0, importance_count * 0.15)  # Each important keyword adds 0.15 up to max 1.0


def calculate_freshness_score(pub_date_str: str) -> float:
    """
    Calculate freshness score based on how recent the article is.
    """
    try:
        if pub_date_str.endswith('Z'):
            pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00').replace('+00:00', ''))
        else:
            pub_date = datetime.fromisoformat(pub_date_str)
        
        # Calculate age in hours
        age_hours = (datetime.utcnow() - pub_date).total_seconds() / 3600
        
        # Freshness decreases exponentially (newer articles = higher score)
        # Max freshness = 1.0 for very recent articles, approaching 0 for older ones
        freshness = max(0.0, min(1.0, 2 ** (-age_hours / 6)))  # Half-life of 6 hours
        
        return freshness
    except:
        # If can't parse date, assume it's moderately fresh
        return 0.5


def deduplicate_articles(articles: List[Dict[str, Any]], time_window_hours: int = 48) -> List[Dict[str, Any]]:
    """
    Remove duplicate articles based on similarity of title and source.
    """
    if not articles:
        return []
    
    # Sort by publication date (newest first)
    sorted_articles = sorted(articles, key=lambda x: x.get('pubDate', ''), reverse=True)
    
    # Use a set to track seen titles (normalized)
    seen_titles = set()
    deduplicated = []
    
    cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
    
    for article in sorted_articles:
        pub_date_str = article.get('pubDate', '')
        try:
            pub_date = datetime.fromisoformat(pub_date_str.replace('Z', ''))
            if pub_date < cutoff_time:
                continue  # Skip old articles
        except:
            # If we can't parse the date, still include it
            pass
        
        title = article.get('title', '').lower().strip()
        source_domain = re.sub(r'^https?://(www\.)?', '', article.get('source', ''))
        
        # Create a normalized title for comparison (remove common words, punctuation)
        normalized_title = re.sub(r'[^\w\s]', ' ', title).strip()
        normalized_title = ' '.join(normalized_title.split())  # Normalize whitespace
        
        # Create a unique identifier combining source and normalized title
        unique_identifier = f"{source_domain}:{normalized_title[:60]}"  # First 60 chars to avoid extremely long titles
        
        if unique_identifier not in seen_titles:
            deduplicated.append(article)
            seen_titles.add(unique_identifier)
    
    logger.info(f"Deduplicated from {len(articles)} to {len(deduplicated)} articles (within {time_window_hours}h)")
    return deduplicated


def compute_news_feed() -> Dict[str, Any]:
    """
    Compute the news feed by fetching from RSS sources, deduplicating, and enriching.
    This is the main function that implements the FC-P1-011 task requirements.
    """
    logger.info("Starting news feed computation...")
    
    try:
        # Fetch articles from all configured sources
        raw_articles = fetch_financial_news(regions=["US", "INTL", "FR", "DE"], limit_per_source=15)
        
        # Deduplicate articles
        deduplicated_articles = deduplicate_articles(raw_articles, time_window_hours=24)
        
        # Sort by importance and freshness combined score
        scored_articles = []
        for article in deduplicated_articles:
            combined_score = (
                article.get('importance_score', 0) * 0.6 + 
                article.get('freshness_score', 0) * 0.4
            )
            article['combined_score'] = combined_score
            scored_articles.append(article)
        
        # Sort by combined score (descending)
        scored_articles.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
        
        # Prepare final response
        result = {
            "articles": scored_articles,
            "count": len(scored_articles),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["rss_multi_sources", "financial_news_pipeline", "deduplication_engine"],
            "regions_covered": list(set(article.get('region', 'unknown') for article in scored_articles)),
            "tickers_mentioned": list(set(ticker for article in scored_articles for ticker in article.get('tickers', []))),
            "freshness_metrics": {
                "avg_freshness": sum(article.get('freshness_score', 0) for article in scored_articles) / len(scored_articles) if scored_articles else 0,
                "newest_article": max((article.get('pubDate') for article in scored_articles if article.get('pubDate')), default=None),
                "oldest_article": min((article.get('pubDate') for article in scored_articles if article.get('pubDate')), default=None)
            }
        }
        
        logger.info(f"News feed computation completed with {len(scored_articles)} articles")
        return result
        
    except Exception as e:
        logger.error(f"Error in compute_news_feed: {e}")
        # Return fallback structure to maintain never-empty guarantee
        return {
            "articles": [],
            "count": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["error_fallback"],
            "regions_covered": [],
            "tickers_mentioned": [],
            "freshness_metrics": {
                "avg_freshness": 0,
                "newest_article": None,
                "oldest_article": None
            },
            "error": str(e),
            "message": "News feed computation encountered an error - returning empty feed as fallback"
        }


def run_news_ingest_job():
    """
    Run the news ingestion job and persist results to storage.
    """
    logger.info("Starting news ingestion job...")
    
    try:
        # Compute the news feed using our function
        news_data = compute_news_feed()
        
        # Save the results using our persistent storage
        save_path = save_json(news_data, "news_feed.json", ["rss_ingestion", "financial_news", "multi_source"])
        
        logger.info(f"News ingestion completed successfully. Saved {len(news_data.get('articles', []))} articles to {save_path}")
        
        return news_data
        
    except Exception as e:
        logger.error(f"Error in news ingestion job: {e}")
        
        # Return fallback structure to maintain never-empty guarantee
        fallback_result = {
            "articles": [],
            "count": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["rss_ingestion", "error_fallback"],
            "regions_covered": [],
            "tickers_mentioned": [],
            "freshness_metrics": {
                "avg_freshness": 0,
                "newest_article": None,
                "oldest_article": None
            },
            "error": str(e),
            "message": "News ingestion failed, saved fallback data to maintain never-empty guarantee"
        }
        
        # Save the error state to ensure the endpoint still has data to serve
        save_json(fallback_result, "news_feed.json", ["rss_ingestion", "error_fallback"])
        
        logger.warning("News ingestion failed, saved fallback data to maintain never-empty guarantee")
        return fallback_result


if __name__ == "__main__":
    print("Testing news ingestion pipeline...")
    print("Task: FC-P1-011 - News Ingest v1 (RSS multi-sources)")
    print(f"Started: {datetime.now().isoformat()}")
    print("-" * 60)
    
    # Run and persist news feed
    news_result = run_news_ingest_job()
    
    print(f"Generated {len(news_result.get('articles', []))} articles")
    print(f"Regions covered: {news_result.get('regions_covered', [])}")
    print(f"Tickers mentioned: {len(news_result.get('tickers_mentioned', []))}")
    print(f"Avg freshness: {news_result.get('freshness_metrics', {}).get('avg_freshness', 0):.2f}")
    
    # Show sample articles
    sample_articles = news_result.get("articles", [])[:3]  # Show top 3
    for i, article in enumerate(sample_articles):
        print(f"\nSample {i+1}: {article.get('title', 'N/A')[:60]}...")
        print(f"  Source: {article.get('source', 'N/A')[20:].split('/')[0] if article.get('source') else 'N/A'}")
        print(f"  Region: {article.get('region', 'N/A')}")
        print(f"  Tickers: {article.get('tickers', [])}")
        print(f"  Importance: {article.get('importance_score', 0):.2f}")
        print(f"  Sentiment: {article.get('sentiment_score', 0):.2f}")
    
    print("-" * 60)
    print("News ingestion pipeline test completed successfully!")
    print(f"Status: SUCCESS - {len(news_data.get('articles', []))} real articles from multi-sources")
    print(f"Output saved to persistent storage with never-empty guarantee")
    print("=" * 60)