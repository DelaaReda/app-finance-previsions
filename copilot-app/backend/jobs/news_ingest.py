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
    Parse RSS XML content and extract articles
    
    Args:
        xml_content: RSS XML as string
        
    Returns:
        List of article dictionaries
    """
    articles = []
    
    if not xml_content:
        return articles
    
    try:
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Find all items (articles)
        # Support both RSS 2.0 (<item>) and Atom (<entry>)
        items = root.findall('.//item') + root.findall('.//{http://www.w3.org/2005/Atom}entry')
        
        for item in items:
            article = {}
            
            # Extract title
            title_elem = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
            article['title'] = title_elem.text.strip() if title_elem is not None and title_elem.text else "No title"
            
            # Extract description/summary
            desc_elem = (item.find('description') or 
                        item.find('{http://www.w3.org/2005/Atom}summary') or
                        item.find('{http://www.w3.org/2005/Atom}content'))
            if desc_elem is not None and desc_elem.text:
                # Clean HTML tags from description
                article['summary'] = re.sub(r'<[^>]+>', '', desc_elem.text).strip()[:300]
            else:
                article['summary'] = ""
            
            # Extract link
            link_elem = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
            if link_elem is not None:
                # Atom link is an attribute
                article['url'] = link_elem.get('href', link_elem.text or "")
            else:
                article['url'] = ""
            
            # Extract publication date
            pubdate_elem = (item.find('pubDate') or 
                           item.find('{http://www.w3.org/2005/Atom}published') or
                           item.find('{http://www.w3.org/2005/Atom}updated'))
            if pubdate_elem is not None and pubdate_elem.text:
                article['published_at'] = pubdate_elem.text.strip()
            else:
                article['published_at'] = datetime.utcnow().isoformat() + "Z"
            
            articles.append(article)
        
        logger.info(f"Parsed {len(articles)} articles from XML")
        
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error parsing XML: {e}")
    
    return articles


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
        
        all_articles = []
        sources_processed = []
        
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
                    
                    # Add ticker extraction (simple version - look for $TICKER pattern)
                    tickers = re.findall(r'\$([A-Z]{1,5})', article.get('title', '') + ' ' + article.get('summary', ''))
                    article['tickers'] = list(set(tickers))[:5]  # Max 5 unique tickers
                    
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
