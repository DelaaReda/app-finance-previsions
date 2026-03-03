import time
from datetime import datetime, timedelta
import re
from typing import Any, Dict, List, Optional
from pathlib import Path
import json

from domains.market_data.application.cache_layer import load_or_compute

try:
    import requests
except Exception:
    requests = None

try:
    import feedparser
except Exception:
    feedparser = None

def fetch_rss_feed(url: str) -> List[Dict]:
    """
    Fetch and parse an RSS feed
    """
    try:
        if feedparser is None or requests is None:
            return []
        headers = {
            'User-Agent': 'Finance-Copilot/1.0 (for educational/research purposes)'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        articles = []
        
        for entry in feed.entries[:20]:  # Limit to 20 most recent
            # Extract ticker symbols from title/description
            text = f"{entry.get('title', '')} {entry.get('description', '')}"
            tickers = extract_tickers(text)
            
            # Calculate sentiment score (basic implementation)
            sentiment_score = calculate_basic_sentiment(text)
            
            articles.append({
                'id': entry.get('id') or entry.get('link'),
                'title': entry.get('title', ''),
                'description': entry.get('summary', '')[:500],  # Limit length
                'link': entry.get('link', ''),
                'pub_date': entry.get('published', ''),
                'source': url.split('//')[1].split('/')[0],  # Domain
                'tickers': tickers,
                'sentiment_score': sentiment_score,
                'relevance_score': calculate_relevance_score(text)
            })
        
        return articles
    except Exception as e:
        print(f"Error fetching RSS feed {url}: {e}")
        return []

def extract_tickers(text: str) -> List[str]:
    """
    Extract potential ticker symbols from text (simple regex approach)
    """
    # Match 1-5 uppercase letters (potential tickers)
    pattern = r'\b[A-Z]{1,5}\b'
    matches = re.findall(pattern, text)
    
    # Common false positives to filter out
    common_words = {'THE', 'AND', 'FOR', 'ARE', 'YOU', 'SAY', 'BUT', 'NOT', 'HAS', 'CAN', 'HER', 'WAS', 'HIS', 'GET', 'ITS', 'AVE', 'INC', 'CORP'}
    
    tickers = [match for match in matches if match not in common_words and len(match) >= 2]
    
    # Filter for likely tickers based on financial relevance
    # Check against a list of common financial terms or known tickers
    likely_tickers = []
    for ticker in tickers:
        # Add basic filtering to reduce false positives
        if ticker in ['SPY', 'QQQ', 'IWM', 'DIA', 'TLT', 'GLD', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'JPM', 'BAC', 'XOM', 'CVX', 'V', 'MA', 'PG', 'KO', 'DIS', 'MCD', 'GE', 'BA', 'MMM', 'IBM', 'INTC', 'CSCO', 'PEP', 'KO', 'TGT', 'WMT', 'HD', 'NKE', 'ADBE', 'CRM', 'CMCSA', 'AMGN', 'HON', 'UNH', 'MRK', 'ABBV', 'LLY', 'DHR', 'MDT', 'TXN', 'ACN', 'NEE', 'ABT', 'AVGO', 'COST', 'QCOM', 'TMUS', 'LIN', 'LMT', 'RTX', 'CAT', 'UPS', 'LOW', 'GS', 'BLK', 'BK', 'AXP', 'MS', 'USB', 'C', 'COF', 'SYF', 'PNC', 'TROW', 'BKNG', 'EXPE', 'MAR', 'HLT', 'DISCK', 'FOXA', 'FOX', 'NWS', 'NWSA', 'PAYX', 'ADP', 'INTU', 'CTSH', 'DXC', 'SYK', 'ISRG', 'ZBH', 'EW', 'DLR', 'FRC', 'CBRE', 'COO', 'CAH', 'TEL', 'HSY', 'EL', 'CL', 'KMB', 'GIS', 'MMM', 'EMR', 'ETN', 'ROK', 'COL', 'GD', 'HII', 'LHX', 'TXT', 'TDG', 'AME', 'DE', 'IRM', 'PKG', 'GLW', 'IP', 'TAP', 'GPC', 'SNA', 'MAS', 'DOV', 'ALLE', 'JCI', 'SWK', 'NOC', 'LMT', 'XEL', 'ES', 'LNT', 'AEP', 'ETR', 'PCG', 'SRE', 'EVRG', 'DTE', 'CMS', 'PNW', 'WEC', 'AEE', 'CNP', 'NI', 'FE', 'PEG', 'OKE', 'WMB', 'BXP', 'COO', 'HIG', 'MMC', 'AFL', 'MET', 'PRU', 'ALL', 'PJG', 'GL', 'HUM', 'CI', 'ANTM', 'CVS', 'ABC', 'CCI', 'SBAC', 'AMT', 'DLR', 'SPG', 'PSA', 'O', 'VNO', 'PEAK', 'EXR', 'IRM', 'LEG', 'FRT', 'KIM', 'GGP', 'MAC', 'SKT', 'DDR', 'AKR', 'CBL', 'SRG', 'WPG', 'ESS', 'REXR', 'HIW', 'SNDR', 'EXLS', 'IONS', 'VRTX', 'REGN', 'GILD', 'BIIB', 'CELG', 'AMGN', 'VRTX', 'ILMN', 'IDXX', 'BECN', 'CHRW', 'FDX', 'UPS', 'EXPD', 'XPO', 'CNX', 'DVN', 'EOG', 'MRO', 'OXY', 'PXD', 'APA', 'HES', 'COP', 'COG', 'VLO', 'PSX', 'MPC', 'ANDV', 'TSO', 'HFC', 'TGT', 'WMT', 'COST', 'BBY', 'HD', 'LOW', 'TJX', 'KSS', 'JWN', 'ORLY', 'AZO', 'ANF', 'AEO', 'GPS', 'URBN', 'BBBY', 'TIF', 'SIG', 'BOOK', 'CDR', 'EPR', 'SKX', 'LEVI', 'NKE', 'UA', 'LULU', 'COLM', 'JILL', 'RL', 'COH', 'VFC', 'DECK', 'ROST', 'TSCO', 'AZO', 'ORLY', 'ANF', 'AEO', 'GPS', 'URBN', 'BBBY', 'TIF', 'SIG', 'BOOK', 'CDR', 'EPR', 'SKX', 'LEVI', 'NKE', 'UA', 'LULU', 'COLM', 'JILL', 'RL', 'COH', 'VFC', 'DECK', 'ROST', 'TSCO']:
            if ticker in tickers:
                likely_tickers.append(ticker)
            elif len(ticker) == 2 and ticker not in ['AM', 'PM', 'TV', 'UK', 'US', 'EU', 'CA', 'NY']:  # Common 2-letter abbreviations
                likely_tickers.append(ticker)
        elif len(ticker) >= 3:  # Likely financial tickers are 3+ chars
            likely_tickers.append(ticker)
    
    return list(set(likely_tickers))  # Remove duplicates

def calculate_basic_sentiment(text: str) -> float:
    """
    Calculate basic sentiment score using keywords
    """
    positive_keywords = [
        'rise', 'gain', 'up', 'bull', 'positive', 'strong', 'beat', 'surge', 
        'expand', 'prospect', 'grow', 'high', 'soar', 'profit', 'success', 
        'upgrade', 'momentum', 'win', 'breakthrough', 'rally', 'jump', 'gain',
        'exciting', 'outperform', 'buy', 'recommend'
    ]
    
    negative_keywords = [
        'fall', 'loss', 'down', 'bear', 'negative', 'weak', 'miss', 'decline', 
        'contract', 'concern', 'shrink', 'low', 'crash', 'loss', 'failure', 
        'downgrade', 'trouble', 'troubles', 'sell', 'avoid', 'warning', 
        'problem', 'problems', 'disappoint', 'cut', 'dropped', 'drop'
    ]
    
    text_lower = text.lower()
    pos_count = sum(1 for word in positive_keywords if word in text_lower)
    neg_count = sum(1 for word in negative_keywords if word in text_lower)
    
    # Normalize to range [-1, 1]
    if pos_count + neg_count == 0:
        return 0.0
    
    total_sentiment = pos_count - neg_count
    return total_sentiment / (pos_count + neg_count + 1)  # +1 to avoid division by zero

def calculate_relevance_score(text: str) -> float:
    """
    Calculate relevance score based on financial keywords
    """
    financial_keywords = [
        'stock', 'market', 'price', 'trading', 'trade', 'invest', 'finance',
        'earnings', 'revenue', 'profit', 'loss', 'sales', 'revenue', 'eps',
        'quarter', 'results', 'report', 'forecast', 'prediction', 'dividend',
        'bond', 'yield', 'rate', 'fed', 'policy', 'inflation', 'gdp', 'cpi',
        'unemployment', 'economic', 'analyst', 'target', 'rating', 'outlook',
        'bullish', 'bearish', 'volatile', 'volatility', 'risk', 'return',
        'portfolio', 'mutual', 'fund', 'etf', 'index', 's&p', 'nasdaq',
        'dow', 'futures', 'options', 'commodities', 'oil', 'gold', 'silver'
    ]
    
    text_lower = text.lower()
    financial_terms = sum(1 for term in financial_keywords if term in text_lower)
    total_words = len(text_lower.split())
    
    if total_words == 0:
        return 0.0
    
    # Normalize relevance score from 0 to 1
    return min(financial_terms / max(total_words, 1) * 5, 1.0)  # Cap at 1.0

def compute_news_feed() -> Dict:
    """
    Compute real news feed from RSS sources
    """
    # Define reliable financial news sources
    news_sources = [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/topNews",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",  # Business
        "https://www.cnbc.com/id/15839135/device/rss/rss.html"   # Investing
    ]
    
    all_articles = []
    
    for source_url in news_sources:
        try:
            articles = fetch_rss_feed(source_url)
            all_articles.extend(articles)
        except Exception as e:
            print(f"Error processing source {source_url}: {e}")
            continue
    
    # Sort by publication date (most recent first) and limit
    all_articles.sort(key=lambda x: x.get('pub_date', ''), reverse=True)
    
    # Return the top 50 articles
    final_articles = all_articles[:50]
    
    # Create the final response
    result = {
        "articles": final_articles,
        "last_update": datetime.now().isoformat(),
        "source": ["reuters", "cnbc", "financial_rss_feeds"],
        "total_articles": len(final_articles),
        "fetched_at": datetime.now().isoformat()
    }
    
    return result


def _iter_articles() -> List[Dict[str, Any]]:
    """Return the latest computed article list with a defensive fallback."""
    try:
        return list(compute_news_feed().get("articles") or [])
    except Exception:
        return []


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        value_float = float(value)
        if value_float != value_float:  # NaN guard
            return default
        return value_float
    except (TypeError, ValueError):
        return default


async def get_news_events(
    tickers: Optional[List[str]] = None,
    event_types: Optional[List[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 200,
) -> Dict[str, Any]:
    """
    Compatibility async helper used by API handlers.
    """
    selected = _iter_articles()
    if tickers:
        selected = [
            row
            for row in selected
            if any(t.upper() in (row.get("tickers") or []) for t in tickers)
        ]

    if start:
        selected = [row for row in selected if str(row.get("pub_date", "")) >= str(start)]
    if end:
        selected = [row for row in selected if str(row.get("pub_date", "")) <= str(end)]

    # event_types placeholder: currently we emit only generic “headline” events
    # so we keep the filter to avoid breaking callers but no-op when absent.
    if event_types:
        # normalize as list for future expansion
        selected = [row for row in selected if "news" in [et.lower() for et in event_types]]

    limited = selected[: max(1, min(int(limit), 1000))]
    return {
        "events": limited,
        "count": len(limited),
        "source": ["news_service", "compat"],
    }


async def get_sentiment(limit: int = 100) -> Dict[str, Any]:
    """
    Compatibility async helper returning aggregated sentiment payload.
    """
    articles = _iter_articles()[: max(1, min(int(limit), 1000))]
    sentiments = []
    for row in articles:
        sentiments.append(
            {
                "ticker": ((row.get("tickers") or ["UNKNOWN"])[0] if row.get("tickers") else "UNKNOWN"),
                "sentiment": _to_float(row.get("sentiment_score", 0.0)),
                "score": _to_float(row.get("relevance_score", 0.0)),
                "title": row.get("title") or row.get("id"),
                "date": row.get("pub_date"),
            }
        )

    return {
        "sentiment": sentiments,
        "count": len(sentiments),
        "source": ["news_service", "compat"],
    }


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).replace(tzinfo=None)
    except Exception:
        return None


def _window_to_cutoff(window: str) -> Optional[datetime]:
    normalized = (window or "").strip().lower()
    if not normalized:
        return None
    hours_map = {
        "1h": 1,
        "6h": 6,
        "12h": 12,
        "1d": 24,
        "3d": 72,
        "7d": 24 * 7,
        "14d": 24 * 14,
        "30d": 24 * 30,
        "90d": 24 * 90,
        "last_day": 24,
        "last_week": 24 * 7,
        "last_month": 24 * 30,
    }
    hours = hours_map.get(normalized)
    if hours is None:
        return None
    return datetime.utcnow() - timedelta(hours=hours)


def get_news_feed(
    tickers: Optional[List[str]] = None,
    q: Optional[str] = None,
    limit: int = 50,
    window: str = "last_week",
    cache=None,
    since: Optional[str] = None,
    score_min: float = 0.0,
    region: str = "all",
):
    """
    Canonical news service contract.
    Returns an `ok/data` envelope while preserving legacy top-level fields.
    """
    try:
        # Legacy compatibility: some callers still pass cache callable as first positional arg.
        if callable(tickers) and cache is None and q is None:
            cache = tickers
            tickers = None

        safe_limit = max(1, min(int(limit), 400))
        requested_tickers = [str(t).upper() for t in (tickers or []) if str(t).strip()]
        query = (q or "").strip().lower()
        min_score = float(score_min or 0.0)
        cutoff = _window_to_cutoff(since or window)

        if callable(cache):
            cached = cache("news_feed", compute_news_feed, source=["rss_ingestion", "real_time"])
        else:
            cached = load_or_compute(
                "news_feed",
                compute_news_feed,
                source=["rss_ingestion", "real_time"],
                ttl_minutes=10,
            )

        if isinstance(cached, dict) and isinstance(cached.get("data"), dict):
            payload = cached.get("data") or {}
        else:
            payload = cached if isinstance(cached, dict) else {}

        articles = payload.get("articles") if isinstance(payload, dict) else []
        articles = articles if isinstance(articles, list) else []

        filtered: List[Dict[str, Any]] = []
        for row in articles:
            if not isinstance(row, dict):
                continue

            row_tickers = [str(t).upper() for t in (row.get("tickers") or []) if str(t).strip()]
            if requested_tickers and not set(requested_tickers).intersection(row_tickers):
                continue

            if query:
                haystack = f"{row.get('title', '')} {row.get('description', '')}".lower()
                if query not in haystack:
                    continue

            row_score = row.get("score", row.get("relevance_score", row.get("sentiment_score", 0.0)))
            if _to_float(row_score, 0.0) < min_score:
                continue

            if cutoff is not None:
                published_at = (
                    row.get("published_at")
                    or row.get("pub_date")
                    or row.get("published")
                    or row.get("date")
                )
                parsed_dt = _parse_datetime(published_at)
                if parsed_dt and parsed_dt < cutoff:
                    continue

            filtered.append(row)

        result_articles = filtered[:safe_limit]
        generated_at = payload.get("generated_at") if isinstance(payload, dict) else None
        last_update = payload.get("last_update") if isinstance(payload, dict) else None
        source = payload.get("source") if isinstance(payload, dict) else None

        data = {
            "articles": result_articles,
            "items": result_articles,
            "count": len(result_articles),
            "total_articles": len(result_articles),
            "generated_at": generated_at or datetime.utcnow().isoformat(),
            "last_update": last_update or datetime.utcnow().isoformat(),
            "freshness": payload.get("freshness") if isinstance(payload, dict) else None,
            "source": source if isinstance(source, list) else ["news_service", "rss_ingestion"],
            "filters_applied": {
                "tickers": requested_tickers,
                "q": q,
                "since": since,
                "window": window,
                "score_min": min_score,
                "region": region,
                "limit": safe_limit,
            },
        }
        return {"ok": True, "data": data, **data}
    except Exception as exc:
        data = {
            "articles": [],
            "items": [],
            "count": 0,
            "total_articles": 0,
            "generated_at": datetime.utcnow().isoformat(),
            "last_update": datetime.utcnow().isoformat(),
            "freshness": None,
            "source": ["news_service", "error_fallback"],
            "filters_applied": {
                "tickers": tickers or [],
                "q": q,
                "since": since,
                "window": window,
                "score_min": score_min,
                "region": region,
                "limit": limit,
            },
            "error": str(exc),
        }
        return {"ok": False, "error": str(exc), "data": data, **data}
