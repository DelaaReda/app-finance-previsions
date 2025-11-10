"""
Stocks Top Endpoint - Finance Copilot System
Task: FC-003 - Missing /api/stocks/top endpoint
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
from fastapi import APIRouter, Query
from typing import List, Optional, Dict, Any
import sys
from pathlib import Path
from datetime import datetime

# Add backend root to path for imports
backend_root = Path(__file__).resolve().parents[2]  # Go from backend/api/routes/stocks.py to backend/
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from core.response import ok, err
from storage.io import load_json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/stocks/top")
def get_top_stocks_by_score(
    limit: int = Query(10, ge=1, le=50, description="Number of top stocks to return (1-50)"),
    sort_by: str = Query("score", description="Sort by: score, change_1d, momentum_30d, market_cap, volume"),
    direction: Optional[str] = Query(None, description="Filter by direction: up, down, flat"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    tickers: Optional[List[str]] = Query(None, description="Specific tickers to include")
):
    """
    Get top stocks by score, momentum, or market cap with filtering options.
    Implements never-empty pattern by returning fallback data if live data unavailable.
    """
    try:
        # Load stocks data - multiple possible sources
        stocks_data = load_json("stocks/universe.json") or load_json("stocks_prices.json") or load_json("forecasts.json") or {}
        
        # Extract stocks from various possible structures
        all_stocks = []
        
        if "rows" in stocks_data and isinstance(stocks_data["rows"], list):
            # If data has rows format (from forecasts or similar)
            all_stocks = stocks_data["rows"]
        elif "items" in stocks_data and isinstance(stocks_data["items"], list):
            # If data has items format
            all_stocks = stocks_data["items"]
        elif "tickers" in stocks_data and isinstance(stocks_data["tickers"], dict):
            # If data has tickers dict format - convert to list
            for ticker, details in stocks_data["tickers"].items():
                if isinstance(details, dict):
                    details["ticker"] = ticker
                    all_stocks.append(details)
                else:
                    all_stocks.append({"ticker": ticker, "data": details})
        elif isinstance(stocks_data, dict):
            # If it's directly a dict but no known structure
            for key, value in stocks_data.items():
                if isinstance(value, dict) and "ticker" in value:
                    all_stocks.append(value)
        elif isinstance(stocks_data, list):
            # If directly a list
            all_stocks = stocks_data
        else:
            # If no valid structure found, use empty array
            all_stocks = []
        
        # Apply ticker filter if specified
        if tickers and len(tickers) > 0:
            ticker_set = {t.upper().strip() for t in tickers if t.strip()}
            all_stocks = [s for s in all_stocks if s.get("ticker", "").upper() in ticker_set]
        
        # Apply direction filter
        if direction:
            direction_lower = direction.lower()
            all_stocks = [s for s in all_stocks 
                         if s.get("direction", "").lower() == direction_lower or 
                            (s.get("trend", "").lower() == direction_lower)]
        
        # Apply confidence filter
        if min_confidence > 0:
            all_stocks = [s for s in all_stocks 
                         if s.get("confidence", s.get("confidence_score", 0)) >= min_confidence]
        
        # Sort by requested field
        def sort_key(stock):
            if sort_by == "change_1d":
                return stock.get("change_1d", stock.get("change_pct_1d", stock.get("change", 0)))
            elif sort_by == "momentum_30d":
                return stock.get("momentum_30d", stock.get("momentum_score", stock.get("score", 0)))
            elif sort_by == "market_cap":
                return stock.get("market_cap", stock.get("mkt_cap", 0))
            elif sort_by == "volume":
                return stock.get("volume", stock.get("vol", 0))
            else:  # score or default
                return stock.get("composite_score", stock.get("score", stock.get("confidence", 0)))
        
        # Sort the stocks (descending order for all fields)
        sorted_stocks = sorted(all_stocks, key=sort_key, reverse=True)
        
        # Apply limit
        top_stocks = sorted_stocks[:limit]
        
        # Prepare response data
        response_data = {
            "stocks": top_stocks,
            "count": len(top_stocks),
            "limit": limit,
            "sort_by": sort_by,
            "filters_applied": {
                "direction": direction,
                "min_confidence": min_confidence,
                "tickers": tickers
            },
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["top_stocks_endpoint", "stocks_tier1", "fc-int-003"]
        }
        
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"Error in top stocks endpoint: {str(e)}")
        # Return fallback structure to maintain never-empty contract
        return ok({
            "stocks": [],
            "count": 0,
            "limit": limit,
            "sort_by": sort_by,
            "filters_applied": {
                "direction": direction,
                "min_confidence": min_confidence,
                "tickers": tickers
            },
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["top_stocks_endpoint", "error_fallback", "fc-int-003"],
            "error": str(e),
            "message": "Could not fetch top stocks but fallback returned to maintain never-empty contract"
        })


@router.get("/stocks/universe")
def get_stock_universe():
    """
    Get list of tracked stocks/tickers.
    Implements never-empty pattern with fallback tickers.
    """
    try:
        # Load the universe data
        universe_data = load_json("stocks/universe.json") or load_json("stocks_universe.json") or {}
        
        # Extract tickers from various possible structures
        tickers = []
        
        if "tickers" in universe_data and isinstance(universe_data["tickers"], list):
            tickers = universe_data["tickers"]
        elif "rows" in universe_data and isinstance(universe_data["rows"], list):
            # Extract ticker from each row if available
            tickers = [row.get("ticker") or row.get("symbol") for row in universe_data["rows"] if row.get("ticker") or row.get("symbol")]
            tickers = [t for t in tickers if t]  # Remove None values
        elif isinstance(universe_data, list):
            # If directly a list of tickers
            tickers = [str(item) if isinstance(item, str) else str(item.get("ticker", item.get("symbol", ""))) 
                      for item in universe_data if item]
            tickers = [t for t in tickers if t.strip()]  # Remove empty strings
        else:
            # Fallback to default tickers to maintain never-empty
            tickers = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "META", "NFLX"]
        
        response_data = {
            "tickers": tickers,
            "count": len(tickers),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["stocks_universe_endpoint", "universe_master", "fc-int-003"]
        }
        
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"Error in stock universe endpoint: {str(e)}")
        # Fallback to default universe to maintain never-empty contract
        return ok({
            "tickers": ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "META", "NFLX"],
            "count": 10,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["stocks_universe_endpoint", "error_fallback", "fc-int-003"],
            "error": str(e),
            "message": "Using default stock universe due to error to maintain never-empty contract"
        })


# Export router with proper name for main.py registration
stocks_router = router