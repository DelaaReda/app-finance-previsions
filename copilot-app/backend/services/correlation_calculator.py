"""
Stock Correlation Calculator Service
Task: FC-API-027 - Stock Correlation Heatmap
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from models.correlation_matrix import correlation_calculator, get_correlation_heatmap
from storage.io import load_json
from services.cache_layer import load_or_compute


class StockCorrelationService:
    """
    Service for calculating and managing stock correlation heatmaps
    """
    
    def __init__(self):
        self.calculator = correlation_calculator
    
    def get_correlation_heatmap_data(self, 
                                   tickers: Optional[List[str]] = None, 
                                   lookback_days: int = 30,
                                   min_correlation: float = 0.1) -> Dict[str, Any]:
        """
        Get correlation heatmap data with caching and fallback
        """
        def compute_heatmap():
            """Compute fresh correlation heatmap from stored data"""
            try:
                # Load price data for tickers (or use all available if none specified)
                price_data = self._load_price_data(tickers, lookback_days)
                
                if not price_data:
                    # If no price data available, use a fallback
                    all_tickers = self._get_all_available_tickers()
                    price_data = self._load_price_data(all_tickers[:5] if all_tickers else ["SPY", "QQQ"], lookback_days)
                
                # Calculate correlation heatmap
                result = self.calculator.get_correlation_heatmap(
                    tickers=list(price_data.keys()) if price_data else (tickers or ["SPY", "QQQ"]),
                    lookback_days=lookback_days,
                    min_correlation=min_correlation
                )
                
                return result
            except Exception as e:
                print(f"Error computing correlation heatmap: {e}")
                
                # Return fallback structure to maintain never-empty contract
                return {
                    "nodes": [],
                    "links": [],
                    "matrix": {},
                    "tickers": tickers or [],
                    "lookback_days": lookback_days,
                    "dates_range": {"start": None, "end": None},
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "status": "error",
                    "error": str(e),
                    "message": "Correlation heatmap calculation failed, returning empty data to maintain never-empty contract"
                }
        
        # Use cache layer to serve latest available data, compute fresh if needed
        cache_key = f"correlation_heatmap_{hash(str(tickers))}_{lookback_days}d_{min_correlation}"
        heatmap_data = load_or_compute(
            key=cache_key,
            compute_fn=compute_heatmap,
            source=["correlation_service", "heatmap_calculation", "fc-api-027"]
        )
        
        if not isinstance(heatmap_data, dict):
            # If returned data is not a dict, create a proper response
            return {
                "ok": False,
                "data": {
                    "nodes": [],
                    "links": [],
                    "matrix": {},
                    "tickers": tickers or [],
                    "lookback_days": lookback_days,
                    "dates_range": {"start": None, "end": None},
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "status": "error",
                    "error": "Invalid data format returned from correlation calculation",
                    "message": "Correlation heatmap service returned invalid data format"
                }
            }
        
        return {
            "ok": heatmap_data.get("status") != "error",
            "data": heatmap_data,
            "freshness": heatmap_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
    
    def _load_price_data(self, tickers: Optional[List[str]] = None, lookback_days: int = 30) -> Dict[str, List[Dict[str, float]]]:
        """
        Load price data for specified tickers from storage
        """
        price_data = {}
        
        # If no tickers specified, try to get all available tickers
        if not tickers:
            tickers = self._get_all_available_tickers()[:10]  # Limit to 10 if none specified
        
        for ticker in tickers or []:
            try:
                # Load stock prices from stored data
                stock_data = load_json(f"stock_prices_{ticker.lower()}")
                
                if stock_data and "data" in stock_data:
                    # Extract price history
                    if "history" in stock_data["data"]:
                        prices = stock_data["data"]["history"]
                    elif "prices" in stock_data["data"]:
                        prices = stock_data["data"]["prices"]
                    else:
                        prices = stock_data["data"] if isinstance(stock_data["data"], list) else []
                    
                    # Limit to lookback period
                    if lookback_days > 0 and prices:
                        # Sort by date (assuming date field exists)
                        sorted_prices = sorted(prices, key=lambda x: x.get("date", ""), reverse=True)
                        price_data[ticker.upper()] = sorted_prices[:lookback_days]
                    else:
                        price_data[ticker.upper()] = prices
                else:
                    # Fallback: try general stock data
                    all_stocks_data = load_json("stocks")
                    if all_stocks_data and isinstance(all_stocks_data, dict):
                        # This is more complex to extract individual ticker data from general stocks file
                        pass  # For now, skip if individual ticker data not found
            except Exception as e:
                print(f"Error loading price data for {ticker}: {e}")
                # Continue loading other tickers rather than failing all
                continue
        
        return price_data
    
    def _get_all_available_tickers(self) -> List[str]:
        """
        Get list of all available tickers from stored data
        """
        try:
            # Load general stocks data to get all available tickers
            all_stocks = load_json("stocks") or {}
            
            if "tickers" in all_stocks:
                return all_stocks["tickers"]
            elif "data" in all_stocks and "tickers" in all_stocks["data"]:
                return all_stocks["data"]["tickers"]
            else:
                # Default set of common tickers
                return ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "META", "TSLA", "AMZN", "NFLX"]
        except:
            # Return default tickers if we can't load from storage
            return ["SPY", "QQQ", "AAPL", "NVDA"]


# Global instance
stock_correlation_service = StockCorrelationService()

# Convenience functions for API access
def get_correlation_heatmap_data(tickers: Optional[List[str]] = None, 
                                lookback_days: int = 30,
                                min_correlation: float = 0.1):
    """
    Get correlation heatmap data from service
    """
    return stock_correlation_service.get_correlation_heatmap_data(tickers, lookback_days, min_correlation)

def get_correlation_matrix(tickers: List[str], lookback_days: int = 30):
    """
    Get raw correlation matrix (not heatmap structure)
    """
    try:
        from models.correlation_matrix import calculate_correlation_matrix
        # Load price data
        price_data = stock_correlation_service._load_price_data(tickers, lookback_days)
        return calculate_correlation_matrix(price_data, lookback_days)
    except Exception as e:
        return {
            "matrix": {},
            "tickers": tickers,
            "lookback_days": lookback_days,
            "error": str(e),
            "status": "error",
            "message": "Failed to compute correlation matrix"
        }