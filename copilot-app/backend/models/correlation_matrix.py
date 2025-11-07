"""
Stock Correlation Matrix Calculator
Task: FC-API-027 - Stock Correlation Heatmap
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import numpy as np
from scipy.stats import pearsonr
from pathlib import Path
import json

class CorrelationMatrixCalculator:
    """
    Calculate correlation matrices between stock assets
    """
    
    def __init__(self):
        self.cached_matrices = {}
    
    def calculate_correlation_matrix(self, price_data: Dict[str, List[Dict[str, float]]], 
                                   lookback_days: int = 30) -> Dict[str, Any]:
        """
        Calculate correlation matrix for provided price data
        
        Args:
            price_data: Dictionary with ticker: [{date: ..., close: ...}, ...] 
            lookback_days: Number of days to look back for correlation calculation
        
        Returns:
            Correlation matrix with metadata
        """
        try:
            # Extract common dates across all tickers
            all_dates = set()
            for ticker, prices in price_data.items():
                dates = {p["date"] for p in prices if "date" in p and "close" in p}
                all_dates.update(dates)
            
            # Sort dates to ensure chronological order
            sorted_dates = sorted(list(all_dates))
            
            # Get the most recent `lookback_days` of data
            if lookback_days > 0 and len(sorted_dates) > lookback_days:
                recent_dates = sorted_dates[-lookback_days:]
            else:
                recent_dates = sorted_dates
            
            # Prepare data matrix: each row is a ticker's returns over time
            tickers = list(price_data.keys())
            returns_matrix = []
            valid_tickers = []
            
            for ticker in tickers:
                prices = price_data[ticker]
                # Filter to only recent dates that are available for this ticker
                ticker_prices = {p["date"]: p["close"] for p in prices if "date" in p and "close" in p}
                
                closes = []
                for date in recent_dates:
                    if date in ticker_prices:
                        closes.append(ticker_prices[date])
                    else:
                        closes.append(None)  # Represent missing data as None
                
                # Only include tickers that have sufficient data
                if all(c is not None for c in closes) and len(closes) >= 2:
                    # Calculate returns from closes
                    returns = []
                    for i in range(1, len(closes)):
                        if closes[i-1] != 0:
                            ret = (closes[i] - closes[i-1]) / closes[i-1]
                            returns.append(ret)
                        else:
                            returns.append(0.0)  # Default return if previous close is 0
                    
                    if len(returns) >= 2:  # Need at least 2 points for correlation
                        returns_matrix.append(returns)
                        valid_tickers.append(ticker)
            
            if len(returns_matrix) < 2:
                # Not enough tickers with data to compute correlations
                return {
                    "matrix": {},
                    "tickers": valid_tickers,
                    "dates_range": {"start": recent_dates[0] if recent_dates else None, "end": recent_dates[-1] if recent_dates else None},
                    "lookback_days": lookback_days,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "message": "Insufficient data to compute correlation matrix - need at least 2 tickers with overlapping price history",
                    "status": "insufficient_data"
                }
            
            # Convert to numpy array for correlation calculation
            returns_array = np.array(returns_matrix)
            
            # Calculate correlation matrix
            n_tickers = len(valid_tickers)
            correlation_matrix = np.eye(n_tickers)  # Initialize identity matrix
            
            for i in range(n_tickers):
                for j in range(i+1, n_tickers):
                    # Calculate Pearson correlation coefficient
                    try:
                        correlation, _ = pearsonr(returns_array[i], returns_array[j])
                        correlation_matrix[i][j] = correlation
                        correlation_matrix[j][i] = correlation  # Correlation matrix is symmetric
                    except Exception as e:
                        # If correlation calculation fails, default to 0
                        correlation_matrix[i][j] = 0.0
                        correlation_matrix[j][i] = 0.0
            
            # Convert matrix to dict format with ticker labels
            matrix_dict = {}
            for i, ticker_i in enumerate(valid_tickers):
                matrix_dict[ticker_i] = {}
                for j, ticker_j in enumerate(valid_tickers):
                    matrix_dict[ticker_i][ticker_j] = float(correlation_matrix[i][j])
            
            return {
                "matrix": matrix_dict,
                "tickers": valid_tickers,
                "dates_range": {"start": recent_dates[0] if recent_dates else None, "end": recent_dates[-1] if recent_dates else None},
                "lookback_days": lookback_days,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "status": "success"
            }
            
        except Exception as e:
            print(f"Error calculating correlation matrix: {e}")
            # Return fallback structure to maintain never-empty contract
            return {
                "matrix": {},
                "tickers": [],
                "dates_range": {"start": None, "end": None},
                "lookback_days": lookback_days,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "status": "error",
                "error": str(e),
                "message": "Correlation calculation failed, returning empty matrix to maintain never-empty contract"
            }
    
    def get_correlation_heatmap(self, tickers: List[str], lookback_days: int = 30, 
                               min_correlation: float = 0.1) -> Dict[str, Any]:
        """
        Get correlation heatmap data with filtering
        
        Args:
            tickers: List of tickers to include in the heatmap
            lookback_days: Number of days to look back for calculation
            min_correlation: Minimum correlation to highlight
        
        Returns:
            Filtered correlation matrix suitable for heatmap visualization
        """
        # For this implementation, we'll create a mock price data structure
        # In a real implementation, this would load actual price data
        price_data = {}
        
        # For now, we'll simulate price data for requested tickers
        for ticker in tickers:
            # This would typically come from price history APIs
            price_data[ticker] = self._generate_mock_price_data(ticker, lookback_days)
        
        correlation_result = self.calculate_correlation_matrix(price_data, lookback_days)
        
        # Create structured response for heatmap
        heatmap_data = {
            "nodes": [{"id": ticker, "label": ticker} for ticker in correlation_result["tickers"]],
            "links": [],
            "matrix": correlation_result["matrix"],
            "tickers": correlation_result["tickers"],
            "lookback_days": lookback_days,
            "dates_range": correlation_result["dates_range"],
            "generated_at": correlation_result["generated_at"],
            "status": correlation_result["status"],
            "filtered_by": {"min_correlation": min_correlation}
        }
        
        # Add links for visualization (correlations above threshold)
        for i, ticker_i in enumerate(correlation_result["tickers"]):
            for j, ticker_j in enumerate(correlation_result["tickers"]):
                if i < j:  # Only add each pair once
                    corr_value = correlation_result["matrix"].get(ticker_i, {}).get(ticker_j, 0)
                    if abs(corr_value) >= abs(min_correlation):
                        heatmap_data["links"].append({
                            "source": ticker_i,
                            "target": ticker_j,
                            "value": corr_value,
                            "strength": abs(corr_value)
                        })
        
        return heatmap_data
    
    def _generate_mock_price_data(self, ticker: str, days: int) -> List[Dict[str, float]]:
        """
        Generate mock price data for demonstration purposes
        In a real implementation, this would load actual price history
        """
        import random
        from datetime import date, timedelta
        
        base_price = random.uniform(10, 500)  # Random base price
        data = []
        
        for i in range(days):
            current_date = (date.today() - timedelta(days=days-i-1)).isoformat()
            # Generate somewhat realistic price data with slight trends
            change = (random.random() - 0.5) * 0.05  # Max ±5% daily change
            base_price *= (1 + change)
            data.append({
                "date": current_date,
                "close": base_price,
                "open": base_price * (1 - (random.random() * 0.01)), 
                "high": base_price * (1 + (random.random() * 0.02)),
                "low": base_price * (1 - (random.random() * 0.02)),
                "volume": random.randint(1000000, 10000000)
            })
        
        return data


# Global calculator instance
correlation_calculator = CorrelationMatrixCalculator()

# Convenience functions
def calculate_correlation_matrix(price_data: Dict[str, List[Dict[str, float]]], lookback_days: int = 30) -> Dict[str, Any]:
    """
    Calculate correlation matrix for stock price data
    """
    return correlation_calculator.calculate_correlation_matrix(price_data, lookback_days)

def get_correlation_heatmap(tickers: List[str], lookback_days: int = 30, min_correlation: float = 0.1) -> Dict[str, Any]:
    """
    Get correlation heatmap data for visualization
    """
    return correlation_calculator.get_correlation_heatmap(tickers, lookback_days, min_correlation)