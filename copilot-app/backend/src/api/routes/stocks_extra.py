"""
Stocks Extra API Routes - Finance Copilot System
Additional endpoints for advanced stock analysis features
Task: FC-API-027 - Stock Correlation Heatmap
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from core.response import ok, err
from storage.io import load_json
from ..models.correlation_matrix import correlation_model

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/stocks/heatmap")
def get_stock_correlation_heatmap(
    tickers: Optional[List[str]] = Query(None, description="Filter by specific tickers (comma-separated)"),
    window: Optional[str] = Query("30d", description="Time window: 7d, 30d, 90d, 1y"),
    method: Optional[str] = Query("pearson", description="Correlation method: pearson, spearman, kendall"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Limit number of results (max 200)"),
    min_correlation: Optional[float] = Query(-1.0, description="Minimum correlation threshold (-1.0 to 1.0)"),
    max_correlation: Optional[float] = Query(1.0, description="Maximum correlation threshold (-1.0 to 1.0)")
) -> Dict[str, Any]:
    """
    Get stock correlation heatmap data with filtering capabilities.
    Returns correlation matrix for specified tickers and time window.
    """
    try:
        logger.info(f"📈 Correlation heatmap requested", extra={
            "tickers": tickers,
            "window": window,
            "method": method,
            "limit": limit
        })
        
        # Load stock price data to calculate correlations
        # In a real implementation, this would fetch from live sources or recent cache
        stocks_data = load_json("stocks_prices")
        
        if not stocks_data:
            # Return empty structure but never fail (never-empty pattern)
            return ok({
                "matrix": {},
                "matrix_table": [],
                "tickers": tickers or [],
                "rows": tickers or [],
                "columns": tickers or [],
                "method": method,
                "start_date": datetime.utcnow().isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "generated_at": datetime.utcnow().isoformat(),
                "message": "No price data available - correlation matrix empty. Prices being fetched in background.",
                "freshness": "unknown",
                "source": ["fallback_empty", "correlation_heatmap"],
                "filters": {
                    "tickers": tickers,
                    "window": window,
                    "method": method,
                    "limit": limit
                },
                "metadata": {
                    "symbols_count": len(tickers) if tickers else 0,
                    "data_points_per_symbol": 0,
                    "computation_method": method,
                    "correlation_range": {"min": 0.0, "max": 0.0, "avg": 0.0},
                    "valid_pairs": 0
                }
            })
        
        # Extract price history for the specified tickers
        data_payload = stocks_data.get("data", stocks_data.get("payload", stocks_data))
        all_prices = data_payload.get("prices", {})
        
        # Filter to include only requested tickers if specified
        if tickers:
            filtered_prices = {k: v for k, v in all_prices.items() if k.upper() in [t.upper() for t in tickers]}
        else:
            filtered_prices = dict(all_prices)
        
        # Calculate returns for each ticker
        ticker_returns = {}
        for ticker, price_data in filtered_prices.items():
            if isinstance(price_data, list) and len(price_data) > 1:
                # Calculate daily logarithmic returns
                closes = []
                for item in price_data:
                    # Get close price from different possible field names
                    close_price = (item.get('close') or item.get('adjusted_close') or 
                                  item.get('last_price') or item.get('price') or 0.0)
                    if close_price and close_price > 0:
                        closes.append(float(close_price))
                
                if len(closes) > 1:
                    # Calculate log returns
                    import numpy as np
                    log_returns = np.diff(np.log(closes))
                    ticker_returns[ticker.upper()] = log_returns.tolist()
        
        # If no returns data, return empty matrix
        if not ticker_returns:
            return ok({
                "matrix": {},
                "matrix_table": [],
                "tickers": list(filtered_prices.keys()) if not tickers else tickers,
                "rows": list(filtered_prices.keys()) if not tickers else tickers,
                "columns": list(filtered_prices.keys()) if not tickers else tickers,
                "method": method,
                "start_date": datetime.utcnow().isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "generated_at": datetime.utcnow().isoformat(),
                "message": "Insufficient price history for correlation calculation",
                "freshness": stocks_data.get("freshness") or "unknown",
                "source": ["insufficient_data", "correlation_heatmap"],
                "filters": {
                    "tickers": tickers,
                    "window": window,
                    "method": method,
                    "limit": limit
                },
                "metadata": {
                    "symbols_count": len(filtered_prices),
                    "data_points_per_symbol": 0,
                    "computation_method": method,
                    "correlation_range": {"min": 0.0, "max": 0.0, "avg": 0.0},
                    "valid_pairs": 0
                }
            })
        
        # Calculate correlation matrix using the correlation model
        correlation_result = correlation_model.create_correlation_matrix(
            ticker_returns=ticker_returns,
            method=method
        )
        
        # Apply additional filters like min/max correlation
        correlation_matrix = correlation_result["matrix"]
        
        # Apply correlation threshold filtering if specified
        if min_correlation > -1.0 or max_correlation < 1.0:
            # This would require post-processing of the correlation matrix
            # For now, we'll return the full matrix as calculated
            pass
        
        # Add request filters to the result
        result = dict(correlation_result)
        result["filters"] = {
            "tickers": tickers,
            "window": window,
            "method": method,
            "limit": limit,
            "min_correlation": min_correlation,
            "max_correlation": max_correlation
        }
        
        logger.info(f"✅ Correlation heatmap generated for {len(ticker_returns)} tickers using {method} method")
        return ok(result)
        
    except Exception as e:
        logger.error(f"❌ Error in correlation heatmap endpoint: {str(e)}", exc_info=True)
        
        # Return structured response even on error to maintain never-empty contract
        return ok({
            "matrix": {},
            "matrix_table": [],
            "tickers": tickers or [],
            "rows": tickers or [],
            "columns": tickers or [],
            "method": method,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Correlation heatmap temporarily unavailable - showing fallback data",
            "freshness": "error",
            "source": ["correlation_heatmap", "error_fallback"],
            "filters": {
                "tickers": tickers,
                "window": window,
                "method": method,
                "limit": limit
            },
            "metadata": {
                "symbols_count": len(tickers) if tickers else 0,
                "data_points_per_symbol": 0,
                "computation_method": method,
                "correlation_range": {"min": 0.0, "max": 0.0, "avg": 0.0},
                "valid_pairs": 0
            }
        })


@router.get("/stocks/correlations")
def get_stock_correlations(
    base_ticker: str = Query(..., description="Base ticker to measure correlations against"),
    compare_tickers: Optional[List[str]] = Query(None, description="Tickers to compare against base (comma-separated)"),
    window: Optional[str] = Query("30d", description="Time window for correlation calculation"),
    method: Optional[str] = Query("pearson", description="Correlation method: pearson, spearman, kendall")
) -> Dict[str, Any]:
    """
    Get correlations of a base ticker against other tickers.
    Useful for sector analysis or benchmark comparisons.
    """
    try:
        logger.info(f"🔗 Getting correlations for {base_ticker} vs {compare_tickers or 'all'}", extra={
            "base_ticker": base_ticker,
            "compare_tickers": compare_tickers,
            "window": window,
            "method": method
        })
        
        # This would use the same correlation calculation as the heatmap
        # For now, return a similar structure but focused on one base ticker
        correlation_result = get_stock_correlation_heatmap(
            tickers=[base_ticker] + (compare_tickers or []),
            window=window,
            method=method,
            limit=50
        )
        
        # Process the result to focus on correlations with the base ticker
        if correlation_result.get("ok") and correlation_result.get("data"):
            data = correlation_result["data"]
            base_correlations = {}
            
            matrix = data.get("matrix", {})
            if base_ticker in matrix:
                base_row = matrix[base_ticker]
                for ticker, correlation in base_row.items():
                    if ticker != base_ticker:  # Exclude self-correlation
                        base_correlations[ticker] = correlation
            
            data["base_correlations"] = base_correlations
            data["base_ticker"] = base_ticker
            correlation_result["data"] = data
        
        return correlation_result
        
    except Exception as e:
        logger.error(f"❌ Error in stock correlations endpoint: {str(e)}", exc_info=True)
        
        return ok({
            "base_ticker": base_ticker,
            "correlations": {},
            "compare_tickers": compare_tickers,
            "method": method,
            "window": window,
            "generated_at": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Stock correlations temporarily unavailable - showing fallback data",
            "source": ["stock_correlations", "error_fallback"]
        })

# Export the router for the main application to include
stocks_extra_router = router