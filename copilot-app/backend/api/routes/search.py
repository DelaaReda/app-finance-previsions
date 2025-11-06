"""
Search API Routes
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: API-SEARCH-001 - Global search functionality
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from core.response import ok, err
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


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
        
        logger.info(f"Search tickers: found {len(matches)} matches")
        
        return ok({
            "query": q,
            "matches": matches,
            "total": len(matches),
            "has_more": len(matches) == limit
        })
        
    except Exception as e:
        logger.error(f"Error searching tickers: {str(e)}")
        return err(f"Search failed: {str(e)}", code=500)


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
        
        return ok({
            "query": q,
            "results": results,
            "total": total
        })
        
    except Exception as e:
        logger.error(f"Error in global search: {str(e)}")
        return err(f"Global search failed: {str(e)}", code=500)


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
        
        return ok({
            "sectors": sectors,
            "total": len(sectors)
        })
        
    except Exception as e:
        logger.error(f"Error getting sectors: {str(e)}")
        return err(f"Failed to get sectors: {str(e)}", code=500)
