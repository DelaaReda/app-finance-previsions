"""
Correlation Calculator Service
Calculates correlation matrices between stock price movements for heatmaps
Task: FC-API-027 - ALEX-FINANCE-ANALYST-SUPERMAN-29
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

class CorrelationCalculator:
    """
    Service to calculate correlation matrices between stock price movements
    """
    
    def __init__(self):
        # Use the shared data directory
        self.data_dir = Path(__file__).parents[3] / "data" / "stocks"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def calculate_correlation_matrix(
        self, 
        tickers: List[str], 
        window: str = "30d",
        price_data: Optional[Dict[str, List[Dict]]] = None
    ) -> Dict[str, any]:
        """
        Calculate correlation matrix between specified tickers over a given window
        
        Args:
            tickers: List of stock tickers to calculate correlations for
            window: Time window ('7d', '30d', '90d', '1y')
            price_data: Optional pre-loaded price data (for efficiency)
        
        Returns:
            Dictionary containing correlation matrix and metadata
        """
        try:
            # Parse the window to get days
            days = self._parse_window_to_days(window)
            
            # Get price data for the specified tickers and time window
            if not price_data:
                price_data = self._load_price_data(tickers, days)
            
            if not price_data:
                # Return empty correlation matrix with metadata
                return {
                    "matrix": {},
                    "tickers": tickers,
                    "rows": [],
                    "columns": [],
                    "window": window,
                    "start_date": datetime.now() - timedelta(days=days),
                    "end_date": datetime.now(),
                    "generated_at": datetime.now().isoformat(),
                    "message": "No price data available - correlation matrix empty",
                    "source": ["correlation_calculator", "fallback_empty"]
                }
            
            # Calculate returns for each ticker
            returns_data = {}
            for ticker in tickers:
                ticker_prices = price_data.get(ticker, [])
                if len(ticker_prices) > 1:
                    # Calculate daily returns
                    closes = [float(point.get('close', point.get('adjusted_close', point.get('price', 0)))) for point in ticker_prices if point.get('close') or point.get('adjusted_close') or point.get('price')]
                    if len(closes) > 1:
                        returns = np.diff(np.log(closes))  # Log returns
                        returns_data[ticker] = returns
            
            if len(returns_data) < 2:
                # Need at least 2 symbols to calculate correlation
                return {
                    "matrix": {},
                    "tickers": tickers,
                    "rows": tickers[:1] if tickers else [],
                    "columns": tickers[:1] if tickers else [],
                    "window": window,
                    "start_date": (datetime.now() - timedelta(days=days)).isoformat(),
                    "end_date": datetime.now().isoformat(),
                    "generated_at": datetime.now().isoformat(),
                    "message": "Insufficient price data for correlation analysis - need at least 2 symbols with price history",
                    "source": ["correlation_calculator", "insufficient_data"]
                }
            
            # Create a DataFrame with all returns
            # Align all series to the same dates
            all_dates = set()
            for ticker, returns in returns_data.items():
                # We need to know the dates associated with returns - assume they're sequential
                # For now, we'll use the returns array directly
                pass  # We'll work with aligned arrays directly
            
            # Create correlation matrix
            aligned_returns = []
            aligned_tickers = []
            
            # Find the shortest series length to align all
            min_length = min(len(returns) for returns in returns_data.values()) if returns_data else 0
            
            for ticker, returns in returns_data.items():
                if len(returns) >= min_length:
                    aligned_returns.append(returns[:min_length])
                    aligned_tickers.append(ticker)
            
            if len(aligned_returns) < 2:
                return {
                    "matrix": {},
                    "tickers": tickers,
                    "rows": aligned_tickers,
                    "columns": aligned_tickers,
                    "window": window,
                    "start_date": (datetime.now() - timedelta(days=days)).isoformat(),
                    "end_date": datetime.now().isoformat(),
                    "generated_at": datetime.now().isoformat(),
                    "message": "Insufficient aligned data for correlation calculation",
                    "source": ["correlation_calculator", "alignment_issue"]
                }
            
            # Convert to numpy array and calculate correlation matrix
            returns_array = np.array(aligned_returns)
            correlation_matrix = np.corrcoef(returns_array)
            
            # Format as a dictionary with ticker pairs as keys
            correlation_dict = {}
            for i, row_ticker in enumerate(aligned_tickers):
                for j, col_ticker in enumerate(aligned_tickers):
                    pair_key = f"{row_ticker}-{col_ticker}"
                    correlation_dict[pair_key] = float(correlation_matrix[i][j])
            
            # Also create a matrix format for Tremor heatmaps
            matrix_format = []
            for i, row_ticker in enumerate(aligned_tickers):
                row = {"symbol": row_ticker}
                for j, col_ticker in enumerate(aligned_tickers):
                    row[col_ticker] = float(correlation_matrix[i][j])
                matrix_format.append(row)
            
            return {
                "matrix": correlation_dict,
                "matrix_table": matrix_format,  # For Tremor Heatmap
                "tickers": aligned_tickers,
                "rows": aligned_tickers,
                "columns": aligned_tickers,
                "window": window,
                "start_date": (datetime.now() - timedelta(days=days)).isoformat(),
                "end_date": datetime.now().isoformat(),
                "generated_at": datetime.now().isoformat(),
                "source": ["correlation_calculator", "price_returns_analysis", "pearson_correlation"],
                "stats": {
                    "symbols_count": len(aligned_tickers),
                    "data_points_per_symbol": min_length,
                    "correlation_range": {
                        "min": float(np.min(correlation_matrix)),
                        "max": float(np.max(correlation_matrix)),
                        "avg": float(np.mean(correlation_matrix))
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {str(e)}", exc_info=True)
            return {
                "matrix": {},
                "tickers": tickers,
                "rows": [],
                "columns": [],
                "window": window,
                "error": str(e),
                "generated_at": datetime.now().isoformat(),
                "message": "Error calculating correlation matrix - returning fallback data",
                "source": ["correlation_calculator", "error_handling"]
            }
    
    def _parse_window_to_days(self, window: str) -> int:
        """
        Parse window string to number of days
        
        Args:
            window: Window string like '7d', '30d', '90d', '1y'
        
        Returns:
            Number of days as integer
        """
        if window.endswith('d'):
            return int(window[:-1])
        elif window.endswith('y'):
            return int(window[:-1]) * 365
        elif window.endswith('mo'):
            return int(window[:-2]) * 30
        elif window.endswith('w'):
            return int(window[:-1]) * 7
        else:
            # Default to 30 days if format not recognized
            return 30
    
    def _load_price_data(self, tickers: List[str], days: int) -> Dict[str, List[Dict]]:
        """
        Load price data for specified tickers and time window
        
        Args:
            tickers: List of tickers to load data for
            days: Number of days of history to load
        
        Returns:
            Dictionary with ticker as key and list of price data points as value
        """
        price_data = {}
        
        try:
            from backend.storage.io import load_json
            
            # Try to load price data for each ticker
            for ticker in tickers:
                try:
                    # Load stock price data (this would come from the stock service/data)
                    stock_data = load_json(f"stocks/{ticker}_prices")
                    if stock_data:
                        # Get the price history (could be in 'data', 'history', or 'rows')
                        price_history = stock_data.get("data", {}).get("history", []) or \
                                       stock_data.get("history", []) or \
                                       stock_data.get("data", {}).get("rows", []) or \
                                       stock_data.get("rows", [])
                        
                        # Filter to only the requested time window
                        cutoff_date = datetime.now() - timedelta(days=days)
                        filtered_data = []
                        
                        for point in price_history:
                            date_str = point.get("date") or point.get("timestamp") or point.get("datetime")
                            if date_str:
                                try:
                                    # Parse the date string
                                    if isinstance(date_str, str) and 'T' in date_str:
                                        pt_date = datetime.fromisoformat(date_str.split('T')[0])
                                    elif isinstance(date_str, str):
                                        pt_date = datetime.fromisoformat(date_str)
                                    else:
                                        continue
                                    
                                    if pt_date >= cutoff_date:
                                        filtered_data.append(point)
                                except ValueError:
                                    # If we can't parse the date, include it anyway
                                    filtered_data.append(point)
                        
                        price_data[ticker] = filtered_data
                    else:
                        # If no data exists, we'll have an empty list for this ticker
                        price_data[ticker] = []
                        
                except Exception as e:
                    logger.warning(f"Could not load price data for {ticker}: {str(e)}")
                    price_data[ticker] = []  # Empty list as fallback
        
        except ImportError:
            logger.warning("Could not import storage.io, using empty price data")
            # If storage module is not available, return empty data per ticker
            for ticker in tickers:
                price_data[ticker] = []
        
        return price_data


# Global instance for use in routes
correlation_calculator = CorrelationCalculator()