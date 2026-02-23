"""
News ingestion job module - REAL IMPLEMENTATION
Handles the refresh of news feed data from various RSS sources
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: DATA-GEN-001 - Create real news generation job
Uses: Standard library only (urllib + xml.etree.ElementTree)
"""
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import sys
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Any
from email.utils import parsedate_to_datetime
import yaml

# Add parent directory to path to import storage
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

logger = logging.getLogger(__name__)

try:
    from core.sentry_runtime import install_global_excepthook, init_sentry, set_job_context, capture_exception
except Exception:  # pragma: no cover
    def install_global_excepthook(job_name: str) -> bool:
        return False

    def init_sentry(component: str) -> bool:
        return False

    def set_job_context(job_name: str, **context: Any) -> None:
        return None

    def capture_exception(exc: BaseException, *, job_name: str | None = None, context: Dict[str, Any] | None = None) -> None:
        return None

# RSS feed sources (base market streams + dynamic ticker feeds)
BASE_RSS_SOURCES = [
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

# Concept patterns to improve ETF/index/company tagging for generic market headlines.
TICKER_CONTEXT_PATTERNS = {
    "SPY": [
        r"\bS&P\s*500\b",
        r"\bSP500\b",
        r"\bSPX\b",
        r"\bS AND P 500\b",
    ],
    "QQQ": [
        r"\bNASDAQ[-\s]?100\b",
        r"\bNDX\b",
    ],
    "TSLA": [
        r"\bTESLA\b",
        r"\bELON MUSK\b",
        r"\bMUSK\b",
    ],
    "AAPL": [
        r"\bAPPLE\b",
        r"\bIPHONE\b",
    ],
    "GOOGL": [
        r"\bALPHABET\b",
        r"\bGOOGLE\b",
    ],
    "MSFT": [
        r"\bMICROSOFT\b",
    ],
    "AMZN": [
        r"\bAMAZON\b",
    ],
    "META": [
        r"\bMETA\b",
        r"\bFACEBOOK\b",
    ],
    "NVDA": [
        r"\bNVIDIA\b",
        r"\bNVDA\b",
    ],
}

LOOKBACK_DAYS = max(30, int(os.getenv("NEWS_LOOKBACK_DAYS", "90") or "90"))
MIN_ARTICLES_PER_TICKER = max(5, int(os.getenv("NEWS_MIN_ARTICLES_PER_TICKER", "20") or "20"))
MAX_ARTICLES_PER_TICKER = max(
    MIN_ARTICLES_PER_TICKER, int(os.getenv("NEWS_MAX_ARTICLES_PER_TICKER", "60") or "60")
)
MAX_TOTAL_ARTICLES = max(100, int(os.getenv("NEWS_MAX_TOTAL_ARTICLES", "600") or "600"))


def _to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_published_datetime(value: Any) -> datetime | None:
    """Parse RSS/Atom date values into timezone-aware UTC datetimes."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    # ISO first
    try:
        iso_val = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # RFC822 / news-style timestamps
    try:
        dt = parsedate_to_datetime(s)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def build_dynamic_sources(tickers: List[str]) -> List[Dict[str, Any]]:
    """Build ticker-specific sources to increase per-ticker coverage over ~3 months."""
    sources: List[Dict[str, Any]] = []
    for ticker in tickers:
        t = ticker.upper().strip()
        if not t:
            continue
        sources.append(
            {
                "name": f"Yahoo Finance - {t}",
                "url": f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={urllib.parse.quote_plus(t)}&region=US&lang=en-US",
                "category": "ticker",
                "source_ticker": t,
            }
        )
        # Google News RSS offers wider ticker-specific coverage and typically longer lookback.
        query = urllib.parse.quote_plus(f"{t} stock when:{LOOKBACK_DAYS}d")
        sources.append(
            {
                "name": f"Google News - {t}",
                "url": f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
                "category": "ticker",
                "source_ticker": t,
            }
        )
    return sources


def extract_tickers(
    article: Dict[str, Any],
    known_tickers: set[str],
    source_name: str = "",
    source_ticker: str | None = None,
) -> List[str]:
    """
    Extract and rank likely tickers from article text.

    Ranking weights:
      - cashtags ($AAPL): strong
      - explicit ticker symbol in text: strong
      - company keyword aliases: medium
      - context patterns (S&P 500 -> SPY, Nasdaq-100 -> QQQ): medium
      - source hint (feed named "... - AAPL"): weak
    """
    text = f"{article.get('title', '')} {article.get('summary', '')}".upper()
    scores: Dict[str, int] = {}

    def bump(ticker: str, weight: int) -> None:
        if not ticker:
            return
        t = ticker.upper()
        scores[t] = scores.get(t, 0) + weight

    # Cashtags ($AAPL, $TSLA, ...)
    for tagged in re.findall(r"\$([A-Z]{1,5})", text):
        bump(tagged, 8)

    # Direct symbol detection (bounded)
    for kt in known_tickers:
        if re.search(rf"\b{re.escape(kt)}\b", text):
            bump(kt, 6)

    # Company aliases
    for name, tk in COMPANY_KEYWORDS.items():
        if name in text:
            bump(tk, 4)

    # Market context aliases (index names -> ETFs, etc.)
    for tk, patterns in TICKER_CONTEXT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text):
                bump(tk, 3)
                break

    # Feed source hint
    source_upper = (source_name or "").upper()
    for kt in known_tickers:
        if kt and kt in source_upper:
            bump(kt, 2)
    if source_ticker:
        bump(source_ticker.upper(), 2)

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    return [ticker for ticker, _ in ranked[:5]]

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
    init_sentry("news_ingest")
    
    try:
        from storage.base import save_json
        try:
            from storage.io import load_json
        except Exception:
            load_json = None
        
        all_articles: List[Dict[str, Any]] = []
        sources_processed: List[str] = []
        seen_uids: set[str] = set()

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

        target_tickers = sorted(
            {
                t
                for t in known_tickers
                if isinstance(t, str) and t and re.fullmatch(r"[A-Z]{1,6}", t)
            }
        )
        dynamic_sources = build_dynamic_sources(target_tickers)
        rss_sources = BASE_RSS_SOURCES + dynamic_sources
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

        logger.info(
            "News ingest config: sources=%d target_tickers=%d lookback_days=%d min_per_ticker=%d",
            len(rss_sources),
            len(target_tickers),
            LOOKBACK_DAYS,
            MIN_ARTICLES_PER_TICKER,
        )
        set_job_context(
            "news_ingest",
            source_count=len(rss_sources),
            target_ticker_count=len(target_tickers),
            lookback_days=LOOKBACK_DAYS,
        )

        # Fetch from each RSS source
        for source in rss_sources:
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
                    # Normalize publication date and enforce 3-month lookback window
                    pub_dt = parse_published_datetime(article.get("published_at"))
                    if pub_dt is None:
                        pub_dt = datetime.now(timezone.utc)
                    if pub_dt < cutoff_dt:
                        continue

                    # Add metadata
                    article['source'] = source['name']
                    article['category'] = source.get('category', 'general')
                    article['published_at'] = _to_utc_iso(pub_dt)
                    article['_published_ts'] = pub_dt.timestamp()
                    
                    # Score article
                    article['score'] = score_article(article)
                    article['sentiment'] = detect_sentiment(article)
                    
                    article['tickers'] = extract_tickers(
                        article,
                        known_tickers=known_tickers,
                        source_name=source.get("name", ""),
                        source_ticker=source.get("source_ticker"),
                    )
                    if not article['tickers'] and source.get("source_ticker"):
                        article['tickers'] = [str(source["source_ticker"]).upper()]
                    
                    # Add ingestion timestamp
                    article['ingested_at'] = datetime.utcnow().isoformat() + "Z"

                    uid = (
                        article.get("url")
                        or f"{article.get('title','')}|{article.get('published_at','')}|{article.get('source','')}"
                    ).strip()
                    if not uid:
                        continue
                    if uid in seen_uids:
                        continue
                    seen_uids.add(uid)
                    article["_uid"] = uid
                    all_articles.append(article)

                sources_processed.append(source['name'])
                logger.info(f"✅ Processed {len(articles)} raw articles from {source['name']}")
                
            except Exception as e:
                logger.error(f"Error processing source {source['name']}: {e}", exc_info=True)
                continue

        # Sort globally: recency first, then relevance.
        all_articles.sort(
            key=lambda a: (a.get("_published_ts", 0), a.get("score", 0)),
            reverse=True,
        )

        # Coverage-aware selection to provide enough ticker context for judge.
        articles_by_ticker: Dict[str, List[Dict[str, Any]]] = {t: [] for t in target_tickers}
        for article in all_articles:
            for t in article.get("tickers") or []:
                if t in articles_by_ticker:
                    articles_by_ticker[t].append(article)

        selected: List[Dict[str, Any]] = []
        selected_uids: set[str] = set()

        for ticker in target_tickers:
            taken = 0
            for article in articles_by_ticker.get(ticker, []):
                uid = article.get("_uid")
                if not uid or uid in selected_uids:
                    continue
                selected.append(article)
                selected_uids.add(uid)
                taken += 1
                if taken >= MIN_ARTICLES_PER_TICKER:
                    break

        for article in all_articles:
            if len(selected) >= MAX_TOTAL_ARTICLES:
                break
            uid = article.get("_uid")
            if not uid or uid in selected_uids:
                continue
            selected.append(article)
            selected_uids.add(uid)

        # Final cap per ticker to avoid one name monopolizing the feed.
        per_ticker_counts: Dict[str, int] = {t: 0 for t in target_tickers}
        balanced_selected: List[Dict[str, Any]] = []
        for article in selected:
            article_tickers = [t for t in (article.get("tickers") or []) if t in per_ticker_counts]
            if article_tickers and all(per_ticker_counts[t] >= MAX_ARTICLES_PER_TICKER for t in article_tickers):
                continue
            balanced_selected.append(article)
            for t in article_tickers:
                per_ticker_counts[t] += 1
            if len(balanced_selected) >= MAX_TOTAL_ARTICLES:
                break

        all_articles = balanced_selected

        # Prepare result
        ticker_coverage: Dict[str, int] = {t: 0 for t in target_tickers}
        for article in all_articles:
            for t in article.get("tickers") or []:
                if t in ticker_coverage:
                    ticker_coverage[t] += 1

        for article in all_articles:
            article.pop("_uid", None)
            article.pop("_published_ts", None)

        result = {
            "articles": all_articles,
            "count": len(all_articles),
            "sources": sources_processed,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "lookback_days": LOOKBACK_DAYS,
            "min_articles_per_ticker_target": MIN_ARTICLES_PER_TICKER,
            "ticker_coverage": ticker_coverage,
            "ticker_target_met": {
                t: (ticker_coverage.get(t, 0) >= MIN_ARTICLES_PER_TICKER)
                for t in target_tickers
            },
        }
        
        # Save to persistent storage
        logger.info("Saving news feed to storage...")
        save_json(result, "news_feed.json", source=["job:news_ingest", "rss_feeds"] + sources_processed)
        
        # Return summary
        summary = {
            "processed_count": len(all_articles),
            "sources": sources_processed,
            "ticker_coverage": ticker_coverage,
            "target_tickers": target_tickers,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "completed"
        }
        
        logger.info(f"✅ News ingestion job completed successfully. Processed {len(all_articles)} articles from {len(sources_processed)} sources.")
        return summary
        
    except ImportError as e:
        logger.error(f"Import error in news ingestion job: {str(e)}", exc_info=True)
        capture_exception(e, job_name="news_ingest", context={"stage": "import"})
        return {
            "processed_count": 0,
            "sources": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": f"Import error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"News ingestion job failed: {str(e)}", exc_info=True)
        capture_exception(e, job_name="news_ingest", context={"stage": "run"})
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
    install_global_excepthook("news_ingest")
    result = run_news_ingest()
    print(f"\n✅ Job completed: {result}")
