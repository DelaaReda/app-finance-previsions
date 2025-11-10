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


@router.get("/stocks/screener")
def stocks_screener(
    universe: Optional[str] = Query(None, description="Comma-separated universe tickers"),
    sectors: Optional[str] = Query(None, description="Comma-separated sectors"),
    q: Optional[str] = Query(None, description="Text search"),
    min_mcap: Optional[float] = Query(None),
    max_mcap: Optional[float] = Query(None),
    min_pe: Optional[float] = Query(None),
    max_pe: Optional[float] = Query(None),
    sort: str = Query("score", description="Sort field: score, risk, momentum_30d, change_1d, mcap, pe, div_yield"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=200, description="Page size"),
) -> Dict[str, Any]:
    """
    Get stocks screener with advanced filtering.
    
    Reads from pre-computed stocks metrics or computes on the fly.
    
    Returns:
        Paginated list of stocks with metrics (score, risk, quality, etc.)
    """
    try:
        # Default universe
        DEFAULT_STOCKS_UNIVERSE = [
            "SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "IBM"
        ]
        
        def _parse_csv_list(value: Optional[str]) -> List[str]:
            """Parse comma-separated string into list."""
            if not value:
                return []
            return [t.strip().upper() for t in value.split(",") if t.strip()]
        
        # Load from pre-computed stocks metrics
        metrics_data = load_json("stocks/metrics")
        
        if metrics_data and "metrics" in metrics_data:
            tickers = _parse_csv_list(universe) or DEFAULT_STOCKS_UNIVERSE
            sector_filters = {s.lower() for s in _parse_csv_list(sectors)}
            metrics = metrics_data.get("metrics", {})
            
            # Convert metrics to rows format
            rows = []
            for ticker in tickers:
                if ticker.upper() in metrics:
                    metric = metrics[ticker.upper()]
                    rows.append({
                        "ticker": metric.get("ticker", ticker.upper()),
                        "name": metric.get("name"),
                        "sector": metric.get("sector"),
                        "price": metric.get("price"),
                        "change_1d": metric.get("change_1d"),
                        "momentum_30d": metric.get("momentum_30d"),
                        "score": metric.get("score"),
                        "risk": metric.get("risk"),
                        "quality": metric.get("quality"),
                        "mcap": metric.get("mcap"),
                        "pe": metric.get("pe"),
                        "div_yield": metric.get("div_yield"),
                    })
        else:
            # Fallback: return empty with metadata
            tickers = _parse_csv_list(universe) or DEFAULT_STOCKS_UNIVERSE
            sector_filters = {s.lower() for s in _parse_csv_list(sectors)}
            rows = []  # Empty fallback - data will be computed by jobs
        
        def _match_sector(row):
            if not sector_filters:
                return True
            sector = (row.get("sector") or "").lower()
            return sector in sector_filters
        
        # Apply filters
        filtered = []
        query_lower = q.lower() if q else None
        for row in rows:
            if query_lower:
                if query_lower not in row["ticker"].lower() and query_lower not in (row.get("name") or "").lower():
                    continue
            if not _match_sector(row):
                continue
            mcap = row.get("mcap")
            if min_mcap is not None and (mcap is None or mcap < min_mcap):
                continue
            if max_mcap is not None and (mcap is None or mcap > max_mcap):
                continue
            pe_val = row.get("pe")
            if min_pe is not None and (pe_val is None or pe_val < min_pe):
                continue
            if max_pe is not None and (pe_val is None or pe_val > max_pe):
                continue
            filtered.append(row)
        
        # Sort
        sort_field = sort if sort in {"score", "risk", "momentum_30d", "change_1d", "mcap", "pe", "div_yield"} else "score"
        reverse = (order or "desc").lower() != "asc"
        
        def sort_key(item: Dict[str, Any]):
            value = item.get(sort_field)
            return (value is None, value)
        
        filtered.sort(key=sort_key, reverse=reverse)
        
        # Paginate
        total = len(filtered)
        start = (page - 1) * page_size
        sliced = filtered[start:start + page_size]
        
        # Ensure fields subset
        fields = ["ticker", "name", "sector", "price", "change_1d", "momentum_30d", "score", "risk", "quality", "mcap", "pe", "div_yield"]
        items = [{field: row.get(field) for field in fields} for row in sliced]
        
        # Get freshness from metrics_data if available
        updated_at = metrics_data.get("freshness", datetime.utcnow().isoformat()) if metrics_data else datetime.utcnow().isoformat()
        
        return ok({
            "updated_at": updated_at,
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        })
        
    except Exception as e:
        logger.error(f"Error in stocks screener: {str(e)}", exc_info=True)
        return ok({
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "total": 0,
            "page": page,
            "page_size": page_size,
            "items": [],
            "error": str(e),
        })


@router.get("/stocks/{ticker}/sheet")
def get_stock_sheet(ticker: str) -> Dict[str, Any]:
    """
    Get detailed stock sheet data for a specific ticker.
    
    Returns comprehensive stock information including:
    - Current price and metrics
    - Historical data
    - Financials
    - Technical indicators
    - Analyst ratings
    
    Args:
        ticker: Stock ticker symbol (e.g., SPY, AAPL)
    
    Returns:
        Stock sheet data with all available information
    """
    try:
        ticker_upper = ticker.upper()
        
        # Try to load from stored prices
        prices_data = load_json("stocks_prices") or {}
        ticker_data = prices_data.get("data", {}).get("tickers", {}).get(ticker_upper, {})
        
        # Try to load from stored metrics
        metrics_data = load_json("stocks/metrics") or {}
        metrics = metrics_data.get("metrics", {}).get(ticker_upper, {})
        
        # Build comprehensive sheet data
        sheet_data = {
            "ticker": ticker_upper,
            "name": metrics.get("name") or ticker_data.get("name") or f"{ticker_upper} Corp",
            "sector": metrics.get("sector") or ticker_data.get("sector") or "N/A",
            "price": {
                "current": metrics.get("price") or (ticker_data.get("points", [{}])[-1].get("value") if ticker_data.get("points") else 0.0),
                "change_1d": metrics.get("change_1d", 0.0),
                "change_percent": metrics.get("change_percent", 0.0)
            },
            "metrics": {
                "score": metrics.get("score"),
                "risk": metrics.get("risk"),
                "quality": metrics.get("quality"),
                "momentum_30d": metrics.get("momentum_30d"),
                "mcap": metrics.get("mcap"),
                "pe": metrics.get("pe"),
                "div_yield": metrics.get("div_yield")
            },
            "historical": {
                "points": ticker_data.get("points", [])[-30:] if ticker_data.get("points") else []  # Last 30 points
            },
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["stocks_prices", "stocks_metrics", "sheet_endpoint"]
        }
        
        # Try to enrich with yfinance if available
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker_upper)
            info = stock.info
            
            if info:
                sheet_data["info"] = {
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "dividend_yield": info.get("dividendYield"),
                    "52_week_high": info.get("fiftyTwoWeekHigh"),
                    "52_week_low": info.get("fiftyTwoWeekLow"),
                    "volume": info.get("volume"),
                    "avg_volume": info.get("averageVolume")
                }
                sheet_data["source"].append("yfinance")
        except Exception as e:
            logger.debug(f"Could not enrich with yfinance for {ticker_upper}: {e}")
        
        return ok(sheet_data)
        
    except Exception as e:
        logger.error(f"Error getting stock sheet for {ticker}: {str(e)}", exc_info=True)
        return ok({
            "ticker": ticker.upper(),
            "name": f"{ticker.upper()} Corp",
            "sector": "N/A",
            "price": {"current": 0.0, "change_1d": 0.0, "change_percent": 0.0},
            "metrics": {},
            "historical": {"points": []},
            "error": str(e),
            "message": "Stock sheet temporarily unavailable",
            "generated_at": datetime.utcnow().isoformat()
        })


# Export router with expected name for main.py registration
stocks_router = router

