"""
News Ingestion Job - FC-P1-011
Fetches RSS feeds from multiple financial sources, deduplicates, enriches with ticker mapping
"""
import feedparser
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import List, Dict, Any

# Import our existing storage functions
from storage.io import save_json


# Financial news RSS sources - Using working URLs only
SOURCES = [
    {"name": "bloomberg", "url": "https://feeds.bloomberg.com/markets/news.rss"},
    {"name": "market_watch", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"name": "cnbc_markets", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html"},
    {"name": "marketwatch_top", "url": "https://www.marketwatch.com/rss/topstories"},
    {"name": "dj_markets", "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"},
    {"name": "ft_markets", "url": "https://www.ft.com/rss/markets"},
]

# Simple ticker mapping dictionary (S&P 500 and major indices)
TICKER_PATTERN = re.compile(r'\b([A-Z]{1,5})\b')
# Expanded ticker mapping for common stocks
TICKER_MAPPING = {
    "SPY", "QQQ", "IWM", "DIA",  # Major ETFs
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX", "META", "AMZN", "TGT", "WMT",
    "JPM", "BAC", "GS", "MS", "C",  # Major banks
    "JNJ", "PFE", "AZN", "NVS", "RHHBY",  # Major pharma
    "XOM", "CVX", "RDS-A", "RDS-B",  # Major oil
    "V", "MA", "PYPL", "SQ", "COIN",  # Fintech/payment
    "ADBE", "CRM", "INTU", "ORCL",  # Software
    # Add more as needed
}

def fetch_feed(url: str) -> List[Dict[str, Any]]:
    """Fetch and parse a single RSS feed"""
    try:
        feed = feedparser.parse(url)
        return feed.entries
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []


def normalize_article(entry: Dict[str, Any], source: Dict[str, str]) -> Dict[str, Any]:
    """Normalize an RSS entry to our standard format"""
    # Parse publication date
    pub_date = None
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        pub_date = datetime(*entry.published_parsed[:6]).isoformat() + "Z"
    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        pub_date = datetime(*entry.updated_parsed[:6]).isoformat() + "Z"
    
    # Extract potential tickers from title
    title = getattr(entry, 'title', '')
    description = getattr(entry, 'summary', '')
    content = getattr(entry, 'content', '')
    
    # Combine title and description for ticker extraction
    text_for_ticker_extraction = f"{title} {description}".upper()
    
    # Find tickers using regex
    potential_tickers = set(TICKER_PATTERN.findall(text_for_ticker_extraction))
    # Filter to known tickers
    actual_tickers = [tick for tick in potential_tickers if tick in TICKER_MAPPING]
    
    return {
        "id": entry.get("id") or entry.get("link") or f"{source['name']}_{hash(title)}",
        "title": title,
        "link": entry.get("link", ""),
        "pubDate": pub_date,
        "source": source["name"],
        "description": description,
        "tickers": actual_tickers,
        "timestamp": int(time.time())  # Unix timestamp for freshness
    }


def deduplicate_articles(articles: List[Dict[str, Any]], time_window_hours: int = 24) -> List[Dict[str, Any]]:
    """Remove duplicate articles based on title similarity and time window"""
    if not articles:
        return []
    
    # Sort by publication date (newest first)
    sorted_articles = sorted(articles, key=lambda x: x.get('pubDate', ''), reverse=True)
    
    # Deduplication based on title and source
    seen_titles = set()
    deduplicated = []
    
    for article in sorted_articles:
        title = article.get('title', '').lower().strip()
        # Normalize title for comparison (remove common words, punctuation)
        normalized_title = re.sub(r'[^\w\s]', '', title).strip()
        
        # Check if we've seen this title before, and if it's recent enough
        if normalized_title not in seen_titles:
            # Check if the article is within our time window (optional)
            pub_date_str = article.get('pubDate')
            if pub_date_str:
                try:
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                    if datetime.now(pub_date.tzinfo) - pub_date <= timedelta(hours=time_window_hours):
                        deduplicated.append(article)
                        seen_titles.add(normalized_title)
                except:
                    # If we can't parse the date, include it anyway
                    deduplicated.append(article)
                    seen_titles.add(normalized_title)
            else:
                deduplicated.append(article)
                seen_titles.add(normalized_title)
    
    return deduplicated


def compute_news_feed() -> Dict[str, Any]:
    """Main function to compute news feed from all sources"""
    print("Starting news ingestion from RSS feeds...")
    
    all_articles = []
    
    for source in SOURCES:
        print(f"Fetching from {source['name']}...")
        entries = fetch_feed(source['url'])
        
        for entry in entries:
            normalized = normalize_article(entry, source)
            all_articles.append(normalized)
        
        # Be respectful to RSS servers
        time.sleep(1)
    
    print(f"Collected {len(all_articles)} articles before deduplication")
    
    # Deduplicate articles
    deduplicated_articles = deduplicate_articles(all_articles)
    print(f"Filtered to {len(deduplicated_articles)} unique articles after deduplication")
    
    # Sort by publication date (newest first)
    sorted_articles = sorted(deduplicated_articles, 
                            key=lambda x: x.get('pubDate', ''), 
                            reverse=True)
    
    # Limit to 50 most recent articles to keep response size manageable
    final_articles = sorted_articles[:50]
    
    # Prepare the response
    result = {
        "articles": final_articles,
        "total_collected": len(all_articles),
        "total_after_dedup": len(deduplicated_articles),
        "sources_used": [s["name"] for s in SOURCES],
        "collected_at": datetime.now().isoformat() + "Z",
        "next_refresh_estimate": (datetime.now() + timedelta(minutes=15)).isoformat() + "Z"
    }
    
    return result


def run_news_ingest():
    """Run the news ingestion job and save results"""
    try:
        news_data = compute_news_feed()
        
        # Save to file using our storage system
        save_json("news_feed", news_data, source=["rss_ingest", "bloomberg", "market_watch", "cnbc", "ft", "dj_markets"])
        
        print(f"News ingestion completed successfully. Saved {len(news_data['articles'])} articles from {len(news_data['sources_used'])} sources.")
        
        return news_data
    except Exception as e:
        print(f"Error during news ingestion: {e}")
        # Return a minimal response even if there's an error
        error_response = {
            "articles": [],
            "error": str(e),
            "collected_at": datetime.now().isoformat() + "Z",
            "sources_used": []
        }
        
        # Still save the error state so the API doesn't return empty
        save_json("news_feed", error_response, source=["rss_ingest", "error"])
        return error_response


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run news ingestion job')
    parser.add_argument('--cron', action='store_true', help='Run in cron mode (no interactive output)')
    args = parser.parse_args()
    
    if args.cron:
        # Silent mode for cron jobs
        run_news_ingest()
    else:
        # Verbose mode
        run_news_ingest()


if __name__ == "__main__":
    run_news_ingest()
