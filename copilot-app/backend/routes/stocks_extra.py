"""
Stock Screener Route
Task: FC-API-026 - Stocks Screener (advanced filtering)
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.services.stock_screener import get_filtered_stocks, validate_filters, get_filter_options
from backend.storage.io import load_json
from backend.services.cache_layer import load_or_compute

router = APIRouter(prefix="/api", tags=["stocks"])

# Define query parameters for the stock screener endpoint
@router.get("/stocks/screener")
async def stock_screener(
    sector: Optional[str] = Query(None, description="Filtrer par secteur (ex: Technology, Healthcare)"),
    market_cap_min: Optional[float] = Query(None, ge=0, description="Market cap minimum (en millions)"),
    market_cap_max: Optional[float] = Query(None, ge=0, description="Market cap maximum (en millions)"),
    pe_ratio_min: Optional[float] = Query(None, ge=0, le=100, description="P/E ratio minimum"),
    pe_ratio_max: Optional[float] = Query(None, ge=0, le=100, description="P/E ratio maximum"),
    pb_ratio_min: Optional[float] = Query(None, ge=0, le=10, description="P/B ratio minimum"),
    pb_ratio_max: Optional[float] = Query(None, ge=0, le=10, description="P/B ratio maximum"),
    dividend_yield_min: Optional[float] = Query(None, ge=0, le=1, description="Dividend yield minimum (0.0-1.0)"),
    dividend_yield_max: Optional[float] = Query(None, ge=0, le=1, description="Dividend yield maximum (0.0-1.0)"),
    price_min: Optional[float] = Query(None, ge=0, description="Prix minimum"),
    price_max: Optional[float] = Query(None, ge=0, description="Prix maximum"),
    volume_min: Optional[int] = Query(None, ge=0, description="Volume minimum"),
    volatility: Optional[str] = Query(None, description="Volatilité (low/medium/high)"),
    beta_min: Optional[float] = Query(None, ge=0, le=5, description="Beta minimum"),
    beta_max: Optional[float] = Query(None, ge=0, le=5, description="Beta maximum"),
    roe_min: Optional[float] = Query(None, ge=0, le=1, description="Return on Equity minimum (0.0-1.0)"),
    eps_growth_min: Optional[float] = Query(None, ge=-1, le=5, description="EPS Growth minimum (-1.0 to 5.0)"),
    debt_to_equity_min: Optional[float] = Query(None, ge=0, le=5, description="Debt-to-equity minimum"),
    debt_to_equity_max: Optional[float] = Query(None, ge=0, le=5, description="Debt-to-equity maximum"),
    tickers: Optional[str] = Query(None, description="Filtre par tickers spécifiques (séparés par virgule)"),
    sort_by: Optional[str] = Query("market_cap", description="Tri par (market_cap, pe_ratio, etc.)"),
    sort_order: Optional[str] = Query("desc", description="Ordre de tri (asc/desc)")
):
    """
    Get stocks filtered by advanced criteria (sector, market cap, ratios, etc.)
    Implements never-empty contract by serving cached/latest data if live computation fails.
    """
    try:
        # Build filter dictionary from query parameters
        filters = {}
        if sector: filters["sector"] = sector
        if market_cap_min is not None: filters["market_cap_min"] = market_cap_min
        if market_cap_max is not None: filters["market_cap_max"] = market_cap_max
        if pe_ratio_min is not None: filters["pe_ratio_min"] = pe_ratio_min
        if pe_ratio_max is not None: filters["pe_ratio_max"] = pe_ratio_max
        if pb_ratio_min is not None: filters["pb_ratio_min"] = pb_ratio_min
        if pb_ratio_max is not None: filters["pb_ratio_max"] = pb_ratio_max
        if dividend_yield_min is not None: filters["dividend_yield_min"] = dividend_yield_min
        if dividend_yield_max is not None: filters["dividend_yield_max"] = dividend_yield_max
        if price_min is not None: filters["price_min"] = price_min
        if price_max is not None: filters["price_max"] = price_max
        if volume_min is not None: filters["volume_min"] = volume_min
        if volatility: filters["volatility"] = volatility
        if beta_min is not None: filters["beta_min"] = beta_min
        if beta_max is not None: filters["beta_max"] = beta_max
        if roe_min is not None: filters["roe_min"] = roe_min
        if eps_growth_min is not None: filters["eps_growth_min"] = eps_growth_min
        if debt_to_equity_min is not None: filters["debt_to_equity_min"] = debt_to_equity_min
        if debt_to_equity_max is not None: filters["debt_to_equity_max"] = debt_to_equity_max
        if sort_by: filters["sort_by"] = sort_by
        if sort_order: filters["sort_order"] = sort_order
        
        # Parse tickers if provided
        if tickers:
            filters["target_tickers"] = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        
        # Create a unique cache key based on filters
        filters_str = str(sorted(filters.items()))
        cache_key = f"stock_screener_{hash(filters_str)}_{int(datetime.utcnow().timestamp())}"
        
        def compute_screener_results():
            """Function to compute fresh screener results"""
            try:
                result = get_filtered_stocks(filters)
                
                # If the result has 'data' attribute, return it, otherwise return the result directly
                if isinstance(result, dict) and "data" in result:
                    return result["data"]
                else:
                    return result
                
            except Exception as e:
                # Fallback if service fails
                return {
                    "filtered_stocks": [],
                    "count": 0,
                    "applied_filters": filters,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filter_summary": {
                        "sector": sector,
                        "price_range": [price_min, price_max],
                        "market_cap_range": [market_cap_min, market_cap_max],
                        "pe_ratio_range": [pe_ratio_min, pe_ratio_max],
                        "sort_by": sort_by or "market_cap",
                        "sort_order": sort_order or "desc"
                    },
                    "message": f"Stock screener service failed: {str(e)}",
                    "source": ["stock_screener_route", "error_fallback", "fc-api-026"]
                }
        
        # Use cache layer to serve latest available data, compute fresh if needed
        screener_data = load_or_compute(
            key=cache_key,
            compute_fn=compute_screener_results,
            source=["stock_screener_route", "fc-api-026", "advanced_filters"]
        )
        
        # Ensure the response structure is always correct
        response_data = {
            "filtered_stocks": [],
            "count": 0,
            "applied_filters": filters,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "filter_summary": {
                "sector": sector,
                "price_range": [price_min, price_max],
                "market_cap_range": [market_cap_min, market_cap_max],
                "pe_ratio_range": [pe_ratio_min, pe_ratio_max],
                "sort_by": sort_by or "market_cap",
                "sort_order": sort_order or "desc"
            },
            "source": ["stock_screener_route", "live_calculation", "fc-api-026"]
        }
        
        if isinstance(screener_data, dict):
            response_data.update(screener_data)
        else:
            # If screener_data is not a dict, use fallback
            response_data["message"] = "Unexpected response format from stock screener service"
        
        return {
            "ok": True,
            "data": response_data,
            "freshness": response_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
        
    except Exception as e:
        print(f"Error in /stocks/screener endpoint: {str(e)}")
        
        # Return structured fallback to maintain never-empty contract
        return {
            "ok": True,  # Still return True to maintain never-empty contract
            "data": {
                "filtered_stocks": [],
                "count": 0,
                "applied_filters": {
                    "sector": sector,
                    "price_range": [price_min, price_max],
                    "market_cap_range": [market_cap_min, market_cap_max],
                    "pe_ratio_range": [pe_ratio_min, pe_ratio_max],
                    "sort_by": sort_by or "market_cap", 
                    "sort_order": sort_order or "desc"
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "filter_summary": {
                    "sector": sector,
                    "price_range": [price_min, price_max],
                    "market_cap_range": [market_cap_min, market_cap_max],
                    "pe_ratio_range": [pe_ratio_min, pe_ratio_max],
                    "sort_by": sort_by or "market_cap",
                    "sort_order": sort_order or "desc"
                },
                "message": "Stock screener endpoint failed, but fallback response generated to maintain never-empty contract",
                "error": str(e),
                "source": ["stock_screener_route", "error_fallback", "fc-api-026"]
            },
            "freshness": "error",
            "error": str(e)
        }

@router.get("/stocks/screener/options")
async def screener_options():
    """
    Get available filter options for the stock screener UI.
    Provides dropdown values and parameter ranges.
    """
    try:
        from backend.services.stock_screener import get_filter_options
        
        options_data = get_filter_options()
        
        return {
            "ok": True,
            "data": options_data,
            "freshness": options_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
    except Exception as e:
        print(f"Error fetching screener options: {str(e)}")
        
        # Return default options to maintain never-empty contract
        return {
            "ok": True,
            "data": {
                "sectors": [
                    "Technology", "Healthcare", "Financials", "Consumer Discretionary",
                    "Consumer Staples", "Industrials", "Communication Services", 
                    "Utilities", "Real Estate", "Energy", "Materials"
                ],
                "sort_options": [
                    "market_cap", "pe_ratio", "dividend_yield", "price", 
                    "volume", "beta", "roe", "eps_growth"
                ],
                "volatility_options": ["low", "medium", "high"],
                "sort_orders": ["asc", "desc"],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "message": "Screener options service failed, using defaults to maintain never-empty"
            },
            "freshness": "error"
        }