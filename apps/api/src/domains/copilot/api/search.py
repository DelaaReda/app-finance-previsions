"""
Search API Routes
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: API-SEARCH-001 - Global search functionality
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from core.response import ok
import logging
    
try:
    from services.service_standard import ensure_decision_contract, utc_now_iso  # type: ignore
except Exception:  # pragma: no cover
    try:
        from platform.legacy.services.service_standard import (  # type: ignore
            ensure_decision_contract,
            utc_now_iso,
        )
    except Exception:  # pragma: no cover
        ensure_decision_contract = None  # type: ignore
        utc_now_iso = None  # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter()


def _now_iso() -> str:
    if callable(utc_now_iso):
        return utc_now_iso()
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _apply_search_contract(payload: Dict[str, Any], *, source: str) -> Dict[str, Any]:
    if callable(ensure_decision_contract):
        ensure_decision_contract(
            payload,
            default_source=source,
            verdict="hold",
            confidence=0.45,
            why=["Search payload is informative-only, not an action recommendation."],
            risk_level="low",
            freshness=payload.get("freshness"),
        )
        return payload

    payload.setdefault("verdict", "hold")
    payload.setdefault("confidence", 0.45)
    payload.setdefault("why", ["Search payload is informative-only, not an action recommendation."])
    payload.setdefault("risk_level", "low")
    payload.setdefault("risk", {"level": "low", "caveat": ""})
    payload.setdefault("risk_flag", False)
    payload.setdefault("generated_at", payload.get("generated_at") or _now_iso())
    payload.setdefault("freshness", payload.get("freshness") or payload.get("generated_at"))
    payload.setdefault("source", [source])
    return payload


def _search_error_payload(
    *, source: str, query: Optional[str] = None, error: str, **extra: Any
) -> Dict[str, Any]:
    now_iso = _now_iso()
    payload: Dict[str, Any] = {
        "query": query,
        "total": 0,
        "generated_at": now_iso,
        "freshness": now_iso,
        "source": [source, "error_fallback"],
        "error": error,
        "message": "Search temporarily unavailable.",
    }
    payload.update(extra)
    return _apply_search_contract(payload, source=source)


# Ticker metadata (can be extended with company names, sectors, etc.)
TICKER_METADATA = {
    # Tech
    "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
    "MSFT": {"name": "Microsoft Corporation", "sector": "Technology"},
    "GOOGL": {"name": "Alphabet Inc.", "sector": "Technology"},
    "GOOG": {"name": "Alphabet Inc. (Class C)", "sector": "Technology"},
    "META": {"name": "Meta Platforms Inc.", "sector": "Technology"},
    "NVDA": {"name": "NVIDIA Corporation", "sector": "Technology"},
    "AMD": {"name": "Advanced Micro Devices", "sector": "Technology"},
    "INTC": {"name": "Intel Corporation", "sector": "Technology"},
    "TSLA": {"name": "Tesla Inc.", "sector": "Technology"},
    "NFLX": {"name": "Netflix Inc.", "sector": "Technology"},
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Technology"},
    # Finance
    "JPM": {"name": "JPMorgan Chase & Co.", "sector": "Finance"},
    "BAC": {"name": "Bank of America", "sector": "Finance"},
    "GS": {"name": "Goldman Sachs", "sector": "Finance"},
    "MS": {"name": "Morgan Stanley", "sector": "Finance"},
    "C": {"name": "Citigroup Inc.", "sector": "Finance"},
    "WFC": {"name": "Wells Fargo", "sector": "Finance"},
    "BRK.B": {"name": "Berkshire Hathaway", "sector": "Finance"},
    # Healthcare
    "JNJ": {"name": "Johnson & Johnson", "sector": "Healthcare"},
    "PFE": {"name": "Pfizer Inc.", "sector": "Healthcare"},
    "UNH": {"name": "UnitedHealth Group", "sector": "Healthcare"},
    "ABBV": {"name": "AbbVie Inc.", "sector": "Healthcare"},
    "TMO": {"name": "Thermo Fisher Scientific", "sector": "Healthcare"},
    "MRK": {"name": "Merck & Co.", "sector": "Healthcare"},
    "LLY": {"name": "Eli Lilly and Company", "sector": "Healthcare"},
    # Energy
    "XOM": {"name": "Exxon Mobil", "sector": "Energy"},
    "CVX": {"name": "Chevron Corporation", "sector": "Energy"},
    "COP": {"name": "ConocoPhillips", "sector": "Energy"},
    "SLB": {"name": "Schlumberger", "sector": "Energy"},
    "EOG": {"name": "EOG Resources", "sector": "Energy"},
    # Consumer
    "WMT": {"name": "Walmart Inc.", "sector": "Consumer"},
    "HD": {"name": "Home Depot", "sector": "Consumer"},
    "MCD": {"name": "McDonald's Corporation", "sector": "Consumer"},
    "NKE": {"name": "Nike Inc.", "sector": "Consumer"},
    "SBUX": {"name": "Starbucks Corporation", "sector": "Consumer"},
    "PG": {"name": "Procter & Gamble", "sector": "Consumer"},
    "KO": {"name": "Coca-Cola Company", "sector": "Consumer"},
    "PEP": {"name": "PepsiCo Inc.", "sector": "Consumer"},
    # ETFs/Indices
    "SPY": {"name": "SPDR S&P 500 ETF", "sector": "ETF/Index"},
    "QQQ": {"name": "Invesco QQQ Trust", "sector": "ETF/Index"},
    "IWM": {"name": "iShares Russell 2000 ETF", "sector": "ETF/Index"},
    "DIA": {"name": "SPDR Dow Jones Industrial Average ETF", "sector": "ETF/Index"},
    "TLT": {"name": "iShares 20+ Year Treasury Bond ETF", "sector": "ETF/Index"},
    "GLD": {"name": "SPDR Gold Trust", "sector": "ETF/Index"},
    "VIX": {"name": "CBOE Volatility Index", "sector": "ETF/Index"},
}


def fuzzy_match(query: str, target: str, threshold: float = 0.7) -> bool:
    """
    Simple fuzzy matching algorithm
    Returns True if query matches target with threshold similarity
    """
    query = query.lower()
    target = target.lower()
    
    # Exact match
    if query == target:
        return True
    
    # Substring match
    if query in target:
        return True
    
    # Simple edit distance approximation
    if len(query) == len(target):
        matches = sum(q == t for q, t in zip(query, target))
        similarity = matches / len(query)
        return similarity >= threshold
    
    return False


@router.get("/tickers")
async def search_tickers(
    q: str = Query(..., description="Search query (ticker symbol or company name)", min_length=1),
    limit: int = Query(10, le=50, description="Maximum number of results"),
    sector: Optional[str] = Query(None, description="Filter by sector")
):
    """
    Search for tickers by symbol or company name
    
    **Features:**
    - Symbol search (e.g., "AAPL")
    - Fuzzy matching (e.g., "APPL" → "AAPL")
    - Company name search (e.g., "Apple" → "AAPL")
    - Sector filtering
    
    **Examples:**
    - `/api/search/tickers?q=apple` → Returns AAPL
    - `/api/search/tickers?q=tech&sector=Technology` → Returns all tech stocks
    - `/api/search/tickers?q=APPL` → Returns AAPL (fuzzy match)
    
    **Returns:**
    ```json
    {
      "query": "apple",
      "matches": [
        {
          "ticker": "AAPL",
          "name": "Apple Inc.",
          "sector": "Technology",
          "match_type": "name"
        }
      ],
      "total": 1
    }
    ```
    """
    try:
        logger.info(f"Search tickers: query='{q}', limit={limit}, sector={sector}")
        
        q_lower = q.lower()
        matches = []
        
        for ticker, metadata in TICKER_METADATA.items():
            # Skip if sector filter doesn't match
            if sector and metadata["sector"] != sector:
                continue
            
            match_type = None
            
            # Check ticker symbol match (exact or fuzzy)
            if fuzzy_match(q_lower, ticker):
                match_type = "symbol"
            # Check company name match
            elif q_lower in metadata["name"].lower():
                match_type = "name"
            # Check sector match (if no specific sector filter)
            elif not sector and q_lower in metadata["sector"].lower():
                match_type = "sector"
            
            if match_type:
                matches.append({
                    "ticker": ticker,
                    "name": metadata["name"],
                    "sector": metadata["sector"],
                    "match_type": match_type
                })
        
        # Sort matches: symbol matches first, then name matches, then sector
        match_priority = {"symbol": 0, "name": 1, "sector": 2}
        matches.sort(key=lambda m: (match_priority.get(m["match_type"], 3), m["ticker"]))
        
        # Limit results
        matches = matches[:limit]
        now_iso = _now_iso()
        has_more = len(matches) == limit and limit > 0
        response_data = {
            "query": q,
            "matches": matches,
            "total": len(matches),
            "has_more": has_more,
            "generated_at": now_iso,
            "freshness": now_iso,
            "source": ["search_tickers"],
        }
        _apply_search_contract(response_data, source="search_tickers")
        
        logger.info(f"Search tickers: found {len(matches)} matches")
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"Error searching tickers: {str(e)}")
        return ok(
            _search_error_payload(
                source="search_tickers",
                error=str(e),
                query=q,
                matches=[],
                has_more=False,
            )
        )


@router.get("/global")
async def search_global(
    q: str = Query(..., description="Global search query", min_length=2),
    limit: int = Query(20, le=100, description="Maximum number of results"),
    types: Optional[str] = Query(None, description="Comma-separated types: tickers,news,notes")
):
    """
    Global search across all data types
    
    **Searches:**
    - Tickers (symbols & company names)
    - News articles (titles & content) - TODO
    - User notes (content) - TODO
    
    **Examples:**
    - `/api/search/global?q=apple` → Returns tickers, news, notes about Apple
    - `/api/search/global?q=inflation&types=news` → Returns only news about inflation
    
    **Returns:**
    ```json
    {
      "query": "apple",
      "results": {
        "tickers": [...],
        "news": [...],
        "notes": [...]
      },
      "total": 15
    }
    ```
    """
    try:
        logger.info(f"Global search: query='{q}', limit={limit}, types={types}")
        
        # Parse types filter
        search_types = set()
        if types:
            search_types = set(t.strip() for t in types.split(","))
        else:
            search_types = {"tickers", "news", "notes"}
        
        results = {}
        total = 0
        
        # Search tickers
        if "tickers" in search_types:
            ticker_results = await search_tickers(q=q, limit=min(limit, 10))
            if ticker_results.get("ok"):
                results["tickers"] = ticker_results["data"]["matches"]
                total += len(results["tickers"])
        
        # TODO: Search news (when news search is implemented)
        if "news" in search_types:
            results["news"] = []  # Placeholder
        
        # TODO: Search notes (when notes search is implemented)
        if "notes" in search_types:
            results["notes"] = []  # Placeholder
        
        logger.info(f"Global search: found {total} results")
        now_iso = _now_iso()
        response_data = {
            "query": q,
            "results": results,
            "total": total,
            "generated_at": now_iso,
            "freshness": now_iso,
            "source": ["search_global"],
        }
        _apply_search_contract(response_data, source="search_global")
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"Error in global search: {str(e)}")
        return ok(
            _search_error_payload(
                source="search_global",
                error=str(e),
                query=q,
                results={},
                total=0,
                execution_time=0,
            )
        )


import time
from core.response import ok
from storage.io import load_json

def calculate_similarity(query: str, target: str) -> float:
    """
    Calculate similarity between query and target string using a simple algorithm
    Returns a score between 0 and 1 (1 being exact match)
    """
    query_lower = query.lower()
    target_lower = target.lower()
    
    if query_lower == target_lower:
        return 1.0
    
    # Check for substring match
    if query_lower in target_lower:
        return 0.8
    
    # Simple word overlap check
    query_words = set(query_lower.split())
    target_words = set(target_lower.split())
    overlap = len(query_words.intersection(target_words))
    
    if len(query_words) == 0 or len(target_words) == 0:
        return 0.0
    
    # Jaccard similarity
    union = len(query_words.union(target_words))
    return overlap / union if union > 0 else 0.0


@router.get("/sectors")
async def get_sectors():
    """
    Get list of available sectors
    
    **Returns:**
    ```json
    {
      "sectors": ["Technology", "Finance", "Healthcare", ...]
    }
    ```
    """
    try:
        sectors = sorted(set(meta["sector"] for meta in TICKER_METADATA.values()))

        response_data = {
            "sectors": sectors,
            "total": len(sectors)
        }
        _apply_search_contract(response_data, source="search_sectors")
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"Error getting sectors: {str(e)}")
        return ok(
            _search_error_payload(
                source="search_sectors",
                error=str(e),
                query=None,
                sectors=[],
                total=0,
            )
        )


@router.get("/universal")
async def universal_search_endpoint(
    q: str = Query(..., description="Search query string", min_length=1),
    type: Optional[str] = Query(None, description="Type of search (stocks, news, briefs, forecasts) or 'all'"),
    tickers: Optional[str] = Query(None, description="Restrict search to specific tickers (comma-separated)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results per category"),
    sort_by: str = Query('relevance', description="Sort order: relevance, date, score"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """
    Universal search endpoint for stocks, news, briefs, and forecasts - FC-API-035
    
    **Parameters:**
    - q: Search query (required)
    - type: Search specific data type or 'all' (default: all)
    - tickers: Filter by specific tickers (comma-separated)
    - limit: Max results per category (default: 20, max: 100)
    - sort_by: Order results by 'relevance', 'date', 'score' (default: relevance)
    - date_from, date_to: Date range filters
    
    **Returns:**
    ```json
    {
      "query": "NVDA",
      "results": {
        "stocks": [...],
        "news": [...],
        "briefs": [...],
        "forecasts": [...]
      },
      "total": 45,
      "execution_time": 123
    }
    ```
    """
    start_time = time.time()
    
    # Normalize search types
    search_types = ['stocks', 'news', 'briefs', 'forecasts']
    if type and type.lower() != 'all':
        search_types = [t.strip().lower() for t in type.split(',') if t.strip()]
    
    # Parse ticker filter
    ticker_list = [t.strip().upper() for t in tickers.split(',')] if tickers else []
    
    results = {}
    total_results = 0
    
    try:
        # Search stocks
        if 'stocks' in search_types:
            stocks_data = load_json('stocks_universe') or []
            filtered_stocks = []
            
            for stock in stocks_data:
                ticker = str(stock.get('ticker', ''))
                name = str(stock.get('name', ''))
                
                # Filter by tickers if specified
                if ticker_list and ticker.upper() not in ticker_list:
                    continue
                
                # Calculate relevance score
                ticker_relevance = calculate_similarity(q, ticker)
                name_relevance = calculate_similarity(q, name)
                
                max_relevance = max(ticker_relevance, name_relevance)
                
                # Only include if relevance score is above threshold
                if max_relevance > 0.1:
                    filtered_stocks.append({
                        **stock,
                        'relevance': max_relevance,
                        'match_field': 'ticker' if ticker_relevance > name_relevance else 'name'
                    })
            
            # Sort by relevance if requested
            if sort_by == 'relevance':
                filtered_stocks.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            # Sort by score if available
            elif sort_by == 'score':
                filtered_stocks.sort(key=lambda x: x.get('score', 0) or x.get('composite_score', 0), reverse=True)
            
            results['stocks'] = filtered_stocks[:limit]
            total_results += len(results['stocks'])
        
        # Search news
        if 'news' in search_types:
            news_data = load_json('news_feed') or {'articles': []}
            articles = news_data.get('articles', [])
            
            # Check if articles is nested in data (common pattern)
            if not articles and 'data' in news_data:
                nested_data = news_data['data']
                if isinstance(nested_data, list):
                    articles = nested_data
                elif isinstance(nested_data, dict) and 'articles' in nested_data:
                    articles = nested_data['articles']
            
            filtered_news = []
            for article in articles:
                title = str(article.get('title', ''))
                content = str(article.get('summary', '') or article.get('description', '') or '')
                tickers_in_article = article.get('tickers', []) or []
                
                # Filter by tickers if specified
                if ticker_list and not any(ticker.upper() in [t.upper() for t in tickers_in_article] for ticker in ticker_list):
                    continue
                
                # Calculate relevance score
                title_relevance = calculate_similarity(q, title)
                content_relevance = calculate_similarity(q, content)
                ticker_tag_relevance = calculate_similarity(q, ' '.join(map(str, tickers_in_article))) if tickers_in_article else 0
                
                max_relevance = max(title_relevance, content_relevance, ticker_tag_relevance)
                
                # Only include if relevance score is above threshold
                if max_relevance > 0.1 or q.lower() in [t.lower() for t in tickers_in_article]:
                    filtered_news.append({
                        **article,
                        'relevance': max_relevance,
                        'match_field': 'title' if title_relevance >= content_relevance else 'content'
                    })
            
            # Sort by relevance or date if requested
            if sort_by == 'relevance':
                filtered_news.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            elif sort_by == 'date':
                filtered_news.sort(key=lambda x: x.get('pub_date') or x.get('date') or '1970-01-01', reverse=True)
            
            results['news'] = filtered_news[:limit]
            total_results += len(results['news'])
        
        # Search briefs
        if 'briefs' in search_types:
            briefs_data = load_json('brief_weekly') or {}
            
            # Structure might vary - look for different formats
            brief_items = []
            if 'data' in briefs_data:
                brief_data = briefs_data['data']
                if isinstance(brief_data, list):
                    brief_items = brief_data
                elif isinstance(brief_data, dict):
                    # Common single-object format, might include top_signals, top_risks, etc.
                    for key in ['top_signals', 'top_risks', 'picks', 'highlights', 'signals', 'risks']:
                        if key in brief_data and isinstance(brief_data[key], list):
                            brief_items.extend(brief_data[key])
            # Check if briefs_data itself is an array of items
            elif isinstance(briefs_data, list):
                brief_items = briefs_data
            
            filtered_briefs = []
            for item in brief_items:
                title = str(item.get('title', '') or item.get('ticker', '') or '')
                content = str(item.get('summary', '') or item.get('description', '') or str(item.get('reason', '')) or '')
                
                # Calculate relevance score
                title_relevance = calculate_similarity(q, title)
                content_relevance = calculate_similarity(q, content)
                
                max_relevance = max(title_relevance, content_relevance)
                
                # Only include if relevance score is above threshold
                if max_relevance > 0.1:
                    filtered_briefs.append({
                        **item,
                        'relevance': max_relevance,
                        'item_type': item.get('type', 'brief')
                    })
            
            if sort_by == 'relevance':
                filtered_briefs.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            elif sort_by == 'date':
                filtered_briefs.sort(key=lambda x: x.get('generated_at') or x.get('date') or '1970-01-01', reverse=True)
            
            results['briefs'] = filtered_briefs[:limit]
            total_results += len(results['briefs'])
        
        # Search forecasts
        if 'forecasts' in search_types:
            forecasts_data = load_json('forecasts') or {'rows': []}
            forecast_items = forecasts_data.get('rows', [])
            
            # Check alternative structures
            if not forecast_items and 'data' in forecasts_data:
                data = forecasts_data['data']
                if isinstance(data, list):
                    forecast_items = data
                elif isinstance(data, dict) and 'rows' in data:
                    forecast_items = data['rows']
            
            filtered_forecasts = []
            for forecast in forecast_items:
                ticker = str(forecast.get('ticker', '') or forecast.get('symbol', ''))
                horizon = str(forecast.get('horizon', ''))
                explanation = str(forecast.get('explanation', '') or forecast.get('reason', '') or '')
                
                # Filter by tickers if specified
                if ticker_list and ticker.upper() not in ticker_list:
                    continue
                
                # Calculate relevance score
                ticker_relevance = calculate_similarity(q, ticker)
                horizon_relevance = calculate_similarity(q, horizon)
                explanation_relevance = calculate_similarity(q, explanation)
                
                max_relevance = max(ticker_relevance, horizon_relevance, explanation_relevance)
                
                # Only include if relevance score is above threshold
                if max_relevance > 0.1:
                    filtered_forecasts.append({
                        **forecast,
                        'relevance': max_relevance,
                        'match_field': 'ticker' if ticker_relevance >= max(horizon_relevance, explanation_relevance) else
                                     'horizon' if horizon_relevance >= explanation_relevance else 'explanation'
                    })
            
            if sort_by == 'relevance':
                filtered_forecasts.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            elif sort_by == 'score':
                filtered_forecasts.sort(key=lambda x: x.get('score') or x.get('confidence', 0), reverse=True)
            
            results['forecasts'] = filtered_forecasts[:limit]
            total_results += len(results['forecasts'])
        
        # Calculate execution time
        exec_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Universal search completed: {total_results} results in {exec_time_ms}ms")
        
        # Prepare response
        response_data = {
            'query': q,
            'results': results,
            'total': total_results,
            'execution_time': exec_time_ms,
            'search_metadata': {
                'types_searched': search_types,
                'tickers_filtered': ticker_list if ticker_list else None,
                'date_range': {
                    'from': date_from,
                    'to': date_to
                } if date_from or date_to else None,
                'sort_by': sort_by
            }
        }
        _apply_search_contract(response_data, source="search_universal")
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"Error in universal search: {str(e)}", exc_info=True)
        return ok(
            _search_error_payload(
                source="search_universal",
                query=q,
                results={},
                total=0,
                execution_time=0,
                search_metadata={
                    "types_searched": [],
                    "tickers_filtered": [],
                    "date_range": None,
                    "sort_by": sort_by,
                },
                error=str(e),
            )
        )

# Export router with expected name for main.py registration
search_router = router
