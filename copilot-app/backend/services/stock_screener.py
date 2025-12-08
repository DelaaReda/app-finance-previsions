"""
Stock Screener Service
Task: FC-API-026 - Stocks Screener (advanced filtering)
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from models.stock_filters import StockScreener, StockFilter
from storage.io import load_json
from services.cache_layer import load_or_compute


class StockScreenerService:
    """
    Service to screen stocks with advanced filtering capabilities
    """
    
    def __init__(self):
        self.screener = StockScreener()
    
    def get_filtered_stocks(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get stocks filtered by advanced criteria
        """
        def compute_filtered_stocks():
            """
            Compute filtered stocks from stored data
            """
            try:
                # Load stock data
                stock_data = load_json("stocks") or {}
                
                # Extract stock rows (could be in different formats)
                if "payload" in stock_data and "rows" in stock_data["payload"]:
                    stocks = stock_data["payload"]["rows"]
                elif "data" in stock_data and "rows" in stock_data["data"]:
                    stocks = stock_data["data"]["rows"]
                elif "rows" in stock_data:
                    stocks = stock_data["rows"]
                else:
                    stocks = []  # Fallback to empty list
                    
                # Use default filters if none provided
                filter_dict = filters or {}
                
                # Apply stock screening filters
                result = self.screener.screen_stocks(stocks, filter_dict)
                
                # Add metadata to result
                result["source"] = ["stock_screener_service", "advanced_filtering", "fc-api-026"]
                result["generated_at"] = datetime.utcnow().isoformat() + "Z"
                
                return result
                
            except Exception as e:
                # Fallback to ensure never-empty contract
                print(f"Error in filtered stocks: {str(e)}")
                return {
                    "ok": False,
                    "data": {
                        "filtered_stocks": [],
                        "count": 0,
                        "applied_filters": filters or {},
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "filter_summary": {
                            "sector": None,
                            "price_range": [None, None],
                            "market_cap_range": [None, None],
                            "pe_ratio_range": [None, None],
                            "sort_by": "market_cap",
                            "sort_order": "desc"
                        },
                        "message": f"Stock filtering failed: {str(e)}",
                        "source": ["stock_screener_service", "error_fallback", "fc-api-026"]
                    }
                }
        
        # Use cache layer to serve latest data, compute fresh if none available
        cached_result = load_or_compute(
            key=f"stock_screener_{str(filters or 'default')}",
            compute_fn=compute_filtered_stocks,
            source=["stock_screener_service", "advanced_filtering", "fc-api-026"]
        )
        
        return cached_result
    
    def validate_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate filter parameters without applying them
        """
        try:
            validation_errors = self.screener.validate_filter_params(filters)
            return {
                "ok": len(validation_errors) == 0,
                "errors": validation_errors,
                "validated_at": datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "validated_at": datetime.utcnow().isoformat() + "Z"
            }
    
    def get_filter_options(self) -> Dict[str, Any]:
        """
        Get available filter options for UI dropdowns
        """
        try:
            return {
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
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            return {
                "sectors": [],
                "sort_options": [],
                "volatility_options": [],
                "sort_orders": ["asc", "desc"],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e)
            }


# Global instance
stock_screener_service = StockScreenerService()

# Convenience functions
def get_filtered_stocks(filters: Optional[Dict[str, Any]] = None):
    """
    Get stocks filtered by advanced criteria
    """
    return stock_screener_service.get_filtered_stocks(filters)

def validate_filters(filters: Dict[str, Any]):
    """
    Validate filter parameters
    """
    return stock_screener_service.validate_filters(filters)

def get_filter_options():
    """
    Get available filter options for UI
    """
    return stock_screener_service.get_filter_options()