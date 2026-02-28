"""
Stocks API Routes
Implements the /api/stocks endpoints for real stock data
"""
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime
import logging

from core.response import ok, err
from storage.io import load_json
from core.market_data import get_price_history, get_fundamentals

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks")

@router.get("/top-legacy")
async def get_top_stocks(
    limit: int = Query(10, ge=1, le=50, description="Number of top stocks to return"),
    sort_by: str = Query("score", description="Sort by: score, change_1d, momentum_30d, mcap"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    min_market_cap: Optional[float] = Query(None, description="Minimum market cap filter (billions)"),
    min_volume: Optional[float] = Query(None, description="Minimum trading volume filter")
):
    """
    Get top performing stocks by score, momentum, or market cap.
    Returns structured response with {ok: true, data: {...}} pattern.
    Implements never-empty with fallback to empty arrays if no data available.
    """
    try:
        # Load stocks data from storage
        prices_data = load_json("stocks/prices") or load_json("stocks_prices") or load_json("stocks") or {}
        metrics_data = load_json("stocks/metrics") or load_json("stocks_metrics") or {}
        
        # Extract stocks list from various possible structures
        stocks_list = []
        
        # Try different possible data structures
        if "tickers" in prices_data:
            prices = prices_data["tickers"]
        elif "data" in prices_data and "tickers" in prices_data["data"]:
            prices = prices_data["data"]["tickers"]
        elif isinstance(prices_data, dict) and any(ticker in ["SPY", "QQQ", "AAPL", "NVDA"] for ticker in prices_data.keys()):
            prices = prices_data  # Direct ticker structure
        else:
            prices = {}
        
        # Get metrics if available
        metrics = metrics_data.get("metrics", {}) or metrics_data.get("data", {}).get("metrics", {})
        
        # Build comprehensive stock list
        for ticker, ticker_prices in prices.items():
            if not isinstance(ticker_prices, dict):
                continue
                
            # Get ticker-specific metrics
            ticker_metrics = metrics.get(ticker, {}) or metrics.get(ticker.upper(), {})
            
            # Calculate derived metrics from price history if available
            points = ticker_prices.get("points", [])
            if points:
                # Calculate recent performance metrics
                recent_prices = [p["close"] for p in points if "close" in p]
                if len(recent_prices) >= 2:
                    latest_price = recent_prices[-1]
                    prev_price = recent_prices[-2]
                    change_1d = ((latest_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0.0
                else:
                    change_1d = 0.0
            else:
                change_1d = 0.0
                latest_price = None
            
            stock_info = {
                "ticker": ticker.upper(),
                "price": latest_price or ticker_metrics.get("price") or 0.0,
                "change_1d": change_1d,
                "change_1d_pct": change_1d,
                "score": ticker_metrics.get("score") or ticker_metrics.get("composite_score") or 0.0,
                "momentum_30d": ticker_metrics.get("momentum_30d") or 0.0,
                "market_cap": ticker_metrics.get("market_cap") or ticker_metrics.get("mcap") or 0.0,
                "volume": ticker_metrics.get("volume") or ticker_metrics.get("avg_volume") or 0,
                "sector": ticker_metrics.get("sector") or "Unknown",
                "pe": ticker_metrics.get("pe") or ticker_metrics.get("pe_ratio"),
                "beta": ticker_metrics.get("beta"),
                "last_updated": ticker_prices.get("last_updated") or datetime.utcnow().isoformat()
            }
            
            # Apply filters
            if sector and stock_info.get("sector", "").lower() != sector.lower():
                continue
            if min_market_cap and stock_info.get("market_cap", 0) < min_market_cap:
                continue
            if min_volume and stock_info.get("volume", 0) < min_volume:
                continue
            
            stocks_list.append(stock_info)
        
        # If no data available from storage, compute a minimal real-time fallback using market_data
        if not stocks_list:
            logger.info("No persisted stocks data found; computing fallback metrics from market_data")
            default_universe = [
                "NVDA", "META", "TSLA", "AAPL", "MSFT", "GOOGL", "SPY", "QQQ"
            ]
            universe = default_universe[:limit]
            for symbol in universe:
                try:
                    df = get_price_history(symbol, interval="1d")
                    latest_price = None
                    change_1d = 0.0
                    if df is not None and not df.empty and "Close" in df.columns:
                        close = df["Close"].dropna()
                        if not close.empty:
                            latest_price = float(close.iloc[-1])
                            if len(close) > 1:
                                prev = float(close.iloc[-2])
                                change_1d = ((latest_price - prev) / prev) * 100 if prev else 0.0
                    facts = get_fundamentals(symbol) or {}
                    stocks_list.append({
                        "ticker": symbol,
                        "price": latest_price or facts.get("price") or 0.0,
                        "change_1d": change_1d,
                        "change_1d_pct": change_1d,
                        "score": 0.0,
                        "momentum_30d": 0.0,
                        "market_cap": facts.get("market_cap") or 0.0,
                        "volume": 0,
                        "sector": facts.get("sector") or "Unknown",
                        "pe": facts.get("pe"),
                        "beta": facts.get("beta"),
                        "last_updated": datetime.utcnow().isoformat()
                    })
                except Exception:
                    continue

        # Sort by requested field
        if sort_by == "change_1d":
            stocks_list.sort(key=lambda x: abs(x.get("change_1d", 0)), reverse=True)
        elif sort_by == "momentum_30d":
            stocks_list.sort(key=lambda x: x.get("momentum_30d", 0), reverse=True)
        elif sort_by == "mcap":
            stocks_list.sort(key=lambda x: x.get("market_cap", 0), reverse=True)
        elif sort_by == "volume":
            stocks_list.sort(key=lambda x: x.get("volume", 0), reverse=True)
        else:  # score or default
            stocks_list.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Limit results
        limited_stocks = stocks_list[:limit]
        
        # Create response with never-empty pattern
        response_data = {
            "stocks": limited_stocks,
            "count": len(limited_stocks),
            "total_available": len(stocks_list),
            "sort_by": sort_by,
            "filters_applied": {
                "sector": sector,
                "min_market_cap": min_market_cap,
                "min_volume": min_volume
            },
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["stocks_prices", "stocks_metrics"],
            "freshness": datetime.utcnow().isoformat(),
            "last_update": prices_data.get("last_update") or datetime.utcnow().isoformat()
        }
        
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"Error in get_top_stocks: {e}", exc_info=True)
        # Never return empty - always return structure with fallback data
        return ok({
            "stocks": [],
            "count": 0,
            "total_available": 0,
            "sort_by": sort_by,
            "filters_applied": {
                "sector": sector,
                "min_market_cap": min_market_cap,
                "min_volume": min_volume
            },
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback"],
            "freshness": datetime.utcnow().isoformat(),
            "last_update": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Top stocks temporarily unavailable, returning empty list per never-empty pattern"
        })


@router.get("/prices")
async def get_stocks_prices(
    ticker: Optional[str] = Query(None, description="Single ticker symbol"),
    tickers: Optional[str] = Query(None, description="Comma-separated ticker symbols"),
    tickers_list: Optional[List[str]] = Query(None, description="List of ticker symbols"),
    timeframe: str = Query("1y", description="Time range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
    interval: str = Query("1d", description="Interval: 1d, 1wk, 1mo")
):
    """
    Get stock prices with time series data.
    Returns structured response with {ok: true, data: {...}} pattern.
    Implements never-empty with fallback to empty arrays if no data available.
    """
    try:
        # Parse tickers from either single or multi parameter
        tickers_to_process = []
        if ticker:
            tickers_to_process = [ticker.upper()]
        elif tickers_list:
            tickers_to_process = [t.strip().upper() for t in tickers_list if t.strip()]
        elif tickers:
            tickers_to_process = [t.strip().upper() for t in tickers.split(',') if t.strip()]
        else:
            # Return empty response if no tickers specified
            return ok({
                "prices": {},
                "requested_tickers": [],
                "count": 0,
                "timeframe": timeframe,
                "interval": interval,
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback_no_tickers"],
                "freshness": datetime.utcnow().isoformat()
            })
        
        # Load stocks data
        stocks_data = load_json("stocks/prices") or load_json("stocks_prices") or load_json("stocks") or {}
        
        # Extract prices for requested tickers
        prices_result = {}
        processed_count = 0
        
        if "tickers" in stocks_data:
            all_prices = stocks_data["tickers"]
        elif "data" in stocks_data and "tickers" in stocks_data["data"]:
            all_prices = stocks_data["data"]["tickers"]
        elif isinstance(stocks_data, dict) and any(ticker.upper() in stocks_data for ticker in tickers_to_process):
            all_prices = stocks_data  # Direct ticker structure
        else:
            all_prices = {}
        
        for ticker_symbol in tickers_to_process:
            if ticker_symbol in all_prices:
                ticker_data = all_prices[ticker_symbol]
                # Apply timeframe and interval filters if the data supports it
                if isinstance(ticker_data, dict):
                    points = ticker_data.get("points", [])
                    
                    # Filter points by timeframe if available
                    if timeframe != "max" and points:
                        # This is a simplified approach - in reality would need to filter by date
                        if timeframe == "1d":
                            points = points[-2:] if len(points) >= 2 else points  # Last 2 points for daily
                        elif timeframe == "5d":
                            points = points[-6:] if len(points) >= 6 else points  # Last 6 points
                        elif timeframe == "1mo":
                            points = points[-20:] if len(points) >= 20 else points  # Approx last month
                        elif timeframe == "3mo":
                            points = points[-60:] if len(points) >= 60 else points  # Approx last 3 months
                        elif timeframe == "1y":
                            points = points[-252:] if len(points) >= 252 else points  # Approx last year
                    
                    prices_result[ticker_symbol] = {
                        "ticker": ticker_symbol,
                        "points": points,
                        "count": len(points),
                        "last_price": points[-1]["close"] if points and "close" in points[-1] else None,
                        "last_date": points[-1]["date"] if points and "date" in points[-1] else None
                    }
                    processed_count += 1
            else:
                # Return empty structure for ticker not found
                prices_result[ticker_symbol] = {
                    "ticker": ticker_symbol,
                    "points": [],
                    "count": 0,
                    "last_price": None,
                    "last_date": None,
                    "note": f"No price data available for {ticker_symbol}"
                }
        
        return ok({
            "prices": prices_result,
            "requested_tickers": tickers_to_process,
            "count": processed_count,
            "timeframe": timeframe,
            "interval": interval,
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["stocks_prices_data"],
            "freshness": stocks_data.get("generated_at") or datetime.utcnow().isoformat(),
            "last_update": stocks_data.get("last_update") or datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in get_stocks_prices: {e}", exc_info=True)
        return ok({
            "prices": {},
            "requested_tickers": [ticker] if ticker else (tickers.split(",") if tickers else []),
            "count": 0,
            "timeframe": timeframe,
            "interval": interval,
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback"],
            "freshness": datetime.utcnow().isoformat(),
            "last_update": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Stock prices temporarily unavailable, returning empty response per never-empty pattern"
        })


# Make router available for import
stocks_router = router
