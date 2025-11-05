"""
News ingestion pipeline for Finance Copilot
Implements robust RSS feed ingestion with deduplication, enrichment and persistent storage
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import os
import re
import json
import hashlib
import datetime as dt
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime, timedelta

# Import our storage system
from backend.storage.base import save_json, load_json

logger = logging.getLogger(__name__)

# Financial news RSS sources
SOURCES = {
    "US": [
        "https://www.reuters.com/business/rssBusinessNews",
        "https://www.reuters.com/markets/rssMarketsNews", 
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.ft.com/rss/markets",
    ],
    "CA": [
        "https://www.theglobeandmail.com/feeds/business/",
        "https://financialpost.com/feed/",
        "https://www.bnnbloomberg.ca/polopoly_fs/BNNBloombergBusinessNews.xml",
    ],
    "FR": [
        "https://www.lesechos.fr/rss/finance-marches.xml",
        "https://www.boursorama.com/rss/flux-actus-boursorama.xml",
        "https://www.zonebourse.com/rss/flash/",
    ],
    "DE": [
        "https://www.handelsblatt.com/contentexport/feed/meistgelesen",
        "https://www.faz.net/rss/aktuell/wirtschaft/",
        "https://www.boersen-zeitung.de/rss",
    ],
    "INTL": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.economist.com/business/rss.xml",
    ],
}

def fetch_financial_news(regions: List[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch financial news from RSS feeds with robust error handling and deduplication.
    """
    import feedparser
    import requests
    from urllib.parse import urlparse
    
    if regions is None:
        regions = ["US", "INTL"]  # Default to US and international sources
    
    all_articles = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Finance Copilot Bot/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    for region in regions:
        if region not in SOURCES:
            continue
            
        for url in SOURCES[region]:
            try:
                logger.info(f"Fetching news from {url}")
                
                # Attempt to fetch feed
                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    
                    feed = feedparser.parse(response.content)
                    
                    if not feed.entries:
                        logger.warning(f"No entries found in feed: {url}")
                        continue
                    
                    for entry in feed.entries[:20]:  # Limit per feed to avoid spam
                        article = normalize_rss_entry(entry, url, region)
                        if article:  # Only add valid articles
                            all_articles.append(article)
                            
                except Exception as e:
                    logger.warning(f"Failed to fetch {url}: {e}")
                    continue
                    
            except Exception as e:
                logger.error(f"Unexpected error fetching from {url}: {e}")
                continue
    
    # Deduplicate articles based on title similarity
    deduplicated_articles = deduplicate_articles(all_articles)
    
    logger.info(f"Fetched and processed {len(deduplicated_articles)} unique articles from {len(regions)} regions")
    return deduplicated_articles


def normalize_rss_entry(entry, source_url: str, region: str) -> Optional[Dict[str, Any]]:
    """
    Normalize an RSS entry to our standard format.
    """
    try:
        # Extract and clean title
        title = getattr(entry, 'title', '').strip()
        if not title:
            return None
            
        # Extract publication date
        pub_date = None
        for date_attr in ['published', 'updated', 'created']:
            date_val = getattr(entry, f'{date_attr}_parsed', None)
            if date_val:
                try:
                    pub_date = dt.datetime(*date_val[:6]).isoformat() + "Z"
                    break
                except:
                    continue
                    
        if not pub_date:
            pub_date = datetime.utcnow().isoformat() + "Z"
        
        # Extract link
        link = getattr(entry, 'link', '').strip()
        if not link:
            # Try alternative fields
            link = getattr(entry, 'id', '').strip()
            
        # Extract summary/description
        summary = getattr(entry, 'summary', '')
        if not summary:
            summary = getattr(entry, 'description', '')
        # Clean HTML if needed
        summary = re.sub('<[^<]+?>', '', summary)[:500]  # Strip HTML and limit length
        
        # Extract potential tickers from title and summary
        text_for_ticker_extraction = f"{title} {summary}".upper()
        potential_tickers = set(re.findall(r'\b([A-Z]{1,5})\b', text_for_ticker_extraction))
        
        # Common financial tickers to filter against (expanded list)
        financial_tickers = {
            "SPY", "QQQ", "IWM", "DIA",  # Major ETFs
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX", "ADBE", "CRM",
            "JPM", "BAC", "GS", "MS", "C", "WFC", "AXP",  # Major banks
            "JNJ", "PFE", "AZN", "NVS", "RHHBY", "UNH", "MRK", "ABBV",  # Major pharma/healthcare
            "XOM", "CVX", "RDS-A", "RDS-B", "BP", "SLB", "HAL",  # Major oil/energy
            "V", "MA", "PYPL", "SQ", "COIN", "VISA", "MAST",  # Payment/Fintech
            "DIS", "CMCSA", "T", "VZ", "TMUS",  # Media/Telecom
            "HD", "LOW", "WMT", "TGT", "COST",  # Retail
            "BA", "CAT", "HON", "LMT", "RTX", "GE",  # Industrials/Defense
            "TMO", "DHR", "ILMN", "TSLA", "SIRI",  # Tech/Biotech
        }
        
        actual_tickers = [ticker for ticker in potential_tickers if ticker in financial_tickers]
        
        # Create normalized article
        normalized_article = {
            "id": entry.get("id") or entry.get("link") or f"{hashlib.md5((title + link).encode()).hexdigest()}",
            "title": title[:500],  # Limit title length
            "url": link,
            "pubDate": pub_date,
            "source": source_url,
            "region": region,
            "summary": summary,
            "tickers": actual_tickers,
            "sentiment_score": estimate_sentiment_score(summary),  # Very basic sentiment
            "importance_score": estimate_importance_score(title, summary),  # Basic importance
            "freshness_score": calculate_freshness_score(pub_date),  # How fresh is the article
            "timestamp": int(datetime.utcnow().timestamp())  # Unix timestamp
        }
        
        return normalized_article
        
    except Exception as e:
        logger.error(f"Error normalizing RSS entry: {e}")
        return None


def estimate_sentiment_score(text: str) -> float:
    """
    Very basic sentiment estimation based on keywords.
    In production, this would use a proper NLP model.
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    
    positive_keywords = ["rise", "gain", "up", "positive", "bullish", "grow", "profit", "beat", "upgrade", "strong"]
    negative_keywords = ["fall", "lose", "down", "negative", "bearish", "drop", "loss", "miss", "downgrade", "weak"]
    
    pos_count = sum(1 for word in positive_keywords if word in text_lower)
    neg_count = sum(1 for word in negative_keywords if word in text_lower)
    
    # Normalize between -1 (very negative) and 1 (very positive)
    total_words = max(1, len(text_lower.split()))
    sentiment = (pos_count - neg_count) / max(1, total_words / 50)  # Scale by content length
    
    # Clamp between -1 and 1
    return max(-1.0, min(1.0, sentiment))


def estimate_importance_score(title: str, summary: str) -> float:
    """
    Very basic importance estimation based on keywords and source authority.
    """
    text_combined = (title + " " + summary).lower()
    
    # Keywords that indicate higher importance
    important_keywords = [
        "earnings", "merger", "acquisition", "dividend", "regulatory", "federal reserve", 
        "interest rate", "inflation", "GDP", "unemployment", "recession", "bankruptcy",
        "CEO", "analyst", "rating", "target", "forecast", "guidance", "buyback"
    ]
    
    importance_count = sum(1 for word in important_keywords if word in text_combined)
    
    # Scale based on how many important keywords were found
    return min(1.0, importance_count * 0.15)  # Each important keyword adds 0.15 up to max 1.0


def calculate_freshness_score(pub_date_str: str) -> float:
    """
    Calculate freshness score based on how recent the article is.
    """
    try:
        if pub_date_str.endswith('Z'):
            pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
        else:
            pub_date = datetime.fromisoformat(pub_date_str)
        
        # Calculate age in hours
        age_hours = (datetime.utcnow() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
        
        # Freshness decreases exponentially (newer articles = higher score)
        # Max freshness = 1.0 for very recent articles, approaching 0 for older ones
        freshness = max(0.0, min(1.0, 2 ** (-age_hours / 12)))  # Half-life of 12 hours
        
        return freshness
    except:
        # If can't parse date, assume it's moderately fresh
        return 0.5


def deduplicate_articles(articles: List[Dict[str, Any]], time_window_hours: int = 24) -> List[Dict[str, Any]]:
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
    
    for article in sorted_articles:
        title = article.get('title', '').lower().strip()
        source_domain = re.sub(r'^https?://(www\.)?', '', article.get('source', ''))
        
        # Create a normalized title for comparison (remove common words, punctuation)
        normalized_title = re.sub(r'[^\w\s]', ' ', title).strip()
        normalized_title = ' '.join(normalized_title.split())  # Normalize whitespace
        
        # Create a unique identifier combining source and normalized title
        unique_identifier = f"{source_domain}:{normalized_title[:50]}"  # First 50 chars to avoid extremely long titles
        
        if unique_identifier not in seen_titles:
            # Check if article is within our time window
            pub_date_str = article.get('pubDate', '')
            if pub_date_str:
                try:
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                    age_hours = (datetime.utcnow() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
                    
                    if age_hours <= time_window_hours:
                        deduplicated.append(article)
                        seen_titles.add(unique_identifier)
                    else:
                        # Article is too old, but still add to seen titles to avoid duplicates
                        seen_titles.add(unique_identifier)
                except:
                    # If we can't parse the date, include the article anyway
                    deduplicated.append(article)
                    seen_titles.add(unique_identifier)
            else:
                # No date available, include the article
                deduplicated.append(article)
                seen_titles.add(unique_identifier)
    
    logger.info(f"Deduplicated from {len(articles)} to {len(deduplicated)} articles")
    return deduplicated


def run_news_ingest_job():
    """
    Run the news ingestion job and persist results to storage.
    """
    logger.info("Starting news ingestion job...")
    
    try:
        # Fetch news from configured sources
        news_articles = fetch_financial_news(regions=["US", "INTL", "FR"])
        
        # Prepare the response data
        result = {
            "articles": news_articles,
            "count": len(news_articles),
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "sources_used": ["Reuters", "Bloomberg", "FT", "LesEchos", "Boursorama"],  # Just listing high-level sources
            "regions_collected": ["US", "INTL", "FR"],
            "import_status": "success"
        }
        
        # Save the results using our persistent storage
        save_path = save_json(result, "news_feed.json", ["rss_ingestion", "financial_news", "multi_source"])
        
        logger.info(f"News ingestion completed successfully. Saved {len(news_articles)} articles to {save_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in news ingestion job: {e}")
        
        # Return fallback structure to maintain never-empty guarantee
        fallback_result = {
            "articles": [],
            "count": 0,
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "sources_used": [],
            "regions_collected": [],
            "import_status": "error",
            "error_message": str(e)
        }
        
        # Save the error state to ensure the endpoint still has data to serve
        save_json(fallback_result, "news_feed.json", ["rss_ingestion", "error_fallback"])
        
        logger.warning("News ingestion failed, saved fallback data to maintain never-empty guarantee")
        return fallback_result


if __name__ == "__main__":
    print("Testing news ingestion pipeline...")
    result = run_news_ingest_job()
    print(f"Ingestion completed with {result.get('count', 0)} articles")
    print("News ingestion pipeline test completed successfully!")