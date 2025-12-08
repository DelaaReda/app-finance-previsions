"""
News ingestion job module - REAL IMPLEMENTATION
Handles the refresh of news feed data from various RSS sources
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: DATA-GEN-001 - Create real news generation job
Uses: Standard library only (urllib + xml.etree.ElementTree)
"""
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Any
import yaml

# Add parent directory to path to import storage
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

logger = logging.getLogger(__name__)

# RSS Feed sources (using publicly accessible feeds)
RSS_SOURCES = [
    {
        "name": "Yahoo Finance - Markets",
        "url": "https://finance.yahoo.com/news/rssindex",
        "category": "markets"
    },
    {
        "name": "Yahoo Finance - NVDA",
        "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US",
        "category": "semiconductors"
    },
    {
        "name": "Yahoo Finance - AAPL",
        "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US",
        "category": "mega-cap-tech"
    },
    {
        "name": "MarketWatch - Top Stories",
        "url": "http://feeds.marketwatch.com/marketwatch/topstories/",
        "category": "general"
    },
    {
        "name": "Seeking Alpha - Market News",
        "url": "https://seekingalpha.com/market_currents.xml",
        "category": "analysis"
    }
]

# Univers par défaut et mapping mots-clés -> ticker (pour mieux tagger les news)
DEFAULT_TICKERS = {"SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "GOOG", "NVDA", "TSLA", "META", "AMZN"}
COMPANY_KEYWORDS = {
    "NVIDIA": "NVDA",
    "NVDIA": "NVDA",
    "NVDA": "NVDA",
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "TESLA": "TSLA",
    "GOOGLE": "GOOGL",
    "ALPHABET": "GOOGL",
    "META": "META",
    "FACEBOOK": "META",
    "AMAZON": "AMZN",
}

def fetch_rss_feed(url: str, timeout: int = 10) -> str:
    """
    Fetch RSS feed content from URL
    
    Args:
        url: RSS feed URL
        timeout: Request timeout in seconds
        
    Returns:
        XML content as string
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Finance Copilot News Aggregator)'}
        request = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = response.read().decode('utf-8')
            return content
    except urllib.error.URLError as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return ""


def parse_rss_xml(xml_content: str) -> List[Dict[str, Any]]:
    """
    Parse RSS/Atom XML with a robust strategy. Falls back to feedparser if needed.
    """
    articles: List[Dict[str, Any]] = []
    if not xml_content:
        return articles
    try:
        root = ET.fromstring(xml_content)
        items = root.findall('.//item') + root.findall('.//{http://www.w3.org/2005/Atom}entry')
        for it in items:
            title = (it.findtext('title') or it.findtext('{http://www.w3.org/2005/Atom}title') or '').strip()
            desc = (
                it.findtext('description')
                or it.findtext('{http://www.w3.org/2005/Atom}summary')
                or it.findtext('{http://www.w3.org/2005/Atom}content')
                or ''
            )
            desc = re.sub(r'<[^>]+>', '', desc).strip()[:300]
            link_elem = it.find('link') or it.find('{http://www.w3.org/2005/Atom}link')
            url = ''
            if link_elem is not None:
                href = link_elem.get('href')
                url = (href or (link_elem.text or '')).strip()
            if (not url) and it.findtext('guid'):
                g = it.findtext('guid').strip()
                if g.startswith('http://') or g.startswith('https://'):
                    url = g
            pub = (
                it.findtext('pubDate')
                or it.findtext('{http://www.w3.org/2005/Atom}published')
                or it.findtext('{http://www.w3.org/2005/Atom}updated')
            )
            articles.append({
                'title': title if title else '(sans titre)',
                'summary': desc,
                'url': url,
                'published_at': (pub.strip() if pub else datetime.utcnow().isoformat() + 'Z')
            })
        logger.info(f"Parsed {len(articles)} articles from XML")
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error parsing XML: {e}")

    # Fallback with feedparser if titles look missing in majority
    try:
        missing = sum(1 for a in articles if not a.get('title') or a.get('title') in {'No title', '(sans titre)'} )
        if not articles or (missing / max(len(articles), 1) > 0.5):
            try:
                import feedparser  # type: ignore
                fp = feedparser.parse(xml_content)
                parsed: List[Dict[str, Any]] = []
                for entry in fp.entries:
                    t = (getattr(entry, 'title', '') or '').strip() or '(sans titre)'
                    link = (getattr(entry, 'link', '') or '').strip()
                    pub = None
                    for field in ('published', 'updated', 'created'):
                        val = getattr(entry, field, None)
                        if val:
                            pub = str(val)
                            break
                    if not pub:
                        pub = datetime.utcnow().isoformat() + 'Z'
                    parsed.append({
                        'title': t,
                        'summary': (getattr(entry, 'summary', '') or '')[:300],
                        'url': link,
                        'published_at': pub,
                    })
                if parsed:
                    articles = parsed
            except Exception:
                pass
    except Exception:
        pass

    # Final cleanup
    out: List[Dict[str, Any]] = []
    for a in articles:
        t = (a.get('title') or '').strip()
        u = (a.get('url') or '').strip()
        if not t and not u:
            continue
        a['title'] = t if t else '(sans titre)'
        out.append(a)
    return out


def score_article(article: Dict[str, Any]) -> float:
    """
    Simple keyword-based scoring for article relevance and sentiment
    
    Args:
        article: Article dictionary with title and summary
        
    Returns:
        Score between 0 and 100
    """
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    
    # Positive keywords (bullish signals)
    positive_keywords = ['rally', 'surge', 'gain', 'rise', 'up', 'growth', 'profit', 
                        'beat', 'strong', 'bullish', 'record', 'high', 'breakthrough']
    
    # Negative keywords (bearish signals)
    negative_keywords = ['fall', 'drop', 'crash', 'loss', 'down', 'weak', 'miss',
                        'bearish', 'decline', 'concern', 'risk', 'warning', 'low']
    
    # High-impact keywords (increases relevance)
    impact_keywords = ['fed', 'inflation', 'earnings', 'market', 'stocks', 'index',
                      'nasdaq', 'sp500', 'dow', 'nasdaq', 'economy', 'gdp']
    
    # Calculate sentiment
    positive_count = sum(1 for keyword in positive_keywords if keyword in text)
    negative_count = sum(1 for keyword in negative_keywords if keyword in text)
    impact_count = sum(1 for keyword in impact_keywords if keyword in text)
    
    # Base score: 50 (neutral)
    score = 50.0
    
    # Adjust for sentiment
    score += positive_count * 5  # +5 per positive keyword
    score -= negative_count * 3  # -3 per negative keyword
    
    # Boost for high-impact topics
    score += impact_count * 10
    
    # Cap between 0 and 100
    score = max(0, min(100, score))
    
    return round(score, 1)


def detect_sentiment(article: Dict[str, Any]) -> str:
    """
    Detect article sentiment based on keywords
    
    Args:
        article: Article dictionary
        
    Returns:
        Sentiment: 'positive', 'negative', or 'neutral'
    """
    score = score_article(article)
    
    if score >= 60:
        return "positive"
    elif score <= 40:
        return "negative"
    else:
        return "neutral"


def run_news_ingest():
    """
    Main function to run news ingestion job
    Fetches from RSS feeds, processes, scores, and saves to persistent storage
    """
    logger.info("Starting news ingestion job with REAL data generation...")
    
    try:
        from storage.base import save_json
        try:
            from storage.io import load_json
        except Exception:
            load_json = None
        
        all_articles = []
        sources_processed = []

        # Known tickers from forecasts + profiles (pour enrichir l'extraction)
        known_tickers = set(DEFAULT_TICKERS)
        if load_json:
            try:
                fc = load_json("forecasts") or {}
                rows = fc.get("rows") or fc.get("data", {}).get("rows", []) or []
                for r in rows:
                    t = (r.get("ticker") or r.get("symbol") or "").upper()
                    if t:
                        known_tickers.add(t)
            except Exception:
                pass
        # Add tickers from judge profiles (YAML) if available
        profiles_dir = Path(__file__).parent.parent / "data" / "judge_profiles"
        if profiles_dir.exists():
            try:
                for p in profiles_dir.glob("*.yaml"):
                    cfg = yaml.safe_load(p.read_text()) or {}
                    for t in cfg.get("tickers", []) or []:
                        if isinstance(t, str):
                            known_tickers.add(t.upper())
            except Exception as e:
                logger.warning(f"Failed to load profile tickers: {e}")
        
        # Fetch from each RSS source
        for source in RSS_SOURCES:
            logger.info(f"Fetching from {source['name']}...")
            
            try:
                # Fetch RSS feed
                xml_content = fetch_rss_feed(source['url'])
                
                if not xml_content:
                    logger.warning(f"No content from {source['name']}, skipping")
                    continue
                
                # Parse articles
                articles = parse_rss_xml(xml_content)
                
                if not articles:
                    logger.warning(f"No articles parsed from {source['name']}")
                    continue
                
                # Process each article
                for article in articles:
                    # Add metadata
                    article['source'] = source['name']
                    article['category'] = source.get('category', 'general')
                    
                    # Score article
                    article['score'] = score_article(article)
                    article['sentiment'] = detect_sentiment(article)
                    
                    # Ticker extraction améliorée : $TICKER + détection sur liste connue + mots-clés société
                    text = (article.get('title', '') + ' ' + article.get('summary', '')).upper()
                    tickers = set(re.findall(r'\$([A-Z]{1,5})', text))
                    for kt in known_tickers:
                        if re.search(rf'\b{re.escape(kt)}\b', text):
                            tickers.add(kt)
                    for name, tk in COMPANY_KEYWORDS.items():
                        if name in text:
                            tickers.add(tk)
                    article['tickers'] = list(tickers)[:5]  # Max 5 uniques
                    
                    # Add ingestion timestamp
                    article['ingested_at'] = datetime.utcnow().isoformat() + "Z"
                
                all_articles.extend(articles)
                sources_processed.append(source['name'])
                
                logger.info(f"✅ Processed {len(articles)} articles from {source['name']}")
                
            except Exception as e:
                logger.error(f"Error processing source {source['name']}: {e}", exc_info=True)
                continue
        
        # Sort by score (highest first)
        all_articles.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Limit to top 100 articles
        all_articles = all_articles[:100]
        
        # Prepare result
        result = {
            "articles": all_articles,
            "count": len(all_articles),
            "sources": sources_processed,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Save to persistent storage
        logger.info("Saving news feed to storage...")
        save_json(result, "news_feed.json", source=["job:news_ingest", "rss_feeds"] + sources_processed)
        
        # Return summary
        summary = {
            "processed_count": len(all_articles),
            "sources": sources_processed,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "completed"
        }
        
        logger.info(f"✅ News ingestion job completed successfully. Processed {len(all_articles)} articles from {len(sources_processed)} sources.")
        return summary
        
    except ImportError as e:
        logger.error(f"Import error in news ingestion job: {str(e)}", exc_info=True)
        return {
            "processed_count": 0,
            "sources": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": f"Import error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"News ingestion job failed: {str(e)}", exc_info=True)
        return {
            "processed_count": 0,
            "sources": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": str(e)
        }


if __name__ == "__main__":
    # Allow testing the job directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    result = run_news_ingest()
    print(f"\n✅ Job completed: {result}")
