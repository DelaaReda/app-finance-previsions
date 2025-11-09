"""
API Routes for Stocks - Dashboard Integration
Provides stock search, analysis, and screener endpoints
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Sprint 3 - Tâche 3.1 - Remplacer données factices par vraies API
"""
from fastapi import APIRouter, Query, Response
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime

from core.response import ok, err
from storage.io import load_json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stocks/search")
def search_stocks(
    q: str = Query(..., description="Search query (ticker symbol or company name)", min_length=1),
    limit: int = Query(10, le=50, description="Maximum number of results")
) -> Dict[str, Any]:
    """
    Search for stocks by ticker or company name with real price data.
    
    Uses /api/search/tickers for search, then enriches with current prices.
    
    Returns:
        List of stocks with ticker, name, current price, change, changePercent
    """
    try:
        # Use the search logic directly from TICKER_METADATA
        from api.routes.search import TICKER_METADATA, fuzzy_match
        
        q_lower = q.lower()
        matches = []
        
        for ticker, metadata in TICKER_METADATA.items():
            match_type = None
            
            # Check ticker symbol match (exact or fuzzy)
            if fuzzy_match(q_lower, ticker):
                match_type = "symbol"
            # Check company name match
            elif q_lower in metadata["name"].lower():
                match_type = "name"
            
            if match_type:
                matches.append({
                    "ticker": ticker,
                    "name": metadata["name"],
                    "sector": metadata["sector"],
                    "match_type": match_type
                })
        
        # Sort matches: symbol matches first, then name matches
        match_priority = {"symbol": 0, "name": 1}
        matches.sort(key=lambda m: (match_priority.get(m["match_type"], 3), m["ticker"]))
        
        # Limit results
        matches = matches[:limit]
        
        # Enrich with real price data
        enriched_results = []
        for match in matches:
            ticker = match.get("ticker")
            if not ticker:
                continue
            
            # Try to get current price from stored data or yfinance
            try:
                # Try to load from stored prices
                prices_data = load_json("stocks_prices") or {}
                ticker_data = prices_data.get("data", {}).get("tickers", {}).get(ticker, {})
                
                if ticker_data and "points" in ticker_data and len(ticker_data["points"]) > 0:
                    # Get latest price
                    latest_point = ticker_data["points"][-1]
                    current_price = latest_point[1] if isinstance(latest_point, (list, tuple)) else latest_point.get("value", 0)
                    
                    # Get previous price for change calculation
                    if len(ticker_data["points"]) > 1:
                        prev_point = ticker_data["points"][-2]
                        prev_price = prev_point[1] if isinstance(prev_point, (list, tuple)) else prev_point.get("value", 0)
                        change = current_price - prev_price
                        change_percent = (change / prev_price * 100) if prev_price != 0 else 0.0
                    else:
                        change = 0.0
                        change_percent = 0.0
                else:
                    # Fallback: try yfinance directly
                    try:
                        import yfinance as yf
                        stock = yf.Ticker(ticker)
                        info = stock.info
                        hist = stock.history(period="2d")
                        
                        if not hist.empty:
                            current_price = float(hist["Close"].iloc[-1])
                            if len(hist) > 1:
                                prev_price = float(hist["Close"].iloc[-2])
                                change = current_price - prev_price
                                change_percent = (change / prev_price * 100) if prev_price != 0 else 0.0
                            else:
                                change = 0.0
                                change_percent = 0.0
                        else:
                            current_price = 0.0
                            change = 0.0
                            change_percent = 0.0
                    except Exception as e:
                        logger.debug(f"Could not fetch price for {ticker}: {e}")
                        current_price = 0.0
                        change = 0.0
                        change_percent = 0.0
                
                enriched_results.append({
                    "ticker": ticker,
                    "name": match.get("name", f"{ticker} Corp"),
                    "sector": match.get("sector", "N/A"),
                    "price": current_price,
                    "change": change,
                    "changePercent": change_percent
                })
            except Exception as e:
                logger.debug(f"Error enriching {ticker}: {e}")
                # Still include the match but with default values
                enriched_results.append({
                    "ticker": ticker,
                    "name": match.get("name", f"{ticker} Corp"),
                    "sector": match.get("sector", "N/A"),
                    "price": 0.0,
                    "change": 0.0,
                    "changePercent": 0.0
                })
        
        return ok({
            "results": enriched_results,
            "count": len(enriched_results),
            "query": q,
            "generated_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in stock search: {str(e)}", exc_info=True)
        return ok({
            "results": [],
            "count": 0,
            "query": q,
            "error": str(e),
            "message": "Stock search temporarily unavailable",
            "generated_at": datetime.utcnow().isoformat()
        })


@router.get("/stocks/universe")
def get_stocks_universe() -> Dict[str, Any]:
    """
    Get list of tracked tickers.
    
    Returns:
        List of tickers in the universe
    """
    try:
        # Try to load from stored data
        universe_data = load_json("stocks_universe")
        
        if universe_data:
            tickers = universe_data.get("data", {}).get("tickers", [])
            if tickers:
                return ok({
                    "tickers": tickers,
                    "count": len(tickers),
                    "generated_at": datetime.utcnow().isoformat()
                })
        
        # Fallback to default universe
        default_universe = [
            "SPY", "QQQ", "DIA", "IWM",  # Indices
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",  # Tech
            "JPM", "BAC", "WFC", "GS",  # Finance
            "XOM", "CVX", "COP",  # Energy
            "JNJ", "UNH", "PFE", "ABBV"  # Healthcare
        ]
        
        return ok({
            "tickers": default_universe,
            "count": len(default_universe),
            "generated_at": datetime.utcnow().isoformat(),
            "source": "default"
        })
        
    except Exception as e:
        logger.error(f"Error getting universe: {str(e)}", exc_info=True)
        return ok({
            "tickers": [],
            "count": 0,
            "error": str(e),
            "generated_at": datetime.utcnow().isoformat()
        })

